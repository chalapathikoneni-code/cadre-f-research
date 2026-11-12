# EPA tiered-storage variant: protocol (fixed before any run, 2026-11-10 ~21:23 PST)

Purpose: test the one condition the EPA replay lacks -- items that touch the
same latent cluster but witness different queries at very different prices.
In the base replay every REC(m,d) costs exactly 2 pages, so CPC's
cheapest-item-per-cluster price equals the query's own cover price.

Change vs. PROTOCOL.md (everything else identical: instances, seeds 9000-9059 /
9100-9159, real 2025 outcomes, 2024-estimated probabilities, page 4096,
budget = round(0.4 x total item cost), policy code unchanged):

- Each daily record REC(m,d) is in cold storage independently with
  probability 0.5, decided by SHA-256 of "tier|<monitor>|<date>" (first byte < 128).
- Cold REC cost = M x its page cost. Primary M = 10; sensitivity M = 5.
- REG(site) and FILE(site,month) costs unchanged.

Semi-synthetic: outcomes, footprints and hot costs are real; the tier
assignment and multiplier are synthetic.

Primary contrast: CADRE-F minus CPC, n = 25 and n = 50, M = 10, 95% paired t
over 60 instances. Secondary: CADRE-F minus myopic, obligation density,
cheapest-certified-completion, two-step. All results reported.

## Amendment 1 (2026-11-10 ~21:41 PST, after the M=10 and M=5 results were seen)
The M=10 run was uninformative because the budget, 0.4 x total item cost,
grows with the cold multiplier and lets every policy decide nearly every
query. Rerun M=10 and M=5 with the budget computed from the UNTIERED costs
(same B as the base replay). This change was made after seeing results and
is reported as such; the original runs are kept.

Timestamp correction (2026-11-10 22:05 PST): the times in the headings above were
first written as estimates and some were wrong (e.g. "~23:05 PST" before 22:00 PST).
Corrected times are reconstructed from file timestamps; the ORDER (each protocol or
amendment written before the runs it governs) is unchanged and is shown by the result
file times: see the list below.
- first runs EPA_TIERED_M10.csv / M5.csv finished 21:27 PST
- amended runs *_baseB.csv finished 21:46 PST
