"""Summarize selector runs: per group means, paired contrasts, choice counts.

Usage: python selector/analyze_selector.py SEL_*.csv
"""
import csv
import math
import statistics
import sys
from collections import Counter, defaultdict

# two-sided 95% t critical values by df
TCRIT = {5: 2.571, 11: 2.201, 19: 2.093, 59: 2.001}
CANDS = ['cadreF', 'cadreG3', 'myopic', 'obligation_density', 'cheapest_first']  # canonical order


def ci(diffs):
    n = len(diffs)
    m = statistics.mean(diffs)
    h = TCRIT.get(n - 1, 2.0) * statistics.stdev(diffs) / math.sqrt(n) if n > 1 else 0.0
    return f'{m:+.3f} [{m - h:+.3f},{m + h:+.3f}]'


def main():
    per = defaultdict(lambda: defaultdict(list))  # group -> (inst,pol) -> decided list
    choice, selsec = {}, defaultdict(list)
    for fn in sys.argv[1:]:
        for r in csv.DictReader(open(fn)):
            per[r['group']][(int(r['instance']), r['policy'])].append(float(r['decided']))
            choice[(r['group'], int(r['instance']))] = r['sel_choice']
            selsec[r['group']].append(float(r['sel_sec']))
    for g in sorted(per):
        insts = sorted({i for i, _ in per[g]})
        present = {p for _, p in per[g]}
        cands = [p for p in CANDS if p in present]
        pols = cands + ['selector']
        mean = {p: [statistics.mean(per[g][(i, p)]) for i in insts] for p in pols}
        # selector must reproduce its chosen policy exactly (sanity check)
        for i, s in zip(insts, mean['selector']):
            assert abs(s - statistics.mean(per[g][(i, choice[(g, i)])])) < 1e-9
        best = max(cands, key=lambda p: statistics.mean(mean[p]))
        picks = Counter(choice[(g, i)] for i in insts)
        print(f'== {g} ({len(insts)} instances; selection {statistics.mean(selsec[g]):.2f}s/instance)')
        print('   means: ' + '  '.join(f'{p}={statistics.mean(mean[p]):.3f}' for p in pols))
        print('   picks: ' + ', '.join(f'{k}:{v}' for k, v in picks.most_common()))
        for base in cands:
            d = [a - b for a, b in zip(mean['selector'], mean[base])]
            tag = ' (best fixed)' if base == best else ''
            print(f'   SEL-{base}{tag}: {ci(d)}')


if __name__ == '__main__':
    main()
