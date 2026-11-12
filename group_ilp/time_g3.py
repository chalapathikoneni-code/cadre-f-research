"""Sequential planning time of CADRE-G3 vs CADRE-F, measured in one process (first world).

Usage: python group_ilp/time_g3.py FAMILY GROUP_SUFFIX   e.g. epa n50 | holdout n50 | n200 n200
"""
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'selector'))
sys.path.insert(0, str(ROOT / 'code'))
import run_selector as S  # noqa: E402
import cadre_group as CG  # noqa: E402


def main():
    fam, suffix = sys.argv[1], sys.argv[2]
    f_t, g_t = [], []
    for idx, group, inst, B, worlds in S.instances(fam):
        if not group.endswith(suffix):
            continue
        w = worlds[0]
        t0 = time.perf_counter()
        S.run(inst, S.CF.pol_cadre_cover, B, w)
        f_t.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        S.run(inst, CG.pol_cadre_group_dense, B, w)
        g_t.append(time.perf_counter() - t0)
    print(f'{fam} {suffix}: CADRE-F {statistics.mean(f_t):.4f}s  CADRE-G {statistics.mean(g_t):.4f}s  '
          f'ratio {statistics.mean(g_t) / statistics.mean(f_t):.1f}x  ({len(f_t)} instances)')


if __name__ == '__main__':
    main()
