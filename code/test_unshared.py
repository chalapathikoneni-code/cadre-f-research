"""Exact check of the unshared-evidence proposition (paper, Prop. 1).

Random instances in which every item witnesses pairs of a single query
(no shared items); clusters may still span queries (correlated outcomes).
Let H*(q) be the exact minimum cover cost of q, sorted ascending, and
k* = max{k : H*_(1) + ... + H*_(k) <= B}. Checks, by exhaustive world
enumeration and the exact adaptive DP:
  (a) cheapest certified completion (CCF) decides >= k* in every world;
  (b) every implemented policy decides <= k* + F(world) per world, and
      OPT(B) <= k* + E[F], F = #queries with a failing pair;
  (c) with all failure probabilities 0, CCF value == OPT(B).
Run: PYTHONHASHSEED=0 python code/test_unshared.py
"""
import itertools
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wcaea_fixed as wcaea  # noqa: E402
sys.modules['wcaea'] = wcaea
import cadre_opt as CO  # noqa: E402
CO.wcaea = wcaea
CO.exp_true_gain = wcaea.exp_true_gain
CO.decided = wcaea.decided
import cadre_feasible as CF  # noqa: E402
CF.cadre_opt = CO

_pd = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lookahead_baselines.py')
_ns = {'__file__': _pd, '__name__': 'lookahead_baselines_defs'}
exec(compile(open(_pd).read().split('POLS = {')[0], _pd, 'exec'), _ns)
CCF = _ns['pol_cheapest_first']


def gen(rng, deterministic):
    nq = rng.randint(2, 4)
    queries = [f'q{idx}' for idx in range(nq)]
    obl = {query: [f'o{idx}' for idx in range(rng.randint(1, 3))] for query in queries}
    items, pc, pf = {}, {}, {}
    ncl = rng.randint(2, 4)
    for cluster_idx in range(ncl):
        pf[f'g{cluster_idx}'] = 0.0 if deterministic else rng.choice([0.0, 0.05, 0.2, 0.4])
    for query in queries:
        for oblig in obl[query]:
            pc[(query, oblig)] = f'g{rng.randrange(ncl)}'  # clusters may span queries
        pairs = [(query, oblig) for oblig in obl[query]]
        for item_idx in range(rng.randint(len(pairs), len(pairs) + 2)):  # private items only
            subset = set(rng.sample(pairs, rng.randint(1, len(pairs))))
            items[f'{query}_e{item_idx}'] = {'cost': float(rng.randint(1, 4)), 'resolves': subset}
        for oblig in obl[query]:  # every pair coverable
            if not any((query, oblig) in meta['resolves'] for meta in items.values()):
                items[f'{query}_s{oblig}'] = {'cost': float(rng.randint(1, 4)), 'resolves': {(query, oblig)}}
    used = sorted(set(pc.values()))
    pf = {cluster: pf[cluster] for cluster in used}
    inst = wcaea.Instance(queries, obl, items, pc, pf, name='unshared')
    budget = float(rng.randint(2, int(sum(meta['cost'] for meta in items.values()))))
    return inst, budget


def worlds(inst):
    clusters = list(inst.cluster_pfail)
    for combo in itertools.product((0, 1), repeat=len(clusters)):
        prob = 1.0
        theta = {}
        for cluster, fail in zip(clusters, combo):
            pfail = inst.cluster_pfail[cluster]
            prob *= pfail if fail else 1 - pfail
            theta[cluster] = 'fail' if fail else 'pass'
        if prob > 0:
            yield prob, {pair: theta[inst.pair_cluster[pair]] for pair in inst.pairs()}


def run(inst, pol, budget, world):
    st, spent = {}, 0.0
    rng = random.Random(0)
    while spent < budget and wcaea.n_decided(inst, st) < len(inst.queries):
        item = pol(inst, st, spent, budget, rng)
        if item is None:
            break
        assert inst.items[item]['cost'] <= budget - spent + 1e-9
        spent += inst.items[item]['cost']
        st = wcaea.apply_item(inst, st, item, world)
    return wcaea.n_decided(inst, st)


def main():
    rng = random.Random(20261111)
    n_cases = n_det = ccf_opt = cf_opt = 0
    worst_gap_ratio = 0.0
    for trial in range(300):
        det = trial % 3 == 0
        inst, budget = gen(rng, det)
        cover_costs = sorted(CF.completion_plan(inst, {}, query)[1] for query in inst.queries)
        kstar, acc = 0, 0.0
        for cost in cover_costs:
            if acc + cost <= budget + 1e-9:
                acc += cost
                kstar += 1
            else:
                break
        opt = wcaea.exact_budgeted(inst, budget)
        e_ccf = e_cf = e_f = 0.0
        for prob, world in worlds(inst):
            failed_queries = sum(any(world[(query, oblig)] == 'fail' for oblig in inst.obligations[query]) for query in inst.queries)
            decided_ccf = run(inst, CCF, budget, world)
            assert decided_ccf >= kstar, ('(a) failed', trial, decided_ccf, kstar)
            decided_cf = run(inst, CF.pol_cadre_cover, budget, world)
            for name, decided_value in (('ccf', decided_ccf), ('cadreF', decided_cf), ('myopic', run(inst, wcaea.pol_myopic, budget, world)),
                             ('density', run(inst, wcaea.pol_sssc, budget, world))):
                assert decided_value <= kstar + failed_queries, ('(b) per-world failed', trial, name, decided_value, kstar, failed_queries)
            e_ccf += prob * decided_ccf
            e_cf += prob * decided_cf
            e_f += prob * failed_queries
        assert opt <= kstar + e_f + 1e-9, ('(b) failed', trial, opt, kstar, e_f)
        if det:
            assert abs(e_ccf - opt) < 1e-9, ('(c) failed', trial, e_ccf, opt)
            n_det += 1
        n_cases += 1
        ccf_opt += abs(e_ccf - opt) < 1e-9
        cf_opt += abs(e_cf - opt) < 1e-9
        if e_f > 0:
            worst_gap_ratio = max(worst_gap_ratio, (opt - e_ccf) / e_f)
    print(f'PASS: {n_cases} unshared instances ({n_det} deterministic); (a) CCF >= k* in every world, '
          f'(b) U <= k* + F(world) per world for CCF, CADRE-F, myopic and density, and OPT <= k* + E[F], '
          f'(c) CCF = OPT when deterministic.')
    print(f'CCF optimal on {ccf_opt}/{n_cases}, CADRE-F optimal on {cf_opt}/{n_cases}; '
          f'max (OPT - CCF) / E[F] = {worst_gap_ratio:.3f}')


if __name__ == '__main__':
    main()
