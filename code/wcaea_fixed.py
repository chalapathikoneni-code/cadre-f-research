"""Workload-level Conjunctive-Admissibility Evidence Acquisition (W-CAEA).

Model:
- Queries q, each with obligations O_q (conjunctive).
- Evidence items e: cost c_e; acquiring e resolves a known set Res(e) of
  (query, obligation) pairs. Each (q, o) pair has an outcome in {pass, fail}
  drawn from a known distribution; outcomes of pairs sharing a *dependence
  cluster* (same origin, e.g. copied sources) are perfectly correlated:
  one latent draw per cluster determines all its pairs' outcomes.
- A query is DECIDED when every obligation is resolved-pass (ADMITTED) or at
  least one obligation is resolved-fail (REFUTED). Utility = # decided.
- Policies are adaptive: choose next item given observed outcomes; stop at
  budget B (budgeted max-decided) or when all decided (min-cost decide-all).

Outcomes are represented by cluster draws: each cluster g has latent value
theta_g in {pass, fail} with P(fail) = pf_g. A pair (q,o) belongs to exactly
one cluster (the origin whose verification settles it). An item resolves its
pairs by revealing the clusters of those pairs (acquiring an item that touches
a cluster reveals that cluster's theta).
"""
from __future__ import annotations
import itertools, math, random
from dataclasses import dataclass, field

@dataclass
class Instance:
    queries: list                 # query ids
    obligations: dict             # q -> list of obligation ids (strings)
    items: dict                   # e -> {"cost": float, "resolves": set[(q,o)]}
    pair_cluster: dict            # (q,o) -> cluster id
    cluster_pfail: dict           # cluster -> P(theta = fail)
    name: str = "inst"

    def pairs(self):
        return [(query, oblig) for query in self.queries for oblig in self.obligations[query]]

    def clusters(self):
        return sorted(self.cluster_pfail)

# ---------- world sampling ----------
def draw_world(inst, rng):
    """Return dict (q,o) -> 'pass'/'fail' from cluster latents."""
    theta = {cluster: ("fail" if rng.random() < inst.cluster_pfail[cluster] else "pass")
             for cluster in inst.cluster_pfail}
    return {(query, oblig): theta[inst.pair_cluster[(query, oblig)]] for (query, oblig) in inst.pairs()}

# ---------- state ----------
# state: dict (q,o) -> 'pass'/'fail' for resolved pairs; item outcomes derive
# from clusters, so resolving one pair of a cluster resolves all its pairs.
def apply_item(inst, state, item, world):
    """Resolve exactly the item's resolution set. Outcomes come from the
    pairs' dependence clusters, so pairs sharing an origin are perfectly
    correlated even when resolved by different items."""
    new = dict(state)
    for pair in inst.items[item]["resolves"]:
        if pair not in new:
            new[pair] = world[pair]
    return new

def decided(inst, state, query):
    oblig_list = inst.obligations[query]
    outcomes = [state.get((query, oblig)) for oblig in oblig_list]
    if any(outcome == "fail" for outcome in outcomes):
        return "refuted"
    if all(outcome == "pass" for outcome in outcomes):
        return "admitted"
    return None

def n_decided(inst, state):
    return sum(1 for query in inst.queries if decided(inst, state, query))

def unresolved_pairs(inst, state):
    return [pair for pair in inst.pairs() if pair not in state]

def item_useful(inst, state, item):
    return any(pair not in state for pair in inst.items[item]["resolves"])


