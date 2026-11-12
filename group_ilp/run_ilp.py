"""Run the ILP re-plan baseline on the reported workloads (same instances/worlds).

Usage: python group_ilp/run_ilp.py FAMILY OUT.csv   (EPA_* / SEL_SEED env as in run_selector.py)
"""
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'selector'))
sys.path.insert(0, str(ROOT / 'code'))
import run_selector as S  # noqa: E402
import ilp_replan as IL  # noqa: E402


def main():
    fam, out = sys.argv[1], sys.argv[2]
    with open(out, 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['group', 'instance', 'world', 'policy', 'decided', 'sec', 'solves', 'nonoptimal'])
        for idx, group, inst, B, worlds in S.instances(fam):
            for wi, w in enumerate(worlds):
                s0, n0 = IL.STATS['solves'], IL.STATS['nonoptimal']
                t0 = time.perf_counter()
                d = S.run(inst, IL.pol_ilp_replan, B, w)
                wr.writerow([group, idx, wi, 'ilp', d, round(time.perf_counter() - t0, 4),
                             IL.STATS['solves'] - s0, IL.STATS['nonoptimal'] - n0])
            fh.flush()
            print(group, idx, flush=True)
    print('ILP_DONE', fam, flush=True)


if __name__ == '__main__':
    main()
