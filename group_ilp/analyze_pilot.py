"""Per-group means and paired CIs of each pilot variant vs the best fixed cheap policy."""
import csv
import math
import statistics
import sys
from collections import defaultdict

FIXED = ['cadreF', 'myopic', 'obligation_density']


def main():
    per = defaultdict(lambda: defaultdict(list))
    for fn in sys.argv[1:]:
        for r in csv.DictReader(open(fn)):
            per[r['group']][(r['seed'], r['policy'])].append(float(r['decided']))
    for g in sorted(per):
        seeds = sorted({s for s, _ in per[g]})
        pols = sorted({p for _, p in per[g]})
        m = {p: [statistics.mean(per[g][(s, p)]) for s in seeds] for p in pols}
        best = max(FIXED, key=lambda p: statistics.mean(m[p]))
        line = f'{g:20s} ' + ' '.join(f'{p}={statistics.mean(m[p]):.2f}' for p in pols)
        for v in [p for p in pols if p not in FIXED]:
            d = [a - b for a, b in zip(m[v], m[best])]
            h = 2.0 * statistics.stdev(d) / math.sqrt(len(d)) if len(d) > 1 else 0.0
            mu = statistics.mean(d)
            line += f' | {v}-{best}: {mu:+.2f} [{mu - h:+.2f},{mu + h:+.2f}]'
        print(line)


if __name__ == '__main__':
    main()
