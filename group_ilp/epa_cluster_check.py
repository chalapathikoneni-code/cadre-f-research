"""How often do the replays' declared clusters (monitor, obligation) contain
contradictory real outcomes within an instance? Also counts multiple daily
rows and missing Observation Percent handling is in prep_epa.py.
Usage: python pilot/epa_cluster_check.py TABLES SEED25 SEED50
"""
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'code'))
tables, s25, s50 = sys.argv[1], sys.argv[2], sys.argv[3]
sys.argv = ['run_epa.py', '--tables', tables, '--code', str(ROOT / 'code'), '--out', '/dev/null',
            '--seed-starts', f'{s25},{s50}']
sys.path.insert(0, str(ROOT / 'epa_replay'))
import run_epa as R  # noqa: E402

tot = mixed = 0
inst_mixed = 0
pairs_in_mixed = pairs = 0
for n, (seeds, nsites) in sorted(R.SEEDS.items()):
    for seed in seeds:
        inst, B, world, _ = R.build(seed, n, nsites)
        cl = defaultdict(set)
        cnt = defaultdict(int)
        for pr, g in inst.pair_cluster.items():
            cl[g].add(world[pr])
            cnt[g] += 1
        m = [g for g, v in cl.items() if len(v) > 1]
        tot += len(cl)
        mixed += len(m)
        inst_mixed += bool(m)
        pairs += len(inst.pair_cluster)
        pairs_in_mixed += sum(cnt[g] for g in m)
print(f'{tables}: clusters {tot}, with contradictory outcomes {mixed} ({100 * mixed / tot:.2f}%); '
      f'pairs in such clusters {100 * pairs_in_mixed / pairs:.2f}%; instances affected {inst_mixed}/120')
