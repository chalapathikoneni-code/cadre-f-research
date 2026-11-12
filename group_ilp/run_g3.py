"""Run frozen CADRE-G3 on the reported workloads (see CADRE_G_PROTOCOL.md).

Usage: python group_ilp/run_g3.py FAMILY OUT.csv   (FAMILY as in selector/run_selector.py;
EPA_* and SEL_SEED environment variables as there). Instances, budgets and
evaluation worlds come from selector/run_selector.instances, i.e. the same
ones as the reported comparators.
"""
import csv
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'selector'))
sys.path.insert(0, str(ROOT / 'code'))
import run_selector as S  # noqa: E402
import cadre_group as CG  # noqa: E402


def main():
    fam, out = sys.argv[1], sys.argv[2]
    with open(out, 'w', newline='') as fh:
        wr = csv.writer(fh)
        wr.writerow(['group', 'instance', 'world', 'policy', 'decided', 'sec'])
        for idx, group, inst, B, worlds in S.instances(fam):
            for wi, w in enumerate(worlds):
                t0 = time.perf_counter()
                d = S.run(inst, CG.pol_cadre_group_dense, B, w)
                wr.writerow([group, idx, wi, 'cadreG3', d, round(time.perf_counter() - t0, 4)])
            fh.flush()
            print(group, idx, flush=True)
    print('G3_DONE', fam, flush=True)


if __name__ == '__main__':
    main()
