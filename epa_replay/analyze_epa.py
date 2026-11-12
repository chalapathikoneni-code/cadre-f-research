"""Analyze EPA replay results per PROTOCOL.md. Usage: python analyze_epa.py OUT_DIR TABLES_DIR"""
import csv
import math
import os
import statistics
import sys
from collections import defaultdict

OUT, TABLES = sys.argv[1], sys.argv[2]
T975 = {59: 2.001}


def load(page):
    fn = os.path.join(OUT, f'EPA_RAW_page{page}.csv')
    if not os.path.exists(fn):
        return None
    res = defaultdict(dict)     # (n, seed) -> policy -> row
    for r in csv.DictReader(open(fn)):
        res[(int(r['n']), int(r['seed']))][r['policy']] = r
    return res


def paired(res, n, a, b):
    d = [float(v[a]['decided']) - float(v[b]['decided'])
         for (nn, _), v in res.items() if nn == n and a in v and b in v]
    m = statistics.mean(d)
    h = T975.get(len(d) - 1, 2.0) * statistics.stdev(d) / math.sqrt(len(d))
    wins = sum(x > 0 for x in d)
    losses = sum(x < 0 for x in d)
    return len(d), m, m - h, m + h, wins, losses


lines = ['# EPA AirData replay results', '']
rates = list(csv.DictReader(open(os.path.join(TABLES, 'global_rates.csv'))))
lines += ['## Calibration (global failure rate)', '', '| obligation | 2024 (planner) | 2025 (truth) |',
          '|---|---|---|'] + [f"| {r['obligation']} | {r['rate_2024']} | {r['rate_2025']} |" for r in rates] + ['']

res = load(4096)
pols = ['cadreF', 'myopic', 'cadreCPC', 'two_step', 'cheapest_first', 'obligation_density']
for n in (25, 50):
    sub = {k: v for k, v in res.items() if k[0] == n}
    ref = statistics.mean(int(v['cadreF']['true_refutable']) for v in sub.values())
    items = statistics.mean(int(v['cadreF']['items']) for v in sub.values())
    lines += [f'## n = {n} ({len(sub)} instances, page 4096; mean items {items:.1f}, '
              f'mean truly refutable queries {ref:.2f})', '',
              '| policy | mean decided | mean sec/run | CADRE-F minus policy [95% CI] | F wins/losses |',
              '|---|---|---|---|---|']
    for p in pols:
        dec = statistics.mean(float(v[p]['decided']) for v in sub.values())
        sec = statistics.mean(float(v[p]['sec']) for v in sub.values())
        if p == 'cadreF':
            lines.append(f'| {p} | {dec:.3f} | {sec:.4f} | reference | |')
        else:
            k, m, lo, hi, w, l = paired(res, n, 'cadreF', p)
            lines.append(f'| {p} | {dec:.3f} | {sec:.4f} | {m:+.3f} [{lo:+.3f}, {hi:+.3f}] | {w}/{l} |')
    lines.append('')

lines += ['## Page-size sensitivity (primary contrast CADRE-F minus myopic)', '',
          '| page | n | diff [95% CI] | wins/losses |', '|---|---|---|---|']
for page in (1024, 4096, 16384):
    r = load(page)
    if r is None:
        continue
    for n in (25, 50):
        k, m, lo, hi, w, l = paired(r, n, 'cadreF', 'myopic')
        lines.append(f'| {page} | {n} | {m:+.3f} [{lo:+.3f}, {hi:+.3f}] | {w}/{l} |')
fn = os.path.join(OUT, 'EPA_SUMMARY.md')
open(fn, 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
