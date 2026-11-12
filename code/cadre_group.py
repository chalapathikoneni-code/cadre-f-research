"""Share-aware CADRE-F variants. Designed on pilot instances only.

CADRE-G ("group certificate"): CADRE-F prices one target query by an executable
cover of its own unresolved pairs. When one shared item advances several
queries, that per-query price misses the saving. CADRE-G also considers, for
each shared item e, the group G_e of undecided queries whose unresolved pairs
e touches, and builds an executable cover of all pairs of G_e (weighted greedy
set cover; still a valid certificate: buying it decides every query in G_e in
every world). Its cost per query, H(G_e)/|G_e|, is compared with the best
single-query cover. If a group is strictly cheaper per query and affordable,
CADRE-G buys the first item of the group cover; otherwise it acts exactly as
CADRE-F. The capture gate and the myopic fallback are CADRE-F's.

CADRE-D: CADRE-F with obligation-density greedy instead of myopic as the
fallback when no single target is affordable (pilot control).
"""
import math

import wcaea_fixed as wf
import cadre_feasible as cf


def group_cover(inst, state, group):
    """Executable cover of every unresolved pair of the queries in `group`.

    shortcut: weighted greedy set cover (ln-factor from optimal); exact DP
    would be exponential in the union size. Returns (plan, cost) or ((), inf).
    """
    need = {(query, oblig) for query in group for oblig in inst.obligations[query] if (query, oblig) not in state}
    if not need:
        return (), 0.0
    plan, cost = [], 0.0
    while need:
        best, best_density = None, 0.0
        for item, meta in inst.items.items():
            covered = len(meta['resolves'] & need)
            if covered and covered / meta['cost'] > best_density + 1e-12:
                best, best_density = item, covered / meta['cost']
        if best is None:
            return (), math.inf
        plan.append(best)
        cost += inst.items[best]['cost']
        need -= inst.items[best]['resolves']
    return tuple(plan), cost


def _gate(inst, state, cand, worst, rem):
    """CADRE-F's capture gate (unchanged)."""
    finite = sorted(cost_value for cost_value in worst.values() if math.isfinite(cost_value))
    n_aff = sum(cost_value <= rem for cost_value in finite)
    fair = finite[0] + finite[1] if n_aff >= 2 else (finite[0] if finite else rem)
    best, best_score = None, 0.0
    for item in cand:
        cost = inst.items[item]['cost']
        if cost > fair:
            continue
        gain = wf.exp_true_gain(inst, state, item)
        if gain / cost > best_score + 1e-12:
            best, best_score = item, gain / cost
    return best


def pol_cadre_group(inst, state, spent, budget, rng):
    cand = wf._remaining(inst, state, spent, budget)
    if not cand:
        return None
    rem = budget - spent
    undecided = [query for query in inst.queries if not wf.decided(inst, state, query)]
    worst = {query: cf.feasible_bound(inst, state, query) for query in undecided}
    item = _gate(inst, state, cand, worst, rem)
    if item is not None:
        return item
    undecided_set = set(undecided)
    single = min((worst[query] for query in undecided if worst[query] <= rem), default=math.inf)
    best_plan, best_ratio = None, single
    seen = set()
    for item in cand:
        group = frozenset(query for (query, oblig) in inst.items[item]['resolves'] if query in undecided_set and (query, oblig) not in state)
        if len(group) < 2 or group in seen:
            continue
        seen.add(group)
        plan, cost = group_cover(inst, state, group)
        if cost <= rem and cost / len(group) < best_ratio - 1e-12:
            best_plan, best_ratio = plan, cost / len(group)
    if best_plan is not None:
        for item in best_plan:  # first still-useful item of the group cover
            if item in cand:
                return item
    return cf.pol_cadre_cover(inst, state, spent, budget, rng)


def _best_group_plan(inst, state, cand, worst, rem, undecided):
    """Cheapest-per-query affordable group cover that beats every single cover."""
    undecided_set = set(undecided)
    single = min((worst[query] for query in undecided if worst[query] <= rem), default=math.inf)
    best_plan, best_ratio = None, single
    seen = set()
    for item in cand:
        group = frozenset(query for (query, oblig) in inst.items[item]['resolves'] if query in undecided_set and (query, oblig) not in state)
        if len(group) < 2 or group in seen:
            continue
        seen.add(group)
        plan, cost = group_cover(inst, state, group)
        if cost <= rem and cost / len(group) < best_ratio - 1e-12:
            best_plan, best_ratio = plan, cost / len(group)
    return best_plan


def pol_cadre_group_first(inst, state, spent, budget, rng):
    """CADRE-G2: the group step runs before the capture gate."""
    cand = wf._remaining(inst, state, spent, budget)
    if not cand:
        return None
    rem = budget - spent
    undecided = [query for query in inst.queries if not wf.decided(inst, state, query)]
    worst = {query: cf.feasible_bound(inst, state, query) for query in undecided}
    plan = _best_group_plan(inst, state, cand, worst, rem, undecided)
    if plan is not None:
        for item in plan:
            if item in cand:
                return item
    return cf.pol_cadre_cover(inst, state, spent, budget, rng)


def pol_cadre_group_dense(inst, state, spent, budget, rng):
    """CADRE-G3: like G2, but buys the group-cover item resolving most pairs per cost."""
    cand = wf._remaining(inst, state, spent, budget)
    if not cand:
        return None
    rem = budget - spent
    undecided = [query for query in inst.queries if not wf.decided(inst, state, query)]
    worst = {query: cf.feasible_bound(inst, state, query) for query in undecided}
    plan = _best_group_plan(inst, state, cand, worst, rem, undecided)
    if plan is not None:
        available = [item for item in plan if item in cand]
        if available:
            def density(item):
                return len([pair for pair in inst.items[item]['resolves'] if pair not in state]) / inst.items[item]['cost']
            return max(available, key=lambda item: (density(item), item))
    return cf.pol_cadre_cover(inst, state, spent, budget, rng)


def pol_cadre_density_fallback(inst, state, spent, budget, rng):
    cand = wf._remaining(inst, state, spent, budget)
    if not cand:
        return None
    rem = budget - spent
    undecided = [query for query in inst.queries if not wf.decided(inst, state, query)]
    worst = {query: cf.feasible_bound(inst, state, query) for query in undecided}
    if not any(worst[query] <= rem for query in undecided) and _gate(inst, state, cand, worst, rem) is None:
        return wf.pol_sssc(inst, state, spent, budget, rng)
    return cf.pol_cadre_cover(inst, state, spent, budget, rng)
