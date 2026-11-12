import sys, os, csv, math, random, statistics, itertools, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'code'))
from common import *
import cadre_feasible as CF

OUT = os.environ.get('CADRE_OUT', 'out/n200')
os.makedirs(OUT, exist_ok=True)
# ---- two-step lookahead, deadline-aware (identical scoring to Phase D) ----
class Deadline(Exception): pass

def make_two_step(deadline_s, counter):
    """deadline_s=None -> unrestricted (must reproduce Phase D exactly).
    Otherwise: per-decision deadline; on expiry, the decision is made by the
    best FULLY evaluated candidate so far this step, or plain myopic if none.
    An unfinished evaluation is never used."""
    def pol(inst, state, spent, B, rng):
        rem = B - spent
        cand = [e for e in inst.items if inst.items[e]['cost'] <= rem + 1e-9 and W.item_useful(inst, state, e)]
        if not cand: return None
        t_start = time.perf_counter()
        def gain_after(state2, rem2, e1):
            best2 = 0.0
            for e2 in inst.items:
                if e2 == e1: continue
                if inst.items[e2]['cost'] <= rem2 + 1e-9 and W.item_useful(inst, state2, e2):
                    best2 = max(best2, W.exp_true_gain(inst, state2, e2) / inst.items[e2]['cost'])
            return best2
        bs, best, n_eval = -1.0, None, 0
        try:
            for e in sorted(cand):
                if deadline_s is not None and time.perf_counter() - t_start > deadline_s:
                    raise Deadline()
                g1 = W.exp_true_gain(inst, state, e) / inst.items[e]['cost']
                new_pairs = [pr for pr in inst.items[e]['resolves'] if pr not in state]
                new_clusters = sorted({inst.pair_cluster[pr] for pr in new_pairs} - {inst.pair_cluster[pr] for pr in state})
                cont = 0.0
                for combo in itertools.product([0, 1], repeat=len(new_clusters)):
                    prob, upd, theta = 1.0, dict(state), {}
                    for g, f in zip(new_clusters, combo):
                        pf = inst.cluster_pfail[g]
                        prob *= pf if f else (1 - pf); theta[g] = 'fail' if f else 'pass'
                    for pr in new_pairs:
                        gg = inst.pair_cluster[pr]
                        upd[pr] = theta[gg] if gg in theta else state[next(x for x in state if inst.pair_cluster[x] == gg)]
                    cont += prob * gain_after(upd, rem - inst.items[e]['cost'], e)
                n_eval += 1
                sc = g1 + 0.5 * cont
                if sc > bs + 1e-12: bs, best = sc, e
        except Deadline:
            counter['fallbacks'] += 1
            if best is None:
                counter['myopic_fallbacks'] += 1
                return W.pol_myopic(inst, state, spent, B, rng)
            return best
        counter['evals'] += n_eval
        return best
    return pol

def run_timed(inst, pol, B, world):
    """Run one world; planning time = sum of policy-call durations only."""
    state, spent, ptime, steps = {}, 0.0, 0.0, 0
    rng = random.Random(0); guard = 0
    while spent < B and W.n_decided(inst, state) < len(inst.queries) and guard < 100000:
        guard += 1
        t0 = time.perf_counter()
        e = pol(inst, state, spent, B, rng)
        ptime += time.perf_counter() - t0
        if e is None: break
        assert inst.items[e]['cost'] <= B - spent + 1e-9, 'BUDGET VIOLATION'
        spent += inst.items[e]['cost']; state = W.apply_item(inst, state, e, world); steps += 1
    assert spent <= B + 1e-9
    return W.n_decided(inst, state), spent, ptime, steps

def pct(vals, q):
    s = sorted(vals); return s[min(len(s) - 1, int(q * len(s)))]

raw = []
def campaign(nq, seeds, nworlds, allowances_ms):
    for seed in seeds:
        inst = A_inst.F4_random(nq=nq, share=.3, maxobl=3, seed=seed)
        B = float(round(.4 * sum(m['cost'] for m in inst.items.values())))
        worlds = [W.draw_world(inst, random.Random(992000 + seed * 31 + t * 7919)) for t in range(nworlds)]
        variants = [('cadreF', CF.pol_cadre_cover), ('myopic', W.pol_myopic)]
        for ams in allowances_ms:
            variants.append((f'two_step_{ams}ms' if ams else 'two_step_unrestricted',
                             make_two_step(None if ams is None else ams / 1000.0, {'evals': 0, 'fallbacks': 0, 'myopic_fallbacks': 0})))
        for vn, pol in variants:
            decs, pts, stps = [], [], []
            for w in worlds:
                d, s, pt, st = run_timed(inst, pol, B, w); decs.append(d); pts.append(pt); stps.append(st)
            raw.append(dict(nq=nq, seed=seed, variant=vn, decided_mean=round(statistics.mean(decs), 4),
                            plan_ms_mean=round(1000 * statistics.mean(pts), 2), plan_ms_median=round(1000 * statistics.median(pts), 2),
                            plan_ms_p95=round(1000 * pct(pts, 0.95), 2), plan_ms_total=round(1000 * sum(pts), 1),
                            steps_mean=round(statistics.mean(stps), 1)))
        print(f'n={nq} seed={seed} done', flush=True)

campaign(25, range(4000, 4012), 40, [5, 10, 20, 50, 100, None])
campaign(50, range(4000, 4012), 40, [5, 10, 20, 50, 100, None])
with open(os.path.join(OUT, 'TRADEOFF_RAW.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(raw[0].keys())); w.writeheader(); w.writerows(raw)
print('MAIN DONE', flush=True)
# extension: n=100/200, fewer allowances, 6 instances x 10 worlds (author scaling seeds)
raw2 = []
for nq in (100, 200):
    for seed in range(8100, 8106):
        inst = A_inst.F4_random(nq=nq, share=.3, maxobl=3, seed=seed)
        B = float(round(.4 * sum(m['cost'] for m in inst.items.values())))
        worlds = [W.draw_world(inst, random.Random(555000 + (seed - 8100) * 977 + t * 131)) for t in range(10)]
        variants = [('cadreF', CF.pol_cadre_cover), ('myopic', W.pol_myopic),
                    ('two_step_100ms', make_two_step(0.1, {'evals': 0, 'fallbacks': 0, 'myopic_fallbacks': 0})),
                    ('two_step_unrestricted', make_two_step(None, {'evals': 0, 'fallbacks': 0, 'myopic_fallbacks': 0}))]
        for vn, pol in variants:
            decs, pts = [], []
            for w in worlds:
                d, s, pt, st = run_timed(inst, pol, B, w); decs.append(d); pts.append(pt)
            raw2.append(dict(nq=nq, seed=seed, variant=vn, decided_mean=round(statistics.mean(decs), 4),
                             plan_ms_mean=round(1000 * statistics.mean(pts), 2), plan_ms_median=round(1000 * statistics.median(pts), 2),
                             plan_ms_p95=round(1000 * pct(pts, 0.95), 2), plan_ms_total=round(1000 * sum(pts), 1), steps_mean=''))
        print(f'ext n={nq} seed={seed} done', flush=True)
with open(os.path.join(OUT, 'TRADEOFF_EXTENSION_RAW.csv'), 'w', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(raw2[0].keys())); w.writeheader(); w.writerows(raw2)
print('PHASE H DONE')
