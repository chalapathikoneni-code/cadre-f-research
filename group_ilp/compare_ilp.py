"""ILP re-plan baseline vs CADRE-G3 (and best fixed cheap policy), paired by instance and world.
Usage: python group_ilp/compare_ilp.py
"""
import csv
import glob
import math
import statistics
from collections import defaultdict

T = {5: 2.571, 11: 2.201, 19: 2.093, 59: 2.001}


def ci(x):
    m = statistics.mean(x)
    h = T[len(x) - 1] * statistics.stdev(x) / math.sqrt(len(x))
    return f'{m:+.3f} [{m - h:+.3f},{m + h:+.3f}]'


def load(files, pol=None):
    d = defaultdict(list)
    extra = defaultdict(list)
    for fn in files:
        for r in csv.DictReader(open(fn)):
            if pol and r['policy'] != pol:
                continue
            d[(r['group'], int(r['instance']), r['policy'])].append(float(r['decided']))
            if 'sec' in r:
                extra[(r['group'], r['policy'])].append(float(r['sec']))
            if 'nonoptimal' in r:
                extra[(r['group'], 'nonopt')].append(int(r['nonoptimal']))
    return {k: statistics.mean(v) for k, v in d.items()}, extra


SETS = [('holdout', 'SEL_holdout.csv'), ('catalog', 'SEL_catalog.csv'), ('stress', 'SEL_stress.csv'),
        ('pm25', 'SEL_epa.csv'), ('ozone', 'SEL3_ozone.csv'), ('tieredM10', 'SEL_tieredM10.csv'),
        ('tieredM5', 'SEL_tieredM5.csv'), ('n200', 'SEL_n200_*.csv')]
for name, base in SETS:
    ilp, ex = load(sorted(glob.glob(f'group_ilp/ilp/ILP_{name}*.csv')), 'ilp')
    g3, exg = load(sorted(glob.glob(f'group_ilp/results/G3_{name}*.csv')), 'cadreG3')
    fx, _ = load(sorted(glob.glob(f'selector/results/{base}')))
    for grp in sorted({k[0] for k in ilp}):
        ins = sorted({k[1] for k in ilp if k[0] == grp})
        if not all((grp, i, 'cadreG3') in g3 for i in ins) or (len(ins) - 1) not in T:
            print(f'{name:9s} {grp:20s} incomplete ({len(ins)} instances)')
            continue
        I = [ilp[(grp, i, 'ilp')] for i in ins]
        G = [g3[(grp, i, 'cadreG3')] for i in ins]
        best = max(('cadreF', 'myopic', 'obligation_density'),
                   key=lambda p: statistics.mean(fx[(grp, i, p)] for i in ins))
        Bf = [fx[(grp, i, best)] for i in ins]
        nonopt = sum(ex[(grp, 'nonopt')])
        print(f'{name:9s} {grp:20s} ILP={statistics.mean(I):.3f} G3={statistics.mean(G):.3f} '
              f'{best}={statistics.mean(Bf):.3f} | ILP-G3 {ci([a - b for a, b in zip(I, G)])} '
              f'| ILP-best {ci([a - b for a, b in zip(I, Bf)])} | ILP s/run {statistics.mean(ex[(grp, "ilp")]):.3f} '
              f'| non-optimal solves {nonopt}')
