"""(1) CADRE-G3 vs CADRE-F/myopic/density on the six 200-query instances (pooled).
(2) CADRE-G3 vs two-step lookahead on the real replays, paired by instance.
(3) Mean G3 planning seconds per run per group.
Usage: python group_ilp/compare_g3_extra.py
"""
import csv
import glob
import math
import statistics
from collections import defaultdict

TCRIT = {5: 2.571, 59: 2.001}


def ci(x):
    m = statistics.mean(x)
    h = TCRIT.get(len(x) - 1, 2.0) * statistics.stdev(x) / math.sqrt(len(x))
    return f'{m:+.2f} [{m - h:+.2f},{m + h:+.2f}]'


def per_inst(files, pols):
    d = defaultdict(list)
    for fn in files:
        for r in csv.DictReader(open(fn)):
            if r['policy'] in pols:
                d[(int(r['instance']), r['policy'])].append(float(r['decided']))
    return {k: statistics.mean(v) for k, v in d.items()}


g = per_inst(glob.glob('group_ilp/results/G3_n200_*.csv'), {'cadreG3'})
c = per_inst(glob.glob('selector/results/SEL_n200_*.csv'), {'cadreF', 'myopic', 'obligation_density'})
ins = sorted({i for i, _ in g})
print('n200', {p: round(statistics.mean(c[(i, p)] for i in ins), 2) for p in ('cadreF', 'myopic', 'obligation_density')},
      'G3', round(statistics.mean(g[(i, 'cadreG3')] for i in ins), 2),
      'G3-F', ci([g[(i, 'cadreG3')] - c[(i, 'cadreF')] for i in ins]))

for name, gfn, raw, starts in [('pm25', 'group_ilp/results/G3_pm25.csv', 'epa_replay/results/EPA_RAW_page4096.csv', (9000, 9100)),
                               ('ozone', 'group_ilp/results/G3_ozone.csv', 'epa_replay/ozone_results/OZONE_RAW_page4096.csv', (9200, 9300))]:
    g = per_inst([gfn], {'cadreG3'})
    two = {}
    for r in csv.DictReader(open(raw)):
        if r['policy'] == 'two_step':
            n, s = int(r['n']), int(r['seed'])
            idx = (s - starts[0]) if n == 25 else 60 + (s - starts[1])
            two[idx] = float(r['decided'])
    for n, rng in ((25, range(0, 60)), (50, range(60, 120))):
        print(name, n, 'G3', round(statistics.mean(g[(i, 'cadreG3')] for i in rng), 2),
              'two-step', round(statistics.mean(two[i] for i in rng), 2),
              'G3-two', ci([g[(i, 'cadreG3')] - two[i] for i in rng]))

for fn in sorted(glob.glob('group_ilp/results/G3_*.csv')):
    secs = defaultdict(list)
    for r in csv.DictReader(open(fn)):
        secs[r['group']].append(float(r['sec']))
    print(fn, {k: round(statistics.mean(v), 3) for k, v in secs.items()})
