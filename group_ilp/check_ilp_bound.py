"""Check the ILP re-plan guarantee: in every world the policy decides at least
A*(B), the all-pass ILP optimum at the start, and nobody decides more than
A*(B) + F(world). Also exact check vs the DP on small instances WITH sharing:
E[U(ILP)] >= OPT(B) - E[F].
Usage: python group_ilp/check_ilp_bound.py FAMILY   (EPA_* env as in run_selector.py), or 'small'
"""
import itertools
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'selector'))
sys.path.insert(0, str(ROOT / 'code'))
import run_selector as S  # noqa: E402
import ilp_replan as IL  # noqa: E402
import numpy as np  # noqa: E402
from scipy.optimize import Bounds, LinearConstraint, milp  # noqa: E402
from scipy.sparse import lil_matrix  # noqa: E402

W = S.W


def allpass_opt(inst, B):
    items = sorted(inst.items)
    qs = list(inst.queries)
    pairs = inst.pairs()
    A = lil_matrix((len(pairs) + 1, len(items) + len(qs)))
    qi = {q: len(items) + i for i, q in enumerate(qs)}
    for r, pr in enumerate(pairs):
        A[r, qi[pr[0]]] = 1.0
        for j, e in enumerate(items):
            if pr in inst.items[e]['resolves']:
                A[r, j] = -1.0
    for j, e in enumerate(items):
        A[len(pairs), j] = inst.items[e]['cost']
    hi = np.zeros(len(pairs) + 1)
    hi[-1] = B + 1e-9
    res = milp(np.concatenate([np.zeros(len(items)), -np.ones(len(qs))]),
               constraints=LinearConstraint(A.tocsr(), np.full(len(pairs) + 1, -np.inf), hi),
               integrality=np.ones(len(items) + len(qs)), bounds=Bounds(0, 1))
    assert res.status == 0
    return round(-res.fun)


def nfail(inst, w):
    return sum(any(w[(q, o)] == 'fail' for o in inst.obligations[q]) for q in inst.queries)


def check_family(fam):
    pols = [('ilp', IL.pol_ilp_replan), ('cadreG', None), ('cadreF', S.CF.pol_cadre_cover)]
    import cadre_group as CG
    pols[1] = ('cadreG', CG.pol_cadre_group_dense)
    n = viol_lower = viol_upper = 0
    for idx, g, inst, B, worlds in S.instances(fam):
        a = allpass_opt(inst, B)
        for w in worlds:
            d = S.run(inst, IL.pol_ilp_replan, B, w)
            n += 1
            viol_lower += d < a
            for name, p in pols[1:]:
                viol_upper += S.run(inst, p, B, w) > a + nfail(inst, w)
            viol_upper += d > a + nfail(inst, w)
    print(f'{fam}: {n} instance-worlds; ILP below A*(B): {viol_lower}; any policy above A*(B)+F: {viol_upper}')


def check_small():
    rng = random.Random(20261112)
    worst = 0.0
    for t in range(150):
        nq = rng.randint(2, 4)
        qs = [f'q{i}' for i in range(nq)]
        obl = {q: [f'o{j}' for j in range(rng.randint(1, 2))] for q in qs}
        pairs = [(q, o) for q in qs for o in obl[q]]
        ncl = rng.randint(2, 3)
        pc = {p: f'g{rng.randrange(ncl)}' for p in pairs}
        pf = {g: rng.choice([0.0, 0.1, 0.3]) for g in set(pc.values())}
        items = {}
        for k in range(rng.randint(3, 5)):  # shared items: subsets across queries
            sub = set(rng.sample(pairs, rng.randint(1, min(3, len(pairs)))))
            items[f'e{k}'] = {'cost': float(rng.randint(1, 3)), 'resolves': sub}
        for p in pairs:
            if not any(p in m['resolves'] for m in items.values()):
                items[f's{p[0]}{p[1]}'] = {'cost': float(rng.randint(1, 3)), 'resolves': {p}}
        inst = W.Instance(qs, obl, items, pc, pf)
        B = float(rng.randint(2, int(sum(m['cost'] for m in items.values()))))
        a = allpass_opt(inst, B)
        opt = W.exact_budgeted(inst, B)
        gs = sorted(pf)
        eu = ef = 0.0
        for combo in itertools.product((0, 1), repeat=len(gs)):
            prob = 1.0
            th = {}
            for g, f in zip(gs, combo):
                prob *= pf[g] if f else 1 - pf[g]
                th[g] = 'fail' if f else 'pass'
            if prob == 0:
                continue
            w = {p: th[pc[p]] for p in pairs}
            d = S.run(inst, IL.pol_ilp_replan, B, w)
            assert d >= a, ('lower bound failed', t, d, a)
            eu += prob * d
            ef += prob * nfail(inst, w)
        assert opt <= a + ef + 1e-9, ('upper bound failed', t, opt, a, ef)
        assert eu >= opt - ef - 1e-9
        worst = max(worst, opt - eu)
    print(f'small shared instances: 150 checked exactly; ILP >= A*(B) in every world, OPT <= A*(B) + E[F]; '
          f'max OPT - E[U(ILP)] = {worst:.3f}')


if __name__ == '__main__':
    if sys.argv[1] == 'small':
        check_small()
    else:
        check_family(sys.argv[1])
