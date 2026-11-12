"""EPA AirData replay: build instances and run policies (see PROTOCOL.md).

Usage: python run_epa.py --tables tables --code CODE_DIR --out out [--page 4096]
       [--policies cadreF,myopic,...]
CODE_DIR must contain common.py, wcaea_fixed.py, cadre_feasible.py,
cadre_opt.py, instances.py and lookahead_baselines.py (policy code is used unchanged).
"""
import argparse
import csv
import math
import os
import random
import statistics
import sys
import time
from collections import defaultdict

ap = argparse.ArgumentParser()
ap.add_argument('--tables', required=True)
ap.add_argument('--code', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--page', type=int, default=4096)
ap.add_argument('--policies', default='cadreF,myopic,cadreCPC,two_step,cheapest_first,obligation_density')
ap.add_argument('--sizes', default='25,50')
ap.add_argument('--seed-starts', default='9000,9100', help='first seed for n=25 and n=50 (60 each)')
args = ap.parse_args()
sys.path.insert(0, args.code)

from common import W, CF, CO, run_policy  # noqa: E402

# Baselines from lookahead_baselines.py, definitions only (skip its experiment loop).
pd_path = os.path.join(args.code, 'lookahead_baselines.py')
src = open(pd_path).read().split('POLS = {')[0]
src = src.replace("OUT = os.environ.get('CADRE_OUT', 'out/strong_baselines')", '')
ns = {'__file__': pd_path, '__name__': 'lookahead_baselines_defs'}
exec(compile(src, pd_path, 'exec'), ns)

POLS = {'cadreF': CF.pol_cadre_cover, 'myopic': W.pol_myopic,
        'cadreCPC': CO.pol_completion_opt, 'two_step': ns['pol_two_step'],
        'cheapest_first': ns['pol_cheapest_first'], 'obligation_density': W.pol_sssc}
OBL = ('reg', 'method', 'complete', 'event')
_s25, _s50 = (int(x) for x in args.seed_starts.split(','))
SEEDS = {25: (range(_s25, _s25 + 60), 6), 50: (range(_s50, _s50 + 60), 12)}


def load(name):
    with open(os.path.join(args.tables, name)) as fh:
        return list(csv.DictReader(fh))


md = load('monitor_days_2025.csv')
by_month_site = defaultdict(lambda: defaultdict(list))
for r in md:
    by_month_site[r['month']][r['site']].append(r)
file_bytes = {(r['site'], r['month']): int(r['bytes']) for r in load('file_bytes_2025.csv')}
reg_bytes = {r['site']: int(r['bytes']) for r in load('reg_bytes.csv')}
pf_mon = {r['mon']: r for r in load('pfail_monitor.csv')}
pf_site = {r['site']: float(r['event']) for r in load('pfail_site_event.csv')}
g24 = {r['obligation']: float(r['rate_2024']) for r in load('global_rates.csv')}


def cost(nbytes):
    return 1 + math.ceil(nbytes / args.page)


def build(seed, n, nsites):
    rng = random.Random(seed)
    month = rng.choice(sorted(by_month_site))
    sites = rng.sample(sorted(by_month_site[month]), nsites)
    pool = sorted((r for s in sites for r in by_month_site[month][s]), key=lambda r: (r['mon'], r['date']))
    rows = rng.sample(pool, n)
    queries, obligations, items, pc, cpf, world = [], {}, {}, {}, {}, {}
    site_q = defaultdict(list)
    for r in rows:
        q = f"{r['mon']}|{r['date']}"
        queries.append(q)
        obligations[q] = list(OBL)
        site_q[r['site']].append(q)
        for ob in OBL:
            world[(q, ob)] = 'fail' if r[ob] == '1' else 'pass'
        # Planner model: one latent per (monitor, obligation) (Amendment 1).
        pm = pf_mon.get(r['mon'])
        for ob in ('reg', 'method', 'complete'):
            g = f"{ob}|{r['mon']}"
            pc[(q, ob)] = g
            cpf[g] = float(pm[ob]) if pm else g24[ob]
        g = f"event|{r['mon']}"
        pc[(q, 'event')] = g
        cpf[g] = pf_site.get(r['site'], g24['event'])
        items[f'REC|{q}'] = {'cost': cost(int(r['rec_bytes'])),
                             'resolves': {(q, 'complete'), (q, 'event')}}
    for s, qs in site_q.items():
        items[f'REG|{s}'] = {'cost': cost(reg_bytes.get(s, 0)),
                             'resolves': {(q, ob) for q in qs for ob in ('reg', 'method')}}
        items[f'FILE|{s}|{month}'] = {'cost': cost(file_bytes[(s, month)]),
                                      'resolves': {(q, ob) for q in qs for ob in ('complete', 'event')}}
    inst = W.Instance(queries, obligations, items, pc, cpf, name=f'epa_{seed}')
    B = float(round(0.4 * sum(m['cost'] for m in items.values())))
    return inst, B, world, month


def main():
    os.makedirs(args.out, exist_ok=True)
    pols = args.policies.split(',')
    fn = os.path.join(args.out, f'EPA_RAW_page{args.page}.csv')
    with open(fn, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['n', 'seed', 'month', 'items', 'budget', 'true_refutable', 'policy', 'decided', 'spent', 'sec'])
        for n in [int(x) for x in args.sizes.split(',')]:
            seeds, nsites = SEEDS[n]
            for seed in seeds:
                inst, B, world, month = build(seed, n, nsites)
                refutable = sum(1 for q in inst.queries if any(world[(q, o)] == 'fail' for o in OBL))
                for p in pols:
                    t0 = time.perf_counter()
                    d, s, _ = run_policy(inst, POLS[p], B, world)
                    w.writerow([n, seed, month, len(inst.items), B, refutable, p, d, s,
                                round(time.perf_counter() - t0, 4)])
                fh.flush()
                print(n, seed, 'done', flush=True)
    print('wrote', fn)


if __name__ == '__main__':
    main()
