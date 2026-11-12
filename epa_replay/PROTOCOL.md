# EPA AirData replay workload: protocol (fixed before any policy run)

Written 2026-11-10, before any policy was executed on this workload.
Only data inspection (failure-rate probe on 2024) was done beforehand.

## Data

EPA AirData pre-generated files, PM2.5 FRM/FEM (parameter 88101),
downloaded 2026-11-10 from https://aqs.epa.gov/aqsweb/airdata/:
`daily_88101_2024.csv` (train), `daily_88101_2025.csv` (test),
`aqs_monitors.csv` (registry). SHA-256 of each file recorded in
`DATA_HASHES.txt`.

## Queries

A query is "report the daily PM2.5 value for monitor m on day d"
(monitor = state-county-site-POC). Only monitor-days present in the
2025 daily file are queryable.

## Obligations (outcome taken from the real 2025 records)

| id | passes when | resolved by |
|---|---|---|
| `reg` | monitor is in the 88101 registry and d is within [First Year of Data, Last Sample Date] | REG(site) |
| `method` | the day's method code equals the registry's Last Method Code | REG(site) |
| `complete` | max Observation Percent over the monitor-day's rows >= 75 | REC(m,d) or FILE(site,month) |
| `event` | no row for the monitor-day carries an exceptional-event flag (Event Type != None) | REC(m,d) or FILE(site,month) |

The canonical row for `method` is the row with the highest
Observation Percent.

## Evidence items and costs

Cost = 1 + ceil(bytes / P) I/O pages, P = 4096 (primary). Bytes are the
UTF-8 length of the CSV lines a request returns:

- REG(site): all `aqs_monitors.csv` rows for the site (all parameters).
- REC(m,d): all 2025 daily rows for that monitor-day.
- FILE(site,month): all 2025 daily rows for that site and month.

Sensitivity: P = 1024 and P = 16384.

## Planner model (estimated on 2024 only)

- Clusters: one latent per (monitor, obligation), shared across days.
  This is the paper's perfect within-cluster correlation assumption; the
  real 2025 outcomes do not satisfy it exactly.
- Failure probability: smoothed 2024 rate (k + 10 g) / (n + 10), where g
  is the global 2024 rate of that obligation. `reg`, `method`,
  `complete` use per-monitor counts; `event` uses per-site site-day
  counts. Units without 2024 data get g.

Amendment 1 (2026-11-10, before any policy result was produced): the
first version used one latent per pair for `complete` and per (site,
day) for `event`. A site-month FILE item then touches up to about 30
new clusters, and the policies' exact outcome enumeration (2^k) did not
finish a single instance in 15 minutes. Clusters were changed to one
per (monitor, obligation). No policy output from the first version
exists.
- The world is the real 2025 outcome of every pair. No sampling.

## Instances

For seed s: draw a month uniformly from 2025, draw S sites uniformly
among sites with data that month (S = 6 for n = 25, S = 12 for n = 50),
and draw n monitor-days uniformly from those sites' monitor-days in that
month. Seeds 9000-9059 (n = 25) and 9100-9159 (n = 50): 60 instances per
size. Budget = round(0.4 x total item cost).

## Policies (code unchanged)

CADRE-F, myopic, CPC, two-step lookahead, cheapest-certified-completion,
obligation density.

## Analysis

- Replication unit: instance (one real world each).
- Primary contrast: CADRE-F minus myopic at n = 25 and n = 50,
  two-sided 95% paired t interval over the 60 instances.
- Secondary: CADRE-F minus each other policy; mean planning time.
- Calibration: 2024 estimated vs 2025 realized failure rate per
  obligation.
- Sensitivity: page size, primary contrast only.
- All results are reported, including unfavourable ones. No design
  change after seeing results.
