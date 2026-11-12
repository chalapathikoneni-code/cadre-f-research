"""Recompute every v7 number from raw files: per-group means of F, G3, Myo, Dens,
SEL3, SEL-G; G3 - best(F,Myo,Dens); SEL-G - best(F,G3,Myo,Dens). Paired over instances.
Usage: python group_ilp/cadre_g_numbers.py
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


def load(files, rename=None):
    d = defaultdict(list)
    for fn in files:
        for r in csv.DictReader(open(fn)):
            p = r['policy']
            if rename and p in rename:
                p = rename[p]
            d[(r['group'], int(r['instance']), p)].append(float(r['decided']))
    return {k: statistics.mean(v) for k, v in d.items()}


SETS = [
    ('holdout', ['selector/results/SEL_holdout.csv'], ['group_ilp/results/G3_holdout.csv'], ['selector/results_regret/SELG_holdout.csv']),
    ('catalog', ['selector/results/SEL_catalog.csv'], ['group_ilp/results/G3_catalog.csv'], ['selector/results_regret/SELG_catalog.csv']),
    ('stress', ['selector/results/SEL_stress.csv'], ['group_ilp/results/G3_stress.csv'], ['selector/results_regret/SELG_stress.csv']),
    ('pm25', ['selector/results/SEL_epa.csv'], ['group_ilp/results/G3_pm25.csv'], ['selector/results_regret/SELG_pm25.csv']),
    ('ozone', ['selector/results/SEL3_ozone.csv'], ['group_ilp/results/G3_ozone.csv'], ['selector/results_regret/SELG_ozone.csv']),
    ('tieredM10', ['selector/results/SEL_tieredM10.csv'], ['group_ilp/results/G3_tieredM10.csv'], ['selector/results_regret/SELG_tieredM10.csv']),
    ('tieredM5', ['selector/results/SEL_tieredM5.csv'], ['group_ilp/results/G3_tieredM5.csv'], ['selector/results_regret/SELG_tieredM5.csv']),
    ('n200', sorted(glob.glob('selector/results/SEL_n200_*.csv')), sorted(glob.glob('group_ilp/results/G3_n200_*.csv')),
     sorted(glob.glob('selector/results_regret/SELG_n200_*.csv'))),
]

for name, sel3, g3, selg in SETS:
    base = load(sel3)
    g = load(g3)
    sg = load(selg, rename={'selector': 'selectorG'})
    for grp in sorted({k[0] for k in g}):
        ins = sorted({k[1] for k in g if k[0] == grp})
        if not all((grp, i, 'selectorG') in sg for i in ins):
            print(name, grp, 'SEL-G incomplete')
            continue
        col = {p: [base[(grp, i, p)] for i in ins] for p in ('cadreF', 'myopic', 'obligation_density', 'selector')}
        col['G3'] = [g[(grp, i, 'cadreG3')] for i in ins]
        col['SELG'] = [sg[(grp, i, 'selectorG')] for i in ins]
        assert col['G3'] == [sg[(grp, i, 'cadreG3')] for i in ins], 'G3 differs between runs'
        fixed = ['cadreF', 'myopic', 'obligation_density']
        bf = max(fixed, key=lambda p: statistics.mean(col[p]))
        b4 = max(fixed + ['G3'], key=lambda p: statistics.mean(col[p]))
        print(f'{name:9s} {grp:20s} ' + ' '.join(f'{p}={statistics.mean(v):.3f}' for p, v in col.items())
              + f' | G3-{bf}: {ci([a - b for a, b in zip(col["G3"], col[bf])])}'
              + f' | SELG-{b4}: {ci([a - b for a, b in zip(col["SELG"], col[b4])])}')
