"""PAOTR-style baseline (adapted), after Casanova et al. Queries are
processed one at a time in cheapest-cost-to-decide order. Within a query,
tests are ordered by the classical ratio rule (refutation-first for a
conjunctive goal). The planner does not exploit cross-query sharing in its
plan; items already bought are not re-bought, which is free reuse in any
implementation. This is an adaptation: PAOTR models each query as a Boolean
tree whose leaves may be shared streams, but our items are arbitrary
covering sets, so exact PAOTR does not apply unchanged."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wcaea_fixed as wcaea
from wcaea_fixed import decided, _cost_to_decide

def pol_paotr(inst, state, spent, budget, rng):
    cand = wcaea._remaining(inst, state, spent, budget)
    if not cand: return None
    undecided = [query for query in inst.queries if not decided(inst, state, query)]
    if not undecided: return None
    target_query = min(undecided, key=lambda candidate: _cost_to_decide(inst, state, candidate))
    # within-query ratio rule: among items resolving q's open obligations,
    # pick min cost / pfail-of-its-clusters (refutation-seeking order for a
    # conjunctive goal; ties -> larger coverage of q's open obligations)
    best, best_key = None, None
    for item in cand:
        relevant = [pair for pair in inst.items[item]['resolves'] if pair[0] == target_query and pair not in state]
        if not relevant: continue
        pfail = max(inst.cluster_pfail[inst.pair_cluster[pair]] for pair in relevant)
        key = (inst.items[item]['cost'] / max(1e-9, pfail), -len(relevant))
        if best_key is None or key < best_key: best_key, best = key, item
    return best if best is not None else cand[0]
