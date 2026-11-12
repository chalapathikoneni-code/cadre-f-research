"""Track B pilot: design data only (no reported workload, no 2025 outcomes).

Families: fresh seeds of F4 (n=25, 50), source-catalog (sparse/dense/hetero),
source-file regimes (R1-R4), and AirData PM2.5 2024 (in-sample, training year).
Usage: python group_ilp/run_pilot.py FAMILY OUT.csv   (PILOT_SET=2 for round 2)
"""
import csv
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ('code', 'freeze', 'transfer', 'epa_replay'):
    sys.path.insert(0, str(ROOT / sub))
import wcaea_fixed as W  # noqa: E402
sys.modules['wcaea'] = W
import cadre_opt as CO  # noqa: E402
CO.wcaea = W
CO.exp_true_gain = W.exp_true_gain
CO.decided = W.decided
import cadre_feasible as CF  # noqa: E402
CF.cadre_opt = CO
import cadre_group as CG  # noqa: E402

POLS = [('cadreF', CF.pol_cadre_cover), ('myopic', W.pol_myopic), ('obligation_density', W.pol_sssc),
        ('cadreG', CG.pol_cadre_group), ('cadreD', CG.pol_cadre_density_fallback)]
if os.environ.get('PILOT_SET') == '2':
    POLS = [('cadreF', CF.pol_cadre_cover), ('myopic', W.pol_myopic), ('obligation_density', W.pol_sssc),
            ('cadreG2', CG.pol_cadre_group_first), ('cadreG3', CG.pol_cadre_group_dense)]


def run(inst, pol, B, world):
    st, spent, guard = {}, 0.0, 0
    rng = random.Random(0)
    while spent < B and W.n_decided(inst, st) < len(inst.queries) and guard < 100000:
        guard += 1
        e = pol(inst, st, spent, B, rng)
        if e is None:
            break
        assert e in inst.items and W.item_useful(inst, st, e)
        assert inst.items[e]['cost'] <= B - spent + 1e-9
        spent += inst.items[e]['cost']
        st = W.apply_item(inst, st, e, world)
    return W.n_decided(inst, st)


def families(fam):
    if fam == 'f4':
        import instances as I
        for n, s0 in ((25, 7000), (50, 7100)):
            for seed in range(s0, s0 + 8):
                inst = I.F4_random(nq=n, share=.3, maxobl=3, seed=seed)
                B = float(round(.4 * sum(m['cost'] for m in inst.items.values())))
                yield f'f4_n{n}', seed, inst, B, [W.draw_world(inst, random.Random(seed * 13 + t)) for t in range(10)]
    elif fam == 'catalog':
        from gen2_independent import gen2
        for fi, f in enumerate(['sparse', 'dense', 'hetero']):
            for i in range(8):
                seed = 910001 + fi * 1000 + i
                inst, B = gen2(seed, f)
                yield f'cat_{f}', seed, inst, B, [W.draw_world(inst, random.Random(seed + t)) for t in range(10)]
    elif fam == 'files':
        from gen_transfer import gen
        for ri, r in enumerate(['R1_sparse', 'R2_complement', 'R3_hetero', 'R4_hub']):
            for i in range(8):
                seed = 5100001 + 10000 * ri + i
                inst, B = gen(seed, r)
                yield f'file_{r}', seed, inst, B, [W.draw_world(inst, random.Random(seed + t)) for t in range(10)]
    elif fam == 'air2024':
        sys.argv = ['run_epa.py', '--tables', str(Path(__file__).resolve().parent / 'pilot_tables_2024'), '--code', str(ROOT / 'code'),
                    '--out', '/dev/null', '--seed-starts', '9500,9600']
        import run_epa as R
        for n, (seeds, nsites) in sorted(R.SEEDS.items()):
            for seed in list(seeds)[:15]:
                inst, B, world, _ = R.build(seed, n, nsites)
                yield f'air2024_n{n}', seed, inst, B, [world]
    else:
        raise ValueError(fam)


def main():
    fam, out = sys.argv[1], sys.argv[2]
    with open(out, 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['group', 'seed', 'world', 'policy', 'decided'])
        for group, seed, inst, B, worlds in families(fam):
            for wi, w in enumerate(worlds):
                for name, pol in POLS:
                    wr.writerow([group, seed, wi, name, run(inst, pol, B, w)])
            fh.flush()
            print(group, seed, flush=True)
    print('PILOT_DONE', fam, flush=True)


if __name__ == '__main__':
    main()
