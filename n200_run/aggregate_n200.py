"""Aggregate n=200 runs into N200_SUMMARY.md (see N200_RUN_SPEC.md).

Instance = replication unit. Paired two-sided 95% t intervals over
instance means. Works with partial results.
"""
import csv
import glob
import math
import os
import statistics

OUT = os.environ.get('CADRE_OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results'))

# T quantiles t_{0.975, df}
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
        7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def load():
    """Return {seed: {variant: row}}."""
    data = {}
    files = glob.glob(os.path.join(OUT, 'N200_SEED*_*.csv'))
    seed8100 = os.path.join(OUT, 'TRADEOFF_EXT200_SEED8100.csv')
    if os.path.exists(seed8100):
        files.append(seed8100)
    for fn in files:
        with open(fn) as fh:
            for r in csv.DictReader(fh):
                data.setdefault(int(r['seed']), {})[r['variant']] = r
    # Seed 8100 was one process: its cadreF also serves as the time reference.
    if 8100 in data and 'cadreF' in data[8100]:
        data[8100].setdefault('cadreF_timeref', data[8100]['cadreF'])
    return data


def paired(data, a, b, field='decided_mean'):
    diffs = [float(v[a][field]) - float(v[b][field])
             for v in data.values() if a in v and b in v]
    n = len(diffs)
    if n < 2:
        return n, None
    m = statistics.mean(diffs)
    h = T975[n - 1] * statistics.stdev(diffs) / math.sqrt(n)
    return n, (m, m - h, m + h)


def ratio(data, num, den):
    rs = [float(v[num]['plan_ms_mean']) / float(v[den]['plan_ms_mean'])
          for v in data.values() if num in v and den in v]
    if not rs:
        return 0, None
    g = math.exp(statistics.mean(math.log(x) for x in rs))
    return len(rs), (g, min(rs), max(rs))


def fmt(res):
    n, v = res
    if v is None:
        return f'n={n}: not enough instances'
    return f'n={n}: {v[0]:+.3f} [{v[1]:+.3f}, {v[2]:+.3f}]'


def fmt_ratio(res):
    n, v = res
    if v is None:
        return f'n={n}: none'
    return f'n={n}: geo-mean {v[0]:.1f}x (min {v[1]:.1f}x, max {v[2]:.1f}x)'


def main():
    data = load()
    lines = ['# n=200 lookahead scaling summary', '',
             f'Instances found: {sorted(data)}', '',
             '## Means per instance (decided, plan ms/run)', '',
             '| seed | variant | decided | plan ms |', '|---|---|---|---|']
    for s in sorted(data):
        for v in sorted(data[s]):
            r = data[s][v]
            lines.append(f"| {s} | {v} | {r['decided_mean']} | {r['plan_ms_mean']} |")
    lines += ['', '## Pre-declared contrasts (95% paired t, instance units)', '',
              f'- A cadreF - myopic: {fmt(paired(data, "cadreF", "myopic"))}',
              f'- B cadreF - two_step_100ms: {fmt(paired(data, "cadreF", "two_step_100ms"))}',
              f'- C two_step_unrestricted - cadreF: {fmt(paired(data, "two_step_unrestricted", "cadreF"))}',
              f'- D1 time two_step_100ms / cadreF: {fmt_ratio(ratio(data, "two_step_100ms", "cadreF"))}',
              f'- D2 time two_step_unrestricted / cadreF (same process): '
              f'{fmt_ratio(ratio(data, "two_step_unrestricted", "cadreF_timeref"))}']
    fn = os.path.join(OUT, 'N200_SUMMARY.md')
    with open(fn, 'w') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
