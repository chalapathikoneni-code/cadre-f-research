"""Paired CADRE-F-minus-policy contrasts for the tiered EPA variant (see TIERED_PROTOCOL.md)."""
import csv
import math
import statistics
import sys
from collections import defaultdict

T59 = 2.001  # two-sided 95% t, 59 df


def analyze(fn):
    d = defaultdict(dict)
    sec = defaultdict(list)
    for r in csv.DictReader(open(fn)):
        d[(int(r['n']), int(r['seed']))][r['policy']] = float(r['decided'])
        sec[(int(r['n']), r['policy'])].append(float(r['sec']))
    print('==', fn)
    for n in (25, 50):
        keys = sorted(k for k in d if k[0] == n)
        pols = list(d[keys[0]])
        for p in pols:
            mean = statistics.mean(d[k][p] for k in keys)
            line = f'n={n} {p:20s} mean={mean:7.3f} sec={statistics.mean(sec[(n, p)]):.4f}'
            if p != 'cadreF':
                diffs = [d[k]['cadreF'] - d[k][p] for k in keys]
                m = statistics.mean(diffs)
                h = T59 * statistics.stdev(diffs) / math.sqrt(len(diffs))
                w = sum(x > 0 for x in diffs)
                l = sum(x < 0 for x in diffs)
                line += f'  F-minus={m:+.3f} [{m-h:+.3f},{m+h:+.3f}] W/L={w}/{l}'
            print(line)


for fn in sys.argv[1:]:
    analyze(fn)
