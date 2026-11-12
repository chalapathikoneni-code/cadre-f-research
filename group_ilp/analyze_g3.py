"""CADRE-G3 vs the fixed cheap policies on reported workloads (CADRE_G_PROTOCOL.md).

Usage: python group_ilp/analyze_g3.py G3.csv COMPARATORS.csv [G3.csv COMPARATORS.csv ...]
COMPARATORS.csv are selector result files (per-world rows for cadreF, myopic,
obligation_density on the same instances and worlds).
"""
import csv
import math
import statistics
import sys
from collections import defaultdict

TCRIT = {5: 2.571, 11: 2.201, 19: 2.093, 59: 2.001}
FIXED = ['cadreF', 'myopic', 'obligation_density']


def load(fn, keep):
    d = defaultdict(list)
    for r in csv.DictReader(open(fn)):
        if r['policy'] in keep:
            d[(r['group'], int(r['instance']), r['policy'])].append((int(r['world']), float(r['decided'])))
    return d


def ci(x):
    m = statistics.mean(x)
    h = TCRIT.get(len(x) - 1, 2.0) * statistics.stdev(x) / math.sqrt(len(x)) if len(x) > 1 else 0.0
    return m, m - h, m + h


def main():
    args = sys.argv[1:]
    for gfn, cfn in zip(args[::2], args[1::2]):
        g3 = load(gfn, {'cadreG3'})
        cmp_ = load(cfn, set(FIXED))
        groups = sorted({k[0] for k in g3})
        for g in groups:
            insts = sorted({k[1] for k in g3 if k[0] == g})
            mean = {}
            for p, src in [('cadreG3', g3)] + [(p, cmp_) for p in FIXED]:
                vals = []
                for i in insts:
                    rows = sorted(src[(g, i, p)])
                    vals.append(statistics.mean(v for _, v in rows))
                mean[p] = vals
            for i in insts:  # same worlds
                assert [w for w, _ in sorted(g3[(g, i, 'cadreG3')])] == [w for w, _ in sorted(cmp_[(g, i, 'cadreF')])]
            best = max(FIXED, key=lambda p: statistics.mean(mean[p]))
            m, lo, hi = ci([a - b for a, b in zip(mean['cadreG3'], mean[best])])
            mf, lof, hif = ci([a - b for a, b in zip(mean['cadreG3'], mean['cadreF'])])
            print(f'{gfn.split("/")[-1]:22s} {g:22s} n_inst={len(insts):3d} '
                  + ' '.join(f'{p}={statistics.mean(mean[p]):.2f}' for p in ['cadreG3'] + FIXED)
                  + f' | G3-best({best})={m:+.2f} [{lo:+.2f},{hi:+.2f}] | G3-F={mf:+.2f} [{lof:+.2f},{hif:+.2f}]')


if __name__ == '__main__':
    main()
