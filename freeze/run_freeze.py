"""Source-catalog paired evaluation and deterministic shared-item control.

Runs three generator regimes with 12 independent instances and ten paired
worlds each, then a deterministic shared-item stress instance. Outputs
instance-level results and confidence intervals.
"""
import sys, time, random, math, csv, statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
sys.path.insert(0,str(ROOT/'freeze'))
import wcaea_fixed as W
sys.modules['wcaea']=W
import cadre_opt as CO
CO.wcaea=W; CO.exp_true_gain=W.exp_true_gain; CO.decided=W.decided
import cadre_feasible as cf
cf.cadre_opt=CO
from gen2_independent import gen2, FAMILIES
Instance=W.Instance

POLS = {'cadreF': cf.pol_cadre_cover, 'cadre': CO.pol_completion_opt, 'myopic': W.pol_myopic}
SEED0, N_INST, N_WORLDS = 700001, 12, 10

def run_in_world(inst, pol, budget, world):
    state, spent, guard = {}, 0.0, 0; rng = random.Random(0); t0 = time.perf_counter()
    while spent < budget and W.n_decided(inst, state) < len(inst.queries) and guard < 10000:
        guard += 1
        e = pol(inst, state, spent, budget, rng)
        if e is None: break
        spent += inst.items[e]['cost']; state = W.apply_item(inst, state, e, world)
    return W.n_decided(inst, state), spent, time.perf_counter() - t0

def t_ci(diffs):
    n = len(diffs); m = statistics.mean(diffs)
    sd = statistics.stdev(diffs) if n > 1 else 0.0
    crit = 2.201  # t(0.975, df=11)
    half = crit * sd / math.sqrt(n) if n > 1 else 0.0
    return m, (m - half, m + half)

raw, summ = [], []
for fi, fam in enumerate(['sparse', 'dense', 'hetero']):
    per = {p: [] for p in POLS}; per_t = {p: [] for p in POLS}; per_u = {p: [] for p in POLS}
    for ii in range(N_INST):
        inst, B = gen2(SEED0 + fi * 1000 + ii, fam)
        wrng = random.Random(SEED0 + 555000 + fi * 1000 + ii)
        worlds = [W.draw_world(inst, wrng) for _ in range(N_WORLDS)]
        for pn, pol in POLS.items():
            ds, ss, ts = [], [], []
            for w in worlds:
                d, s, el = run_in_world(inst, pol, B, w); ds.append(d); ss.append(s); ts.append(el)
            per[pn].append(statistics.mean(ds)); per_t[pn].append(statistics.mean(ts)); per_u[pn].append(statistics.mean(ss) / B)
            raw.append(dict(family=fam, instance=ii, policy=pn, decided_mean=round(statistics.mean(ds), 3),
                            spent_mean=round(statistics.mean(ss), 2), budget=B, sec_per_run=round(statistics.mean(ts), 4)))
    for base in ('cadre', 'myopic'):
        diffs = [a - b for a, b in zip(per['cadreF'], per[base])]
        m, (lo, hi) = t_ci(diffs)
        summ.append(dict(family=fam, contrast=f'cadreF-{base}', mean_diff=round(m, 3), ci_lo=round(lo, 3), ci_hi=round(hi, 3),
                         F_mean=round(statistics.mean(per['cadreF']), 3), base_mean=round(statistics.mean(per[base]), 3),
                         wins=sum(1 for x in diffs if x > 1e-9), ties=sum(1 for x in diffs if abs(x) <= 1e-9),
                         F_sec=round(statistics.mean(per_t['cadreF']), 4), base_sec=round(statistics.mean(per_t[base]), 4),
                         F_budget_util=round(statistics.mean(per_u['cadreF']), 3), base_budget_util=round(statistics.mean(per_u[base]), 3)))
    print(fam, 'done', flush=True)

# Family G negative control (deterministic, single world per n)
def family_G(n):
    queries = ['D1', 'D2'] + [f'q{i}' for i in range(n)]
    obl = {q: ['o'] for q in queries}
    items = {'d1': {'cost': 1.0, 'resolves': {('D1', 'o')}}, 'd2': {'cost': 1.0, 'resolves': {('D2', 'o')}},
             'E': {'cost': 3.0, 'resolves': {(f'q{i}', 'o') for i in range(n)}}}
    pc = {(q, 'o'): f'g_{q}' for q in queries}; pf = {f'g_{q}': 0.0 for q in queries}
    inst = Instance(queries, obl, items, pc, pf, name=f'familyG_{n}')
    return inst, {(q, 'o'): 'pass' for q in queries}
for n in (10, 50):
    gi, gw = family_G(n)
    for pn, pol in POLS.items():
        d, s, el = run_in_world(gi, pol, 3.0, gw)
        raw.append(dict(family=f'familyG_n{n}', instance=0, policy=pn, decided_mean=d, spent_mean=s, budget=3.0, sec_per_run=round(el, 4)))
    summ.append(dict(family=f'familyG_n{n}', contrast='control', mean_diff='', ci_lo='', ci_hi='', F_mean='', base_mean=f'OPT={n}', wins='', ties='', F_sec='', base_sec='', F_budget_util='', base_budget_util=''))
    print(f'familyG n={n} done', flush=True)

with open(ROOT/'freeze/INDEPENDENT_RESULTS_RAW.csv', 'w', newline='') as fh:
    wtr = csv.DictWriter(fh, fieldnames=list(raw[0].keys())); wtr.writeheader(); wtr.writerows(raw)
with open(ROOT/'freeze/INDEPENDENT_ANALYSIS.csv', 'w', newline='') as fh:
    wtr = csv.DictWriter(fh, fieldnames=list(summ[0].keys())); wtr.writeheader(); wtr.writerows(summ)
print('FREEZE RUN COMPLETE')
