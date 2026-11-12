"""ILP re-plan vs two-step lookahead on the real replays, paired by instance.
Usage: python group_ilp/compare_ilp_twostep.py
"""
import csv
import math
import statistics
from collections import defaultdict


def ci(x):
    m = statistics.mean(x)
    h = 2.001 * statistics.stdev(x) / math.sqrt(len(x))
    return f'{m:+.2f} [{m - h:+.2f},{m + h:+.2f}]'


for name, ifn, raw, starts in [('pm25', 'group_ilp/ilp/ILP_pm25.csv', 'epa_replay/results/EPA_RAW_page4096.csv', (9000, 9100)),
                               ('ozone', 'group_ilp/ilp/ILP_ozone.csv', 'epa_replay/ozone_results/OZONE_RAW_page4096.csv',
                                (9200, 9300))]:
    il = defaultdict(list)
    for r in csv.DictReader(open(ifn)):
        il[int(r['instance'])].append(float(r['decided']))
    two = {}
    for r in csv.DictReader(open(raw)):
        if r['policy'] == 'two_step':
            n, s = int(r['n']), int(r['seed'])
            two[(s - starts[0]) if n == 25 else 60 + (s - starts[1])] = float(r['decided'])
    for n, rng in ((25, range(0, 60)), (50, range(60, 120))):
        print(name, n, 'ILP', round(statistics.mean(statistics.mean(il[i]) for i in rng), 2),
              'two-step', round(statistics.mean(two[i] for i in rng), 2),
              'ILP-two', ci([statistics.mean(il[i]) - two[i] for i in rng]))