# ---------- analytic expected gains (no Monte Carlo in policy decisions) --
def _p_decided_after(inst, state, query, extra_pairs):
    """P(q decided) if the pairs in extra_pairs were resolved (outcomes drawn
    from their clusters), given current state. Clusters independent."""
    oblig_list = inst.obligations[query]
    outcomes = {oblig: state.get((query, oblig)) for oblig in oblig_list}
    if any(outcome == "fail" for outcome in outcomes.values()):
        return 1.0
    # unresolved obligations after extra resolution
    unresolved = [oblig for oblig in oblig_list if outcomes[oblig] is None and (query, oblig) not in extra_pairs]
    newly = [oblig for oblig in oblig_list if outcomes[oblig] is None and (query, oblig) in extra_pairs]
    if not newly and unresolved:
        return 0.0 if not decided(inst, state, query) else 1.0
    if decided(inst, state, query):
        return 1.0
    # q is decided now if some newly resolved cluster fails (refutation) or
    # all newly resolved ones pass. We only count queries decided after this
    # item, i.e. all obligations resolved and (any fail or all pass).
    if unresolved:
        return 0.0  # still unresolved obligations remain -> not decided now
    # all obligations resolved after this item: decided with probability 1
    return 1.0

def exp_true_gain(inst, state, item):
    """E[# newly decided queries] from acquiring item. Exact, and credits
    both completion and refutation gains. For each undecided q the item
    touches, q is decided if some newly resolved cluster fails (refutation)
    or the item resolves q's last open obligations (decided either way)."""
    res = inst.items[item]["resolves"]
    total = 0.0
    for query in {query for (query, oblig) in res}:
        if decided(inst, state, query):
            continue
        oblig_list = inst.obligations[query]
        open_obligs = [oblig for oblig in oblig_list if (query, oblig) not in state]
        new_clusters = {inst.pair_cluster[(query, oblig)] for oblig in open_obligs if (query, oblig) in res}
        if not new_clusters:
            continue
        # Condition on clusters we already saw. A cluster revealed through
        # another resolved pair has a known outcome: revealed-fail means q
        # is already decided (handled above), revealed-pass contributes
        # probability 1, not (1 - pfail).
        revealed = {}
        for pair, outcome in state.items():
            revealed[inst.pair_cluster[pair]] = outcome
        p_all_pass = 1.0
        for cluster in new_clusters:
            if revealed.get(cluster) == 'pass':
                continue
            if revealed.get(cluster) == 'fail':
                p_all_pass = 0.0; break
            p_all_pass *= (1 - inst.cluster_pfail[cluster])
        p_refuted = 1 - p_all_pass
        remaining_obligs = [oblig for oblig in open_obligs if (query, oblig) not in res]
        total += p_refuted + (p_all_pass if not remaining_obligs else 0.0)
    return total

def exp_surrogate_gain(inst, state, item):
    return float(sum(1 for pair in inst.items[item]["resolves"] if pair not in state))

# ---------- policies: fn(inst, state, spent, budget) -> item id or None ----------
def _remaining(inst, state, spent, budget):
    return [item for item in inst.items if inst.items[item]["cost"] <= budget - spent
            and item_useful(inst, state, item)]

def _expected_gain(inst, state, item, gainfn, rng, sims=30):
    """Monte Carlo estimate of E[gainfn(state after item) - gainfn(state)]."""
    base = gainfn(inst, state)
    total = 0.0
    for _ in range(sims):
        world = draw_world(inst, rng)
        total += gainfn(inst, apply_item(inst, state, item, world)) - base
    return total / sims

def pol_sssc(inst, state, spent, budget, rng):
    """Adaptive greedy on the SSSC surrogate: expected newly resolved
    obligations per unit cost (Golovin-Krause / DHK-style)."""
    cand = _remaining(inst, state, spent, budget)
    if not cand: return None
    best, best_score = None, -1.0
    for item in cand:
        score = exp_surrogate_gain(inst, state, item) / inst.items[item]["cost"]
        if score > best_score: best_score, best = score, item
    return best

def pol_myopic(inst, state, spent, budget, rng):
    """Adaptive greedy on the true objective: expected newly decided queries
    per unit cost. Ties broken by surrogate progress, then by cheapest."""
    cand = _remaining(inst, state, spent, budget)
    if not cand: return None
    scored = []
    for item in cand:
        gain = exp_true_gain(inst, state, item)
        scored.append((gain / inst.items[item]["cost"], gain, -inst.items[item]["cost"], item))
    scored.sort(reverse=True)
    if scored[0][1] > 1e-9:
        return scored[0][3]
    # plateau: no item decides anything in expectation -> surrogate tie-break
    best, best_score = None, -1.0
    for item in cand:
        score = exp_surrogate_gain(inst, state, item) / inst.items[item]["cost"]
        if score > best_score: best_score, best = score, item
    return best

