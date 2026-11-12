"""Planning-time ratio of CADRE-SEL to CADRE-F, measured in one process.

Usage: python selector/time_selector.py FAMILY   (holdout or epa: n = 50 instances; n200: set SEL_SEED)
Prints mean seconds per run for CADRE-F and for CADRE-SEL (selection + chosen run).
"""
import statistics
import sys
import time

import run_selector as S


def main():
    fam = sys.argv[1]
    f_t, s_t = [], []
    for idx, group, inst, B, worlds in S.instances(fam):
        if not (group.endswith('n50') or group == 'n200'):
            continue
        w = worlds[0]
        t0 = time.perf_counter()
        S.run(inst, S.CF.pol_cadre_cover, B, w)
        f_t.append(time.perf_counter() - t0)
        t0 = time.perf_counter()
        choice, _ = S.select(inst, B, idx)
        S.run(inst, dict(S.CANDIDATES)[choice], B, w)
        s_t.append(time.perf_counter() - t0)
    ratio = statistics.mean(s_t) / statistics.mean(f_t)
    print(f'{fam}{"" if fam == "n200" else " n50"}: CADRE-F {statistics.mean(f_t):.4f}s  SEL {statistics.mean(s_t):.4f}s  ratio {ratio:.1f}x  ({len(f_t)} instances)')


if __name__ == '__main__':
    main()
