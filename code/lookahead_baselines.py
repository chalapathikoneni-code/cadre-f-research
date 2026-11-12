import sys, os, csv, math, random, statistics, itertools
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
import cadre_feasible as CF

OUT = os.environ.get('CADRE_OUT', 'out/strong_baselines')

def pol_cheapest_first(inst, state, spent, budget, rng):
    """Baseline A: follow the cheapest certified completion plan, item by item
    (ties by item id). Falls back to myopic when no query is completable."""
    best = None
    for query in inst.queries:
        if wcaea.decided(inst, state, query): continue
        plan, cost = CF.completion_plan(inst, state, query)
        if plan and cost <= budget - spent + 1e-9:
            if best is None or cost < best[1] or (cost == best[1] and min(plan) < min(best[0])):
                best = (plan, cost)
    if best is None: return wcaea.pol_myopic(inst, state, spent, budget, rng)
    return min(best[0])

def pol_two_step(inst, state, spent, budget, rng):
    """Baseline B: two-step lookahead myopic. Score item e1 by exact one-step
    gain + best discounted one-step gain available afterwards (cluster-
    conditioned exact gains both steps). Deterministic ties by item id."""
    rem = budget - spent
    cand = [item for item in inst.items if inst.items[item]['cost'] <= rem + 1e-9 and wcaea.item_useful(inst, state, item)]
    if not cand: return None
    def gain_after(state2, rem2, first_item):
        best2 = 0.0
        for second_item in inst.items:
            if second_item == first_item: continue
            if inst.items[second_item]['cost'] <= rem2 + 1e-9 and wcaea.item_useful(inst, state2, second_item):
                best2 = max(best2, wcaea.exp_true_gain(inst, state2, second_item) / inst.items[second_item]['cost'])
        return best2
    best_score, best = -1.0, None
    for item in sorted(cand):
        gain1 = wcaea.exp_true_gain(inst, state, item) / inst.items[item]['cost']
        # expected continuation: enumerate e's cluster outcomes cheaply via gain states
        new_pairs = [pair for pair in inst.items[item]['resolves'] if pair not in state]
        new_clusters = sorted({inst.pair_cluster[pair] for pair in new_pairs} - {inst.pair_cluster[pair] for pair in state})
        cont = 0.0
        for combo in itertools.product([0, 1], repeat=len(new_clusters)):
            prob, upd, theta = 1.0, dict(state), {}
            for cluster, fail in zip(new_clusters, combo):
                pfail = inst.cluster_pfail[cluster]
                prob *= pfail if fail else (1 - pfail); theta[cluster] = 'fail' if fail else 'pass'
            for pair in new_pairs:
                cluster_of_pair = inst.pair_cluster[pair]
                upd[pair] = theta[cluster_of_pair] if cluster_of_pair in theta else state[next(other for other in state if inst.pair_cluster[other] == cluster_of_pair)]
            cont += prob * gain_after(upd, rem - inst.items[item]['cost'], item)
        score = gain1 + 0.5 * cont
        if score > best_score + 1e-12: best_score, best = score, item
    return best

POLS = {'cadreF': CF.pol_cadre_cover, 'myopic': wcaea.pol_myopic, 'cheapest_first': pol_cheapest_first,
        'two_step': pol_two_step, 'cadreCPC': CO.pol_completion_opt, 'completion_greedy': wcaea.pol_completion}
raw = []
for nq in (25, 50):
    for seed in range(4000, 4012):
        inst = A_inst.F4_random(nq=nq, share=.3, maxobl=3, seed=seed)
        budget = float(round(.4 * sum(meta['cost'] for meta in inst.items.values())))
        worlds = [wcaea.draw_world(inst, random.Random(992000 + seed * 31 + trial * 7919)) for trial in range(40)]
        for pn, pol in POLS.items():
            decs, sps, tms = [], [], []
            for world in worlds:
                decided_count, spent, elapsed = run_policy(inst, pol, budget, world); decs.append(decided_count); sps.append(spent); tms.append(elapsed)
            raw.append(dict(nq=nq, seed=seed, policy=pn, decided_mean=round(statistics.mean(decs), 4),
                            spent_mean=round(statistics.mean(sps), 2), sec_mean=round(statistics.mean(tms), 4)))
        print(f'n={nq} seed={seed} done', flush=True)
with open(os.path.join(OUT, 'BASELINES_RAW.csv'), 'w', newline='') as fh:
    writer = csv.DictWriter(fh, fieldnames=list(raw[0].keys())); writer.writeheader(); writer.writerows(raw)
summ = []
for nq in (25, 50):
    base = {row['seed']: row['decided_mean'] for row in raw if row['nq'] == nq and row['policy'] == 'cadreF'}
    for pn in POLS:
        vals = [row['decided_mean'] for row in raw if row['nq'] == nq and row['policy'] == pn]
        tm = statistics.mean(row['sec_mean'] for row in raw if row['nq'] == nq and row['policy'] == pn)
        diffs = [row['decided_mean'] - base[row['seed']] for row in raw if row['nq'] == nq and row['policy'] == pn]
        mean_diff, ci = paired_ci(diffs)
        summ.append(dict(nq=nq, policy=pn, mean_decided=round(statistics.mean(vals), 3),
                         vs_cadreF=f'{mean_diff:+.3f}', ci_lo=f'{ci[0]:+.3f}', ci_hi=f'{ci[1]:+.3f}', mean_sec_per_run=round(tm, 4)))
with open(os.path.join(OUT, 'BASELINES_SUMMARY.csv'), 'w', newline='') as fh:
    writer = csv.DictWriter(fh, fieldnames=list(summ[0].keys())); writer.writeheader(); writer.writerows(summ)
for entry in summ: print(entry, flush=True)
print('DONE')
