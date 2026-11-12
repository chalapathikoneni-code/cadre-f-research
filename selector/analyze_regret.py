"""Summarize run_selector_regret.py outputs: mean selection regret (decisions) by group and K.

Usage: python selector/analyze_regret.py REG_*.csv
"""
import csv
import statistics
import sys
from collections import defaultdict


def main():
    d = defaultdict(list)
    for fn in sys.argv[1:]:
        for r in csv.DictReader(open(fn)):
            d[(r['group'], r['misspec'], int(r['K']))].append((float(r['mean_regret']), float(r['p_wrong'])))
    groups = sorted({(g, m) for g, m, _ in d})
    print(f'{"group":24s} {"misspec":>7s} ' + ' '.join(f'K={k:<2d} regret/p_wrong' for k in (5, 10, 20, 40)))
    for g, m in groups:
        cells = []
        for k in (5, 10, 20, 40):
            v = d.get((g, m, k), [])
            if v:
                cells.append(f'{statistics.mean(x for x, _ in v):6.3f}/{statistics.mean(y for _, y in v):.2f}      ')
        print(f'{g:24s} {m:>7s} ' + ' '.join(cells))
    allk = defaultdict(list)
    for (g, m, k), v in d.items():
        if m == '1.0':
            allk[k] += [x for x, _ in v]
    print('pooled (correct model):', {k: round(statistics.mean(v), 3) for k, v in sorted(allk.items())},
          'max instance regret at K=20:', round(max(allk[20]), 3) if allk[20] else None)


if __name__ == '__main__':
    main()
