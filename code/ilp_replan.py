"""ILP re-plan baseline: solve the all-pass budgeted completion problem
exactly on the current state, buy one item of the optimal
plan, and re-solve after every purchase.

At each step, over undecided queries U and affordable useful items A:
    max  sum_q y_q
    s.t. y_q <= sum_{e in A: p in R(e)} x_e   for every unresolved pair p of q in U
         sum_e c_e x_e <= remaining budget,   x, y binary.
The ILP assumes every pair passes, so it values only admissions; a failure
seen on the way still refutes its query and the next solve uses the new state.
Among the optimal plan's items it buys the one resolving the most unresolved
pairs per unit cost (ties by item id). If the optimum completes no query it
falls back to myopic (to keep refutation opportunities). Requires SciPy
(HiGHS via scipy.optimize.milp).
"""
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

import wcaea_fixed as wf

TIME_LIMIT = 2.0  # seconds per solve; shortcut: best incumbent if hit (logged as non-optimal)
STATS = {'solves': 0, 'nonoptimal': 0}


def pol_ilp_replan(inst, state, spent, budget, rng):
    cand = wf._remaining(inst, state, spent, budget)
    if not cand:
        return None
    rem = budget - spent
    und = [query for query in inst.queries if not wf.decided(inst, state, query)]
    pairs = [(query, oblig) for query in und for oblig in inst.obligations[query] if (query, oblig) not in state]
    cand = sorted(cand)
    ne, nq = len(cand), len(und)
    qi = {query: ne + idx for idx, query in enumerate(und)}
    cover = {}
    for col, item in enumerate(cand):
        for pair in inst.items[item]['resolves']:
            if pair not in state:
                cover.setdefault(pair, []).append(col)
    rows = [pair for pair in pairs]
    constraint_matrix = lil_matrix((len(rows) + 1, ne + nq))
    for row, pair in enumerate(rows):
        constraint_matrix[row, qi[pair[0]]] = 1.0
        for col in cover.get(pair, []):
            constraint_matrix[row, col] = -1.0
    for col, item in enumerate(cand):
        constraint_matrix[len(rows), col] = inst.items[item]['cost']
    lo = np.full(len(rows) + 1, -np.inf)
    hi = np.zeros(len(rows) + 1)
    hi[-1] = rem + 1e-9
    objective = np.concatenate([np.zeros(ne), -np.ones(nq)])
    res = milp(objective, constraints=LinearConstraint(constraint_matrix.tocsr(), lo, hi), integrality=np.ones(ne + nq),
               bounds=Bounds(0, 1), options={'time_limit': TIME_LIMIT, 'disp': False})
    STATS['solves'] += 1
    if res.status != 0:
        STATS['nonoptimal'] += 1
    if res.x is None or -res.fun < 0.5:
        return wf.pol_myopic(inst, state, spent, budget, rng)
    plan = [cand[col] for col in range(ne) if res.x[col] > 0.5]
    if not plan:
        return wf.pol_myopic(inst, state, spent, budget, rng)

    def density(item):
        return len([pair for pair in inst.items[item]['resolves'] if pair not in state]) / inst.items[item]['cost']
    return max(plan, key=lambda item: (density(item), item))
