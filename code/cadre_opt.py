"""Optimized CADRE. Same semantics as wcaea.pol_completion; only the
cost-to-decide computation is restructured:
(1) cheapest-item-per-cluster precomputed once per instance;
(2) per-query cluster->cheapest-cost and item->clusters maps precomputed;
(3) the heuristic proxy arithmetic is identical (ratio-order refutation
    score, max-coverage-first cluster-footprint cover, min of the two), so
    the proxy is still neither optimal cost nor a certified bound.
The algorithm is unchanged, including its possibly over-optimistic
affordability gate. Only the O(|E|) scans are replaced, by precomputed
lookups. Decision equivalence with the reference implementation is checked
by comparing pick trajectories under identical world seeds."""
import os, sys, math, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wcaea_fixed as wcaea
from wcaea_fixed import decided, exp_true_gain

_cache = {}
def _prep(inst):
    key = (id(inst), len(inst.items))
    hit = _cache.get(key)
    if hit is not None and hit[2] is inst.items: return hit
    item_clusters = {item: {inst.pair_cluster[pair] for pair in meta['resolves']}
                     for item, meta in inst.items.items()}
    cheapest = {}
    for item, meta in inst.items.items():
        # Match the reference semantics exactly: cheapest_item_for([g])
        # minimises cost over items whose resolution set touches cluster g
        # at all (any pair), not just items resolving a g-pair of a query.
        for pair in meta['resolves']:
            cluster = inst.pair_cluster[pair]
            if cluster not in cheapest or meta['cost'] < cheapest[cluster]: cheapest[cluster] = meta['cost']
    _cache[key] = (item_clusters, cheapest, inst.items)
    return _cache[key]

def ctd_fast(inst, state, query):
    if decided(inst, state, query): return 0.0
    item_clusters, cheapest, _ = _prep(inst)
    unres = {}
    for oblig in inst.obligations[query]:
        if (query, oblig) not in state:
            unres.setdefault(inst.pair_cluster[(query, oblig)], []).append(oblig)
    if not unres: return 0.0
    order = sorted(unres, key=lambda cluster: cheapest[cluster] / max(1e-9, inst.cluster_pfail[cluster]))
    exp_ref, prem = 0.0, 1.0
    for cluster in order:
        exp_ref += prem * cheapest[cluster]
        prem *= (1 - inst.cluster_pfail[cluster])
    remaining = set(unres); adm = 0.0
    while remaining:
        best_item, best_cover = None, set()
        for item, meta in inst.items.items():
            cov = item_clusters[item] & remaining
            if len(cov) > len(best_cover) or (len(cov) == len(best_cover) and best_item and meta['cost'] < inst.items[best_item]['cost']):
                best_item, best_cover = item, cov
        if best_item is None: return math.inf
        adm += inst.items[best_item]['cost']; remaining -= best_cover
    return min(exp_ref, adm)

def _ctd_reduction(inst, state, query, item, base):
    """Copied semantics from wcaea.pol_completion's plateau scoring, with
    ctd_fast substituted."""
    open_clusters = sorted({inst.pair_cluster[(query, oblig)] for oblig in inst.obligations[query] if (query, oblig) not in state} &
                {inst.pair_cluster[pair] for pair in inst.items[item]['resolves']})
    red = 0.0
    for combo in itertools.product([0, 1], repeat=len(open_clusters)):
        prob, theta = 1.0, {}
        for cluster, isfail in zip(open_clusters, combo):
            pf = inst.cluster_pfail[cluster]
            prob *= pf if isfail else (1 - pf)
            theta[cluster] = 'fail' if isfail else 'pass'
        upd = dict(state)
        for pair in inst.items[item]['resolves']:
            if inst.pair_cluster[pair] in theta: upd[pair] = theta[inst.pair_cluster[pair]]
        red += prob * (base - ctd_fast(inst, upd, query))
    return red

def pol_completion_opt(inst, state, spent, budget, rng):
    cand = wcaea._remaining(inst, state, spent, budget)
    if not cand: return None
    undecided0 = [query for query in inst.queries if not decided(inst, state, query)]
    ctds = {query: ctd_fast(inst, state, query) for query in undecided0}
    _finite = sorted(cost_value for cost_value in ctds.values() if cost_value != math.inf)
    _n_aff = sum(1 for cost_value in _finite if cost_value <= budget - spent)
    if _n_aff >= 2: fair_share = _finite[0] + _finite[1]
    elif _finite: fair_share = _finite[0]
    else: fair_share = budget - spent
    best_true, best_score = None, 0.0
    for item in cand:
        if inst.items[item]['cost'] > fair_share: continue
        gain = exp_true_gain(inst, state, item)
        if gain / inst.items[item]['cost'] > best_score + 1e-12:
            best_score, best_true = gain / inst.items[item]['cost'], item
    if best_true is not None: return best_true
    remaining_budget = budget - spent
    affordable = [query for query in undecided0 if ctds[query] <= remaining_budget]
    pool = affordable if affordable else undecided0
    qstar = min(pool, key=lambda query: ctds[query])
    base = ctds[qstar]
    best, best_score = None, -1e18
    for item in cand:
        score = _ctd_reduction(inst, state, qstar, item, base) / inst.items[item]['cost']
        if score > best_score: best_score, best = score, item
    if best is None:
        best_red, best_score = None, -1e18
        for item in cand:
            red_all = 0.0
            for query in undecided0:
                query_base = ctds[query]
                if query_base == math.inf: continue
                red_all += _ctd_reduction(inst, state, query, item, query_base)
            score = red_all / inst.items[item]['cost']
            if score > best_score: best_score, best_red = score, item
        return best_red if best_red is not None else cand[0]
    return best
