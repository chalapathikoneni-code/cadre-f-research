"""Run one n=200 instance for one policy group (see N200_RUN_SPEC.md).

Reuses make_two_step / run_timed from n200_extra.py unchanged by
importing the helpers defined there. The module-level loop in that file is
skipped by exec-ing only the definitions.

Usage: python run_n200.py --seed 8101 --group fast|slow
"""
import argparse
import csv
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'code')
OUT = os.environ.get('CADRE_OUT', os.path.join(HERE, 'results'))
sys.path.insert(0, WORK)
sys.path.insert(0, HERE)

# Load function definitions from n200_extra.py without running its loop.
src_path = os.path.join(HERE, 'n200_extra.py')
src = open(src_path).read()
defs_only = src.split('OUT = os.environ.get')[0]
ns = {'__file__': src_path, '__name__': 'ext200b_defs'}
exec(compile(defs_only, src_path, 'exec'), ns)
A_inst, W, CF = ns['A_inst'], ns['W'], ns['CF']
make_two_step, run_timed, pct = ns['make_two_step'], ns['run_timed'], ns['pct']

GROUPS = {
    'fast': [('cadreF', CF.pol_cadre_cover), ('myopic', W.pol_myopic),
             ('two_step_100ms', make_two_step(0.1))],
    # cadreF is re-timed here so the slow ratio uses one machine/process.
    'slow': [('cadreF_timeref', CF.pol_cadre_cover),
             ('two_step_unrestricted', make_two_step(None))],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seed', type=int, required=True)
    ap.add_argument('--group', choices=sorted(GROUPS), required=True)
    a = ap.parse_args()
    seed = a.seed
    inst = A_inst.F4_random(nq=200, share=.3, maxobl=3, seed=seed)
    B = float(round(.4 * sum(m['cost'] for m in inst.items.values())))
    worlds = [W.draw_world(inst, random.Random(555000 + (seed - 8100) * 977 + t * 131))
              for t in range(10)]
    rows = []
    for name, pol in GROUPS[a.group]:
        decs, pts = [], []
        for w in worlds:
            d, pt = run_timed(inst, pol, B, w)
            decs.append(d)
            pts.append(pt)
        rows.append(dict(nq=200, seed=seed, variant=name,
                         decided_mean=round(statistics.mean(decs), 4),
                         decided_per_world=' '.join(str(x) for x in decs),
                         plan_ms_mean=round(1000 * statistics.mean(pts), 2),
                         plan_ms_median=round(1000 * statistics.median(pts), 2),
                         plan_ms_p95=round(1000 * pct(pts, 0.95), 2),
                         plan_ms_total=round(1000 * sum(pts), 1)))
        print(seed, a.group, name, rows[-1]['decided_mean'], rows[-1]['plan_ms_mean'], flush=True)
    fn = os.path.join(OUT, f'N200_SEED{seed}_{a.group}.csv')
    with open(fn, 'w', newline='') as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print('wrote', fn)


if __name__ == '__main__':
    main()
