# Model-based policy selector (CADRE-SEL): protocol (fixed before any run, 2026-11-10 ~21:37 PST)

## Policy
For an instance (items, costs, footprints, clusters, planner failure
probabilities p_g) and budget B, before any purchase:
1. Draw K = 20 worlds from the PLANNER's model (W.draw_world with
   random.Random(424242 + instance_index)); never the evaluation worlds,
   never the real outcomes.
2. Simulate CADRE-F, myopic and obligation density on these worlds.
3. Choose the policy with the highest simulated mean decided count;
   ties broken CADRE-F > myopic > obligation density.
4. Run the chosen policy on the evaluation world(s).
Selection cost is charged once per instance and reported with planning time.
No parameter is tuned; K = 20 and the candidate set are fixed here.

## Workloads (generators, seeds, budgets and evaluation worlds unchanged)
- EPA replay (PROTOCOL.md): 60 + 60 instances, real 2025 outcomes, planner
  p from 2024 (miscalibrated).
- Primary F4 holdout: n = 25, 50; seeds 4000-4011; 40 worlds/instance.
- Source-catalog families sparse/dense/hetero: 12 instances x 10 worlds.
- Source-file stress regimes R1-R4: 20 instances x 10 worlds.

## Analysis
Primary contrast: SEL minus best fixed simple policy per workload, chosen
from {CADRE-F, myopic, obligation density} by the evaluation means (an
oracle-best fixed baseline, a deliberately strict comparator), plus SEL
minus CADRE-F and SEL minus myopic. 95% paired t over instances.
Also reported: which policy SEL picked, and the obligation-density row for
Table I. All results reported whatever they show.

## Amendment 1 (before running it; after the four families above finished)
Add the six 200-query instances of the n200 lookahead study (seeds
8100-8105, same 10 worlds) to measure selector decisions and planning cost
at scale. Selector timing is per-instance selection plus one run.

## Amendment 2 (before running it)
Run the selector, unchanged, on the EPA tiered-storage variant with the
untiered budget (TIERED_PROTOCOL.md Amendment 1), M = 10 and M = 5.

Timestamp correction (2026-11-10 22:05 PST): the times in the headings above were
first written as estimates and some were wrong (e.g. "~23:05 PST" before 22:00 PST).
Corrected times are reconstructed from file timestamps; the ORDER (each protocol or
amendment written before the runs it governs) is unchanged and is shown by the result
file times: see the list below.
- holdout/catalog/stress/epa results finished 21:38-21:41 PST
- n200 results (Amendment 1) finished 21:43-21:44 PST
- tiered selector results (Amendment 2) finished 21:48 PST

## Amendment 3 (2026-11-11 08:08 PST, after all results above were seen)
Motivation is theoretical, not a result: without shared items, the
cheapest-certified-completion policy (CCF, `lookahead_baselines.pol_cheapest_first`)
decides at least the deterministic optimum in every world (paper,
Proposition on unshared evidence), and a selector inherits any
candidate's guarantee up to its sampling error. SEL4 adds CCF as a
fourth candidate (tie order CADRE-F > myopic > obligation density > CCF);
K = 20 and the selection seeds are unchanged. SEL3, the pre-declared
selector, stays the primary selector and is reported unchanged. SEL4 is
run on every workload above and on the held-out ozone replay
(epa_replay/OZONE_PROTOCOL.md). All SEL4 results are reported.

## Amendment 4 (2026-11-11, before running it; after CADRE-G3's results were seen)
SEL-G replaces CADRE-F by the frozen CADRE-G3 (group_ilp/CADRE_G_PROTOCOL.md) in
the candidate set: {CADRE-G3, myopic, obligation density}, tie order in that
order; K = 20 and the selection seeds are unchanged. Run on every workload.
Reported against the best of {CADRE-G3, CADRE-F, myopic, obligation density}
chosen in hindsight. SEL3 remains the pre-declared selector and is
reported unchanged. Chosen after seeing G3's results; disclosed as such.

## Amendment 5 (2026-11-11, before running it; after the ILP re-plan baseline's results were seen)
SEL-I: candidates {CADRE-G3, ILP re-plan (code/ilp_replan.py), myopic,
obligation density}, tie order in that order;
K = 20 and selection seeds unchanged. Run on every workload. Reported against
the best of all cheap policies (CADRE-F, CADRE-G3, ILP, myopic, density)
chosen in hindsight. Added after seeing results; disclosed as such.
