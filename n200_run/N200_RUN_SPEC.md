# n=200 lookahead scaling run: spec

Goal: replace the single-instance n=200 lookahead comparison in Sec. VI-I
with 6 independent instances, so the claim "at 200 queries a practical
time cap leaves two-step far behind CADRE-F" is an instance-level paired
estimate, not one instance.

## What already exists

Seed 8100 (`n200_extra.py`, 10 worlds) was run first:

| variant | decided | plan s/run |
|---|---|---|
| cadreF | 169.6 | 1.10 |
| myopic | 167.6 | 1.25 |
| two_step_100ms | 103.0 | 18.4 |
| two_step_unrestricted | 172.3 | 448.8 |

## Design (fixed before running)

- Generator: `F4_random(nq=200, share=0.3, maxobl=3, seed=s)`, budget
  `round(0.4 * total item cost)`. Same as seed 8100.
- Seeds: 8101-8105 (8100 already done; keep it). 6 instances total.
- Worlds: 10 per instance, seeds `555000 + (s-8100)*977 + t*131`, t=0..9.
  All policies see the same 10 worlds.
- Policies:
  - Group FAST: `cadreF`, `myopic`, `two_step_100ms`
  - Group SLOW: `two_step_unrestricted`
- Do not change any policy code, cap, tie order or fallback.

## Run rules (these matter for validity)

1. **Never run anything else on the machine while a capped (100 ms) variant
   runs.** The cap is wall-clock. CPU contention changes which candidates are
   evaluated before the deadline and therefore changes the decided counts,
   not just the timing.
2. Run FAST seeds **serially**, one process.
3. SLOW can run on a different machine, or after FAST finishes. Uncapped
   decided counts do not depend on CPU contention (no deadline), but its
   timings do. If SLOW runs in parallel or elsewhere, report its time as a
   ratio to cadreF measured **in the same process/machine** (the runner
   times cadreF alongside it for that reason).
4. Set `PYTHONHASHSEED=0`.
5. Record `python --version`, `nproc`, and `lscpu | head -20` into
   `results/N200_ENV.txt`.

## Commands

From the artifact root:

```bash
export PYTHONHASHSEED=0

# FAST group, serial, nothing else running
for s in 8101 8102 8103 8104 8105; do python n200_run/run_n200.py --seed $s --group fast; done

# SLOW group (long; includes a cadreF timing reference)
for s in 8101 8102 8103 8104 8105; do python n200_run/run_n200.py --seed $s --group slow; done

# Aggregate (works with whatever has finished)
python n200_run/aggregate_n200.py
```

Outputs: `results/N200_SEED<s>_<group>.csv` per run and `results/N200_SUMMARY.md`
from the aggregator. Seed 8100's existing results are reused.

## Analysis (fixed before running)

Unit of replication: instance. For each instance, average the 10 worlds.
Report, over the 6 instances, mean and two-sided 95% paired t interval
(5 d.f.) for:

- A. cadreF minus myopic (decided)
- B. cadreF minus two_step_100ms (decided)
- C. two_step_unrestricted minus cadreF (decided), if SLOW has at least 3 instances
- D. planning-time ratios two_step_100ms / cadreF and
  two_step_unrestricted / cadreF (geometric mean over instances, plus min and max)

No other contrasts. No re-tuning of the cap after seeing results.

## Reporting (fixed before running)

Report A and B with their intervals and the capped time ratio. If SLOW
completes, also report C and both time ratios over all six instances;
otherwise keep the uncapped single-instance figure labelled "on one
instance". If B is not clearly positive (interval crosses zero or reverses),
report it as measured and lead the trade-off with the uncapped time ratio;
do not pick a different cap after the fact.
