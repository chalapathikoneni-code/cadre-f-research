# Held-out real workload: EPA AirData ozone (parameter 44201)

Written 2026-11-11 08:06 PST, before the ozone files were downloaded or
inspected and before any policy was run on them. Purpose: an independent
real-data replication of the PM2.5 replay (PROTOCOL.md), with nothing
tuned on it.

## Data
EPA AirData pre-generated files, downloaded on the day of this protocol
from https://aqs.epa.gov/aqsweb/airdata/: `daily_44201_2024.csv` (train),
`daily_44201_2025.csv` (test), `aqs_monitors.csv` (registry). SHA-256
recorded in OZONE_DATA_HASHES.txt.

## Everything else is identical to PROTOCOL.md
Queries (monitor-day of a monitor with 44201 data in 2025), the four
obligations (`reg`, `method`, `complete`, `event`, same definitions with
parameter 44201 in the registry), evidence items REG/REC/FILE and their
byte-based page costs (P = 4096), planner model (one latent per monitor
and obligation, smoothed 2024 rates, Amendment 1 of PROTOCOL.md),
instance construction (one month, S = 6 / 12 sites, n = 25 / 50), budget
round(0.4 x total item cost), and policy code (unchanged).
Seeds: 9200-9259 (n = 25) and 9300-9359 (n = 50); 60 instances per size.
Preparation: `prep_epa.py` with the registry parameter code set to 44201
(the only change).

## Policies
CADRE-F, myopic, CPC, obligation density, cheapest certified completion
(CCF), two-step lookahead, CADRE-SEL with its three pre-declared
candidates (SEL3), and CADRE-SEL with CCF added (SEL4; see
selector/SELECTOR_PROTOCOL.md, Amendment 3).

## Analysis
Replication unit: instance (one real world each). Report every policy's
mean decided count, CADRE-F minus each policy and SEL minus the best
fixed cheap policy (chosen in hindsight), 95% paired t over the 60
instances. All results reported whatever they show. No design change
after seeing results.