def pol_coverage(inst, state, spent, budget, rng):
    """Das Sarma-Dong-Halevy style coverage planner (adapted): maximise the
    number of distinct queries touched by new independent evidence per cost.
    Copies in the same cluster count once. Blind to correctness/obligations."""
    cand = _remaining(inst, state, spent, budget)
    if not cand: return None
    seen_clusters = {inst.pair_cluster[pair] for pair in state}
    best, best_score = None, -1.0
    for item in cand:
        touched_queries, touched_clusters = set(), set()
        for (query, oblig) in inst.items[item]["resolves"]:
            cluster = inst.pair_cluster[(query, oblig)]
            if cluster not in seen_clusters:
                touched_queries.add(query); touched_clusters.add(cluster)
        score = len(touched_queries) / inst.items[item]["cost"]
        if score > best_score: best_score, best = score, item
    return best

def _cost_to_decide(inst, state, query):
    """Heuristic cost-to-decide proxy for q. This is not a proven bound.

    It approximates a refutation sequence and an admission cover from cluster
    footprints, counting items that may resolve a different query's pair in
    the same cluster. So the value can come out below any feasible cost to
    decide q, which can make CADRE's budget gate optimistic. This matches the
    reference policy's proxy exactly. Do not read it as an optimal expected
    cost or an upper bound."""
    if decided(inst, state, query):
        return 0.0
    # clusters still unresolved for q, grouped: obligation -> cluster
    unresolved = {}
    for oblig in inst.obligations[query]:
        if (query, oblig) not in state:
            unresolved.setdefault(inst.pair_cluster[(query, oblig)], []).append(oblig)
    if not unresolved:
        return 0.0
    # cheapest item covering each cluster (an item may cover several)
    def cheapest_item_for(clusters):
        best = math.inf
        for item, meta in inst.items.items():
            cov = {inst.pair_cluster[pair] for pair in meta["resolves"]} & set(clusters)
            if cov:
                best = min(best, meta["cost"])
        return best
    # refutation: acquire items until some cluster fails; expected cost of
    # testing clusters in increasing cost/(pfail) order (ratio rule approx)
    order = sorted(unresolved, key=lambda cluster: cheapest_item_for([cluster]) / max(1e-9, inst.cluster_pfail[cluster]))
    exp_ref, prem = 0.0, 1.0
    for cluster in order:
        cost = cheapest_item_for([cluster])
        exp_ref += prem * cost
        prem *= (1 - inst.cluster_pfail[cluster])
    # admission: must reveal every cluster and have all pass; expected cost
    # = sum of cheapest items covering the cluster set (greedy cover), paid
    # regardless
    remaining = set(unresolved); adm = 0.0
    while remaining:
        best_item, best_cover = None, set()
        for item, meta in inst.items.items():
            cov = {inst.pair_cluster[pair] for pair in meta["resolves"]} & remaining
            if len(cov) > len(best_cover) or (len(cov) == len(best_cover) and best_item and meta["cost"] < inst.items[best_item]["cost"]):
                best_item, best_cover = item, cov
        if best_item is None: return math.inf
        adm += inst.items[best_item]["cost"]; remaining -= best_cover
    return min(exp_ref, adm)

