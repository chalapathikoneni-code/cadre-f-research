"""Model-based policy selector (CADRE-SEL); see SELECTOR_PROTOCOL.md.

Usage: python selector/run_selector.py FAMILY OUT.csv
FAMILY in {holdout, catalog, stress, epa}. Run from the artifact root with
PYTHONHASHSEED=0. Generators, seeds, budgets and evaluation worlds are the
ones used for the paper's tables; the policy code is unchanged.
"""
import csv
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ('code', 'freeze', 'transfer'):
    sys.path.insert(0, str(ROOT / sub))
import wcaea_fixed as W  # noqa: E402
sys.modules['wcaea'] = W
import cadre_opt as CO  # noqa: E402
CO.wcaea = W
CO.exp_true_gain = W.exp_true_gain
CO.decided = W.decided
import cadre_feasible as CF  # noqa: E402
CF.cadre_opt = CO

CANDIDATES = [('cadreF', CF.pol_cadre_cover), ('myopic', W.pol_myopic),
              ('obligation_density', W.pol_sssc)]  # order = tie-break order
if os.environ.get('SEL_SET', '3') == '4':
    # Amendment 3: add cheapest certified completion (CCF) from lookahead_baselines.py, definitions only.
    _pd = ROOT / 'code' / 'lookahead_baselines.py'
    _ns = {'__file__': str(_pd), '__name__': 'lookahead_baselines_defs'}
    exec(compile(open(_pd).read().split('POLS = {')[0], str(_pd), 'exec'), _ns)
    CANDIDATES.append(('cheapest_first', _ns['pol_cheapest_first']))
if os.environ.get('SEL_SET', '3') == 'G':
    # Amendment 4: CADRE-G3 replaces CADRE-F.
    import cadre_group as CG  # noqa: E402
    CANDIDATES = [('cadreG3', CG.pol_cadre_group_dense), ('myopic', W.pol_myopic),
                  ('obligation_density', W.pol_sssc)]
if os.environ.get('SEL_SET', '3') == 'I':
    # Amendment 5: CADRE-G3, ILP re-plan, myopic, density (needs SciPy).
    import cadre_group as CG  # noqa: E402
    import ilp_replan as IL  # noqa: E402
    CANDIDATES = [('cadreG3', CG.pol_cadre_group_dense), ('ilp', IL.pol_ilp_replan),
                  ('myopic', W.pol_myopic), ('obligation_density', W.pol_sssc)]
K_SEL = 20


def run(inst, pol, B, world):
    state, spent, guard = {}, 0.0, 0
    rng = random.Random(0)
    while spent < B and W.n_decided(inst, state) < len(inst.queries) and guard < 100000:
        guard += 1
        e = pol(inst, state, spent, B, rng)
        if e is None:
            break
        assert e in inst.items and W.item_useful(inst, state, e)
        assert inst.items[e]['cost'] <= B - spent + 1e-9, 'budget violation'
        spent += inst.items[e]['cost']
        state = W.apply_item(inst, state, e, world)
    return W.n_decided(inst, state)


def select(inst, B, idx):
    """Pick a candidate by simulating on worlds drawn from the planner's own model."""
    t0 = time.perf_counter()
    rng = random.Random(424242 + idx)
    worlds = [W.draw_world(inst, rng) for _ in range(K_SEL)]
    best, best_v = None, -1.0
    for name, pol in CANDIDATES:
        v = sum(run(inst, pol, B, w) for w in worlds) / K_SEL
        if v > best_v + 1e-12:  # strict: earlier candidate wins ties
            best, best_v = name, v
    return best, time.perf_counter() - t0


def instances(family):
    """Yield (idx, group, inst, B, eval_worlds) exactly as in the paper's runners."""
    idx = 0
    if family == 'holdout':
        import instances as I
        for n in (25, 50):
            for seed in range(4000, 4012):
                inst = I.F4_random(nq=n, share=.3, maxobl=3, seed=seed)
                B = float(round(.4 * sum(m['cost'] for m in inst.items.values())))
                ws = [W.draw_world(inst, random.Random(992000 + seed * 31 + t * 7919)) for t in range(40)]
                yield idx, f'holdout_n{n}', inst, B, ws
                idx += 1
    elif family == 'catalog':
        from gen2_independent import gen2
        seed0 = 700001
        for fi, fam in enumerate(['sparse', 'dense', 'hetero']):
            for ii in range(12):
                inst, B = gen2(seed0 + fi * 1000 + ii, fam)
                wrng = random.Random(seed0 + 555000 + fi * 1000 + ii)
                yield idx, f'catalog_{fam}', inst, B, [W.draw_world(inst, wrng) for _ in range(10)]
                idx += 1
    elif family == 'stress':
        from gen_transfer import gen
        for ri, regime in enumerate(['R1_sparse', 'R2_complement', 'R3_hetero', 'R4_hub']):
            for ii in range(20):
                seed = 3100001 + 10000 * ri + ii
                inst, B = gen(seed, regime)
                wrng = random.Random(seed + 555000)
                yield idx, f'stress_{regime}', inst, B, [W.draw_world(inst, wrng) for _ in range(10)]
                idx += 1
    elif family == 'n200':
        import instances as I
        seed = int(os.environ['SEL_SEED'])  # one 200-query instance per process
        inst = I.F4_random(nq=200, share=.3, maxobl=3, seed=seed)
        B = float(round(.4 * sum(m['cost'] for m in inst.items.values())))
        ws = [W.draw_world(inst, random.Random(555000 + (seed - 8100) * 977 + t * 131)) for t in range(10)]
        yield seed - 8100, 'n200', inst, B, ws
    elif family == 'epa':
        epa_dir = os.environ['EPA_DIR']  # folder holding run_epa.py (or run_epa_tiered.py)
        tables = os.environ['EPA_TABLES']
        sys.argv = ['run_epa.py', '--tables', tables, '--code', str(ROOT / 'code'), '--out', '/dev/null']
        sys.argv += os.environ.get('EPA_EXTRA_ARGS', '').split()
        sys.path.insert(0, epa_dir)
        R = __import__(os.environ.get('EPA_MODULE', 'run_epa'))
        for n, (seeds, nsites) in sorted(R.SEEDS.items()):
            for seed in seeds:
                inst, B, world, _ = R.build(seed, n, nsites)
                yield idx, f'epa_n{n}', inst, B, [world]
                idx += 1
    else:
        raise ValueError(family)


def main():
    family, out = sys.argv[1], sys.argv[2]
    with open(out, 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['group', 'instance', 'world', 'policy', 'decided', 'sel_choice', 'sel_sec'])
        for idx, group, inst, B, worlds in instances(family):
            choice, sel_sec = select(inst, B, idx)
            pols = dict(CANDIDATES)
            for wi, w in enumerate(worlds):
                for name, pol in CANDIDATES:
                    wr.writerow([group, idx, wi, name, run(inst, pol, B, w), choice, round(sel_sec, 4)])
                wr.writerow([group, idx, wi, 'selector', run(inst, pols[choice], B, w), choice, round(sel_sec, 4)])
            fh.flush()
            print(group, idx, choice, round(sel_sec, 2), flush=True)
    print('SELECTOR_DONE', family, flush=True)


if __name__ == '__main__':
    main()
