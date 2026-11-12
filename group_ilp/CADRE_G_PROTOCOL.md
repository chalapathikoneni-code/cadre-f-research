# Share-aware policy CADRE-G (protocol, 2026-11-11 09:46 PST)

Written after the pilot and before CADRE-G was run on any reported
workload or on any 2025 outcome.

## Design data (pilot only)
Fresh seeds never used in reported results: F4 (7000-7007, 7100-7107),
source-catalog (910001-912008), source-file regimes (5100001-5130008), and
AirData PM2.5 **2024** monitor-days (seeds 9500-9514 / 9600-9614, in-sample
2024 rates; no 2025 data). Results: `out/PILOT_*.csv`, `out/PILOT2_*.csv`.

Variants tried, in order: CADRE-G (group step after the gate), CADRE-D
(density fallback), CADRE-G2 (group step before the gate), CADRE-G3 (G2 with
the densest group-cover item). Selection rule, chosen when picking between
G2 and G3 (G and D were dominated): the smallest worst-case pilot loss
against the best fixed cheap policy. G3: -3.03 (G2: -3.11). Frozen: **CADRE-G3**,
`pol_cadre_group_dense` in `code/cadre_group.py`,
SHA-256 81ca1e88927766adedd5ca63381a8ac15cd64ba5abf4c0770a1cc8b2e984d490
(cadre_feasible.py 2d300b87..., wcaea_fixed.py 0c333804...).

## Evaluation (reported workloads, unchanged instances, budgets and worlds)
Primary holdout n=25/50, source-catalog x3, source-file R1-R4, 200-query
instances, PM2.5 2025 replay n=25/50, held-out ozone 2025 replay n=25/50,
tiered variant (amended budget, M=10 and M=5). Comparators: CADRE-F,
myopic, obligation density (same worlds; existing runs).

## Acceptance test (fixed now)
Primary (real data): on PM2.5 and ozone 2025, at both sizes, CADRE-G3's
mean >= the best of {CADRE-F, myopic, obligation density}, with the paired
95% CI of (G3 - best fixed) not entirely below zero. Reported per group.
Secondary: not significantly below the best fixed policy on the primary
holdout and source-catalog groups. Expected from the pilot and reported
either way: below obligation density on the complementary and hub regimes.
All results reported whatever they show.
