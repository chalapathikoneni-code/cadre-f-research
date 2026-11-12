"""Track D: measured selection regret of CADRE-SEL vs K, and under a misspecified model.

For each instance: draw POOL worlds from the planner's model, run every
candidate on each, estimate V_a on the first VAL worlds, and draw selection
sets of size K from the remaining worlds (REPS resamples without
replacement). Regret = max_a V_a - V_chosen, in decisions, under the model.

Misspecification (holdout only, MISSPEC=f): the planner's failure
probabilities are scaled by f (clipped to [0, 0.95]) for selection, while
values are measured on worlds drawn from the true probabilities.

Usage: python selector/run_selector_regret.py FAMILY OUT.csv
"""
import copy
import csv
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_selector as S  # noqa: E402

POOL, VAL, REPS = 100, 60, 200
KS = (5, 10, 20, 40)


def main():
    fam, out = sys.argv[1], sys.argv[2]
    f = float(os.environ.get('MISSPEC', '1'))
    with open(out, 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['group', 'instance', 'misspec', 'K', 'mean_regret', 'p_wrong', 'gap_best_second'])
        for idx, group, inst, B, _ in S.instances(fam):
            model = inst
            if f != 1.0:
                model = copy.copy(inst)
                model.cluster_pfail = {g: min(0.95, p * f) for g, p in inst.cluster_pfail.items()}
            rng_true = random.Random(777000 + idx)
            rng_model = random.Random(888000 + idx)
            val_worlds = [S.W.draw_world(inst, rng_true) for _ in range(VAL)]
            sel_worlds = [S.W.draw_world(model, rng_model) for _ in range(POOL - VAL)]
            names = [n for n, _ in S.CANDIDATES]
            # policies plan with the (possibly wrong) model in both pools
            V = {n: sum(S.run(model, p, B, w) for w in val_worlds) / VAL for n, p in S.CANDIDATES}
            U = {n: [S.run(model, p, B, w) for w in sel_worlds] for n, p in S.CANDIDATES}
            best_v = max(V.values())
            ranked = sorted(V.values(), reverse=True)
            rs = random.Random(999000 + idx)
            for K in KS:
                reg = wrong = 0.0
                for _ in range(REPS):
                    ix = rs.sample(range(len(sel_worlds)), K)
                    sim = {n: sum(U[n][i] for i in ix) / K for n in names}
                    choice = None
                    for n in names:  # tie order as in CADRE-SEL
                        if choice is None or sim[n] > sim[choice] + 1e-12:
                            choice = n
                    reg += best_v - V[choice]
                    wrong += V[choice] < best_v - 1e-12
                wr.writerow([group, idx, f, K, round(reg / REPS, 4), round(wrong / REPS, 4),
                             round(ranked[0] - ranked[1], 4)])
            fh.flush()
            print(group, idx, flush=True)
    print('REGRET_DONE', fam, flush=True)


if __name__ == '__main__':
    main()
