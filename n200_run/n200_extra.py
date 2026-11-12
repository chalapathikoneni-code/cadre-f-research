import sys, os, csv, statistics, random, time, itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'code'))
from common import *
import cadre_feasible as CF
class Deadline(Exception): pass
def make_two_step(deadline_s):
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
        bs, best = -1.0, None
        try:
            for e in sorted(cand):
                if deadline_s is not None and time.perf_counter() - t_start > deadline_s: raise Deadline()
                g1 = W.exp_true_gain(inst, state, e) / inst.items[e]['cost']
                new_pairs = [pr for pr in inst.items[e]['resolves'] if pr not in state]
                new_clusters = sorted({inst.pair_cluster[pr] for pr in new_pairs} - {inst.pair_cluster[pr] for pr in state})
                cont = 0.0
                for combo in itertools.product([0, 1], repeat=len(new_clusters)):
                    prob, upd, theta = 1.0, dict(state), {}
                    for g, f in zip(new_clusters, combo):
                        pf = inst.cluster_pfail[g]; prob *= pf if f else (1 - pf); theta[g] = 'fail' if f else 'pass'
                    for pr in new_pairs:
                        gg = inst.pair_cluster[pr]
                        upd[pr] = theta[gg] if gg in theta else state[next(x for x in state if inst.pair_cluster[x] == gg)]
                    cont += prob * gain_after(upd, rem - inst.items[e]['cost'], e)
                sc = g1 + 0.5 * cont
                if sc > bs + 1e-12: bs, best = sc, e
        except Deadline:
            if best is None: return W.pol_myopic(inst, state, spent, B, rng)
            return best
        return best
    return pol
def pct(vals, q):
    s = sorted(vals); return s[min(len(s) - 1, int(q * len(s)))]
def run_timed(inst, pol, B, world):
    state, spent, ptime = {}, 0.0, 0.0
    rng = random.Random(0); guard = 0
    while spent < B and W.n_decided(inst, state) < len(inst.queries) and guard < 100000:
        guard += 1
        t0 = time.perf_counter(); e = pol(inst, state, spent, B, rng); ptime += time.perf_counter() - t0
        if e is None: break
        spent += inst.items[e]['cost']; state = W.apply_item(inst, state, e, world)
    return W.n_decided(inst, state), ptime
OUT = os.environ.get('CADRE_OUT', 'out/n200')
for seed in range(8100, 8106):
    inst = A_inst.F4_random(nq=200, share=.3, maxobl=3, seed=seed)
    B = float(round(.4 * sum(m['cost'] for m in inst.items.values())))
    worlds = [W.draw_world(inst, random.Random(555000 + (seed - 8100) * 977 + t * 131)) for t in range(10)]
    rows = []
    for vn, pol in (('cadreF', CF.pol_cadre_cover), ('myopic', W.pol_myopic),
                    ('two_step_100ms', make_two_step(0.1)), ('two_step_unrestricted', make_two_step(None))):
        decs, pts = [], []
        for w in worlds:
            d, pt = run_timed(inst, pol, B, w); decs.append(d); pts.append(pt)
        rows.append(dict(nq=200, seed=seed, variant=vn, decided_mean=round(statistics.mean(decs), 4),
                         plan_ms_mean=round(1000 * statistics.mean(pts), 2), plan_ms_median=round(1000 * statistics.median(pts), 2),
                         plan_ms_p95=round(1000 * pct(pts, 0.95), 2), plan_ms_total=round(1000 * sum(pts), 1), steps_mean=''))
    fn = os.path.join(OUT, f'TRADEOFF_EXT200_SEED{seed}.csv')
    with open(fn, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    print('ext200 seed', seed, 'written', flush=True)
print('EXT200 DONE')