def pol_completion(inst, state, spent, budget, rng):
    """Completion-aware acquisition. If some item has positive expected true
    gain, take the best gain/cost (the myopic step). Otherwise pick the
    undecided query with the smallest cost-to-decide and buy the item that
    cuts that query's cost-to-decide the most per unit cost. This keeps
    spending on the cheapest completion instead of spreading it across many
    near-complete queries."""
    cand = _remaining(inst, state, spent, budget)
    if not cand: return None
    # Gate the decisive step on affordability. Take a positive-gain item only
    # if the completion it finishes is affordable, i.e. its cost is within a
    # fair share (1 / #undecided) of the remaining budget. Without the gate a
    # single expensive completion captures the policy the same way it captures
    # myopic greedy (family F2).
    undecided0 = [query for query in inst.queries if not decided(inst, state, query)]
    # Fair share comes from the remaining workload's completions: the mean
    # cost-to-decide over undecided queries. An item above the average
    # completion is a capture risk; cheaper decisive items are not.
    _ctds = [_cost_to_decide(inst, state, query) for query in undecided0]
    _finite = sorted(cost_value for cost_value in _ctds if cost_value != math.inf)
    _n_aff = sum(1 for cost_value in _finite if cost_value <= budget - spent)
    if _n_aff >= 2:
        # Cheapest-pair rule: one decisive purchase must not cost more than
        # the two cheapest affordable completions combined. A purchase that
        # expensive gives up at least two decisions elsewhere. Eg F2's
        # eX1 = 100 >> 2+2 is blocked; F3's origin = 6 <= 2+7 passes.
        fair_share = _finite[0] + _finite[1]
    elif _finite:
        fair_share = _finite[0]
    else:
        fair_share = budget - spent
    best_true, best_score = None, 0.0
    for item in cand:
        if inst.items[item]["cost"] > fair_share:
            continue
        gain = exp_true_gain(inst, state, item)
        if gain / inst.items[item]["cost"] > best_score + 1e-12:
            best_score, best_true = gain / inst.items[item]["cost"], item
    if best_true is not None:
        return best_true
    undecided = [query for query in inst.queries if not decided(inst, state, query)]
    # Only target queries whose completion is affordable within the remaining
    # budget. Spending toward a completion the budget can never reach is the
    # sunk cost this policy is meant to avoid.
    remaining_budget = budget - spent
    affordable = [query for query in undecided
                  if _cost_to_decide(inst, state, query) <= remaining_budget]
    pool = affordable if affordable else undecided
    qstar = min(pool, key=lambda query: _cost_to_decide(inst, state, query))
    base = _cost_to_decide(inst, state, qstar)
    best, best_score = None, -1e18
    for item in cand:
        # expected reduction in qstar's cost-to-decide: enumerate outcomes of
        # the clusters e touches (others marginalise out of the expectation
        # only through qstar's open clusters; restrict to those).
        open_clusters = sorted({inst.pair_cluster[(qstar, oblig)] for oblig in inst.obligations[qstar]
                                if (qstar, oblig) not in state} &
                               {inst.pair_cluster[pair] for pair in inst.items[item]["resolves"]})
        red = 0.0
        for combo in itertools.product([0, 1], repeat=len(open_clusters)):
            prob, theta = 1.0, {}
            for cluster, isfail in zip(open_clusters, combo):
                pfail = inst.cluster_pfail[cluster]
                prob *= pfail if isfail else (1 - pfail)
                theta[cluster] = "fail" if isfail else "pass"
            upd = dict(state)
            for pair in inst.items[item]["resolves"]:
                if inst.pair_cluster[pair] in theta:
                    upd[pair] = theta[inst.pair_cluster[pair]]
            red += prob * (base - _cost_to_decide(inst, upd, qstar))
        score = red / inst.items[item]["cost"]
        if score > best_score: best_score, best = score, item
    if best is None:
        # No candidate reduces qstar's ctd (e.g. qstar is decided only via an
        # unaffordable completion). Fall back to the largest expected ctd
        # reduction per unit cost across all undecided queries.
        best_red, best_score = None, -1e18
        for item in cand:
            red_all = 0.0
            for query in undecided:
                query_base = _cost_to_decide(inst, state, query)
                if query_base == math.inf: continue
                open_clusters = sorted({inst.pair_cluster[(query, oblig)] for oblig in inst.obligations[query]
                             if (query, oblig) not in state} &
                            {inst.pair_cluster[pair] for pair in inst.items[item]["resolves"]})
                for combo in itertools.product([0, 1], repeat=len(open_clusters)):
                    prob, theta = 1.0, {}
                    for cluster, isfail in zip(open_clusters, combo):
                        pfail = inst.cluster_pfail[cluster]
                        prob *= pfail if isfail else (1 - pfail)
                        theta[cluster] = "fail" if isfail else "pass"
                    upd = dict(state)
                    for pair in inst.items[item]["resolves"]:
                        if inst.pair_cluster[pair] in theta: upd[pair] = theta[inst.pair_cluster[pair]]
                    red_all += prob * (query_base - _cost_to_decide(inst, upd, query))
            score = red_all / inst.items[item]["cost"]
            if score > best_score: best_score, best_red = score, item
        return best_red if best_red is not None else cand[0]
    return best

