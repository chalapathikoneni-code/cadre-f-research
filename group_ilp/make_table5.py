"""Emit Table V rows (LaTeX) and contrasts from raw files: F, G3, ILP, Myo, Dens,
SEL3, SEL-G, SEL-I; G3 - best(F,Myo,Dens); ILP - G3; SEL-I - best of all five cheap.
Usage: python group_ilp/make_table5.py [--latex]
"""
import csv
import glob
import math
import statistics
import sys
from collections import defaultdict

T = {5: 2.571, 11: 2.201, 19: 2.093, 59: 2.001}


def ci(x):
    m = statistics.mean(x)
    h = T[len(x) - 1] * statistics.stdev(x) / math.sqrt(len(x))
    return m, m - h, m + h


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
    ('holdout', 'F4', 'SEL_holdout.csv'), ('catalog', 'Cat.', 'SEL_catalog.csv'),
    ('stress', 'File', 'SEL_stress.csv'), ('pm25', 'PM2.5', 'SEL_epa.csv'),
    ('ozone', 'Ozone', 'SEL3_ozone.csv'), ('tieredM10', 'Tiered', 'SEL_tieredM10.csv'),
    ('tieredM5', 'TieredM5', 'SEL_tieredM5.csv'), ('n200', 'F4', 'SEL_n200_*.csv'),
]
LABEL = {'holdout_n25': 'F4, 25', 'holdout_n50': 'F4, 50', 'catalog_sparse': 'Cat.\\ sparse',
         'catalog_dense': 'Cat.\\ dense', 'catalog_hetero': 'Cat.\\ hetero.', 'stress_R1_sparse': 'File sparse',
         'stress_R2_complement': 'File compl.', 'stress_R3_hetero': 'File hetero.', 'stress_R4_hub': 'File hub',
         'n200': 'F4, 200'}
ORDER = ['holdout_n25', 'holdout_n50', 'catalog_sparse', 'catalog_dense', 'catalog_hetero', 'stress_R1_sparse',
         'stress_R2_complement', 'stress_R3_hetero', 'stress_R4_hub']


def f2(x):
    return f'{x:.2f}'


def fci(t):
    m, lo, hi = t
    return f'${m:+.2f}\\,[{lo:.2f},{hi:.2f}]$'


def main():
    latex = '--latex' in sys.argv
    out = []
    for name, lab, base in SETS:
        fx = load(sorted(glob.glob(f'selector/results/{base}')))
        g3 = load(sorted(glob.glob(f'group_ilp/results/G3_{name}*.csv')))
        il = load(sorted(glob.glob(f'group_ilp/ilp/ILP_{name}*.csv')))
        sg = load(sorted(glob.glob(f'selector/results_regret/SELG_{name}*.csv')), {'selector': 'selG'})
        si = load(sorted(glob.glob(f'selector/results_regret/SELI_{name}*.csv')), {'selector': 'selI'})
        for grp in sorted({k[0] for k in g3}):
            ins = sorted({k[1] for k in g3 if k[0] == grp})
            need = [(il, 'ilp'), (sg, 'selG'), (si, 'selI')]
            if not all((grp, i, p) in d for d, p in need for i in ins):
                print(name, grp, 'INCOMPLETE')
                continue
            c = {p: [fx[(grp, i, p)] for i in ins] for p in ('cadreF', 'myopic', 'obligation_density', 'selector')}
            c['G3'] = [g3[(grp, i, 'cadreG3')] for i in ins]
            c['ILP'] = [il[(grp, i, 'ilp')] for i in ins]
            c['SELG'] = [sg[(grp, i, 'selG')] for i in ins]
            c['SELI'] = [si[(grp, i, 'selI')] for i in ins]
            assert c['G3'] == [si[(grp, i, 'cadreG3')] for i in ins]
            assert c['ILP'] == [si[(grp, i, 'ilp')] for i in ins], (name, grp, 'ILP differs between runs')
            mean = {p: statistics.mean(v) for p, v in c.items()}
            bf = max(('cadreF', 'myopic', 'obligation_density'), key=lambda p: mean[p])
            b5 = max(('cadreF', 'myopic', 'obligation_density', 'G3', 'ILP'), key=lambda p: mean[p])
            gb = ci([a - b for a, b in zip(c['G3'], c[bf])])
            ig = ci([a - b for a, b in zip(c['ILP'], c['G3'])])
            sb = ci([a - b for a, b in zip(c['SELI'], c[b5])])
            label = LABEL.get(grp, f'{lab}, {grp[-2:]}')
            if name == 'tieredM5':
                label = f'Tiered M5, {grp[-2:]}'
            row = (f'{label} & ' + ' & '.join(f2(mean[p]) for p in ('cadreF', 'G3', 'ILP', 'myopic', 'obligation_density',
                                                                     'selector', 'SELG', 'SELI'))
                   + f' & {fci(gb)} & {fci(ig)} & {fci(sb)} \\\\')
            out.append((name, grp, row, b5, sb))
    for name, grp, row, b5, sb in out:
        print(row if latex else f'{name} {grp} best5={b5} SELI-best5={sb[0]:+.3f} [{sb[1]:+.3f},{sb[2]:+.3f}] || {row}')


if __name__ == '__main__':
    main()