POLICIES = {"sssc": pol_sssc, "myopic": pol_myopic, "coverage": pol_coverage,
            "completion": pol_completion}

# ---------- evaluation ----------
def run_policy(inst, policy, budget, rng, seed_items=None):
    """Simulate one adaptive run in a fresh world. Returns (decided, spent)."""
    world = draw_world(inst, rng)
    state, spent = {}, 0.0
    guard = 0
    while spent < budget and n_decided(inst, state) < len(inst.queries) and guard < 10000:
        guard += 1
        item = policy(inst, state, spent, budget, rng)
        if item is None: break
        spent += inst.items[item]["cost"]
        state = apply_item(inst, state, item, world)
    return n_decided(inst, state), spent

def eval_policy(inst, pname, budget, trials=200, seed=7):
    rng = random.Random(seed)
    dec, cost = 0.0, 0.0
    for _ in range(trials):
        decided_count, spent_cost = run_policy(inst, POLICIES[pname], budget, rng)
        dec += decided_count; cost += spent_cost
    return dec / trials, cost / trials

# ---------- exact solver (small instances, integer costs) ----------
from functools import lru_cache

def exact_budgeted(inst, budget):
    """Optimal adaptive policy value: max expected # decided within budget.
    State = tuple of (pair -> outcome) for resolved pairs, encoded as a
    frozenset of (pair, outcome); remaining budget integer. Enumerates the
    outcome distribution of newly resolved clusters exactly."""
    pairs = inst.pairs()
    pidx = {pair: idx for idx, pair in enumerate(pairs)}
    items = list(inst.items)
    costs = {item: inst.items[item]["cost"] for item in items}
    assert all(float(cost_value).is_integer() for cost_value in costs.values()), "exact solver needs integer costs"
    clusters = inst.clusters()
    cidx = {cluster: idx for idx, cluster in enumerate(clusters)}

    def decided_count(state):
        state_copy = dict(state)
        return n_decided(inst, state_copy)

    from functools import lru_cache
    @lru_cache(maxsize=None)
    def value_of(state_fs, rem):
        state = dict(state_fs)
        base = decided_count(state_fs)
        if rem <= 0 or base == len(inst.queries):
            return float(base)
        best = float(base)  # may stop
        for item in items:
            cost_value = int(costs[item])
            if cost_value > rem: continue
            new_pairs = [pair for pair in inst.items[item]["resolves"] if pair not in state]
            if not new_pairs: continue
            revealed = {inst.pair_cluster[pair] for pair in state}
            new_clusters = sorted({inst.pair_cluster[pair] for pair in new_pairs} - revealed)
            exp = 0.0
            for combo in itertools.product([0, 1], repeat=len(new_clusters)):
                prob, upd = 1.0, dict(state)
                theta = {}
                for cluster, isfail in zip(new_clusters, combo):
                    pfail = inst.cluster_pfail[cluster]
                    prob *= pfail if isfail else (1 - pfail)
                    theta[cluster] = "fail" if isfail else "pass"
                for pair in new_pairs:
                    cluster = inst.pair_cluster[pair]
                    if cluster in theta:
                        upd[pair] = theta[cluster]
                    else:
                        # cluster already revealed: inherit its outcome
                        source_pair = next(other for other in state if inst.pair_cluster[other] == cluster)
                        upd[pair] = state[source_pair]
                exp += prob * value_of(frozenset(upd.items()), rem - cost_value)
            best = max(best, exp)
        return best
    return value_of(frozenset(), int(budget))
