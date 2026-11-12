# CADRE-F reproducibility artifact

This is the reproducibility artifact for the ICDE 2027 submission *CADRE-F: Budgeted Evidence Acquisition for Query Validation over Shared, Correlated Data Sources*. It contains the code for every policy in the paper, the raw paired results behind every table, and the commands that regenerate them. The claims rest on paired comparisons, an exact oracle, and two replays of public EPA data, all checkable here. Start with the three checks under "Quick verification"; they take about two minutes.

## Contents

**Policies.** CADRE-F (pair-complete certificate policy) is in `code/cadre_feasible.py`. CADRE-G (group certificates) is in `code/cadre_group.py`. The ILP re-plan baseline (an all-pass integer program, re-solved after every purchase) is in `code/ilp_replan.py`. CADRE-SEL (model-based policy selection) is in `selector/run_selector.py`. Cluster-priced completion (CPC) is in `code/cadre_opt.py`. Myopic and obligation density are in `code/wcaea_fixed.py`, and PAOTR-style sequencing is in `code/paotr.py`. Two-step lookahead and cheapest certified completion (CCF) are in `code/lookahead_baselines.py`.

**Exact references.** The exact adaptive dynamic program and the per-world enumeration are in `code/exact_policy_enumeration.py`. The certificate tests are `code/test_feasible.py` and `code/test_partial_states.py`. The exact check of Proposition 1 is `code/test_unshared.py`.

**Real data.** `epa_replay/` replays EPA AirData PM2.5 (parameter 88101) and ozone (parameter 44201) records. It ships the prepared tables, the SHA-256 hashes of the public source files, and the protocols. Each protocol was written before the first policy run on its data.

**Results.** Every folder keeps its raw paired observations (one row per policy, instance and world) next to the script that summarizes them.

## Where each result lives

| Paper result | Folder or script |
|---|---|
| Table I, primary F4 holdout | `data/HOLDOUT_FINAL.csv`, `code/run_holdout.py` |
| Table II, EPA PM2.5 and ozone replays | `epa_replay/` |
| Table III, source-catalog workloads | `freeze/` |
| Table IV, source-file stress tests | `transfer/` |
| Table V, every policy on every workload | `group_ilp/make_table5.py` (uses `selector/`, `group_ilp/`) |
| Table VI, component variants | `ablation/` |
| Table VII, constructed exact cases | `data/exact_policy_results.csv` |
| Table IX and Sec. VI-K, 200-query study | `n200_run/` |
| Sec. VI-B, tiered-storage variant | `epa_replay/tiered_variant/` |
| Sec. VI-B, cluster misspecification rates | `group_ilp/epa_cluster_check.py` |
| Sec. VI-C, 13-configuration F4 study | `data/F4_CONFIGURATION_SUMMARY.csv` |
| Sec. VI-E, selection and regret study | `selector/` |
| Sec. VI-F, CADRE-G and ILP re-plan | `group_ilp/`, `group_ilp/ilp/` |

## Running the artifact

**Requirements.** Python 3.10 or later, with no third-party packages. SciPy 1.14.1 is needed only for the ILP baseline, SEL-I and `ablation/run_ablation_portable.py` (`pip install scipy==1.14.1`). Run every command from this folder with `PYTHONHASHSEED=0`, so set iteration order matches the shipped results.

**Quick verification.** These checks confirm the certificate, the partial-state semantics and the synthetic table numbers.

```
PYTHONHASHSEED=0 python code/test_feasible.py
PYTHONHASHSEED=0 python code/test_partial_states.py
python verify_results.py
python group_ilp/make_table5.py
```

**EPA replays.** The prepared tables are included. To rebuild them, download the public AirData files listed in `epa_replay/PROTOCOL.md` and `epa_replay/OZONE_PROTOCOL.md`, then check them against `DATA_HASHES.txt` and `OZONE_DATA_HASHES.txt`.

```
mkdir -p out
gunzip -c epa_replay/tables/monitor_days_2025.csv.gz > epa_replay/tables/monitor_days_2025.csv
gunzip -c epa_replay/oz_tables/monitor_days_2025.csv.gz > epa_replay/oz_tables/monitor_days_2025.csv
PYTHONHASHSEED=0 python epa_replay/run_epa.py --tables epa_replay/tables --code code --out out/epa
PYTHONHASHSEED=0 python epa_replay/run_epa.py --tables epa_replay/oz_tables --code code --out out/oz --seed-starts 9200,9300
python epa_replay/analyze_epa.py out/epa epa_replay/tables
python epa_replay/analyze_epa.py out/oz epa_replay/oz_tables
# optional rebuild from raw files: python epa_replay/prep_epa.py RAW_DIR epa_replay/oz_tables 44201
PYTHONHASHSEED=0 python group_ilp/epa_cluster_check.py epa_replay/tables 9000 9100
PYTHONHASHSEED=0 python group_ilp/epa_cluster_check.py epa_replay/oz_tables 9200 9300
```

**CADRE-SEL.** Each family takes about five minutes on one core. Prefix any selector command with `SEL_SET=4`, `SEL_SET=G` or `SEL_SET=I` to run SEL4, SEL-G or SEL-I.

```
for f in holdout catalog stress; do PYTHONHASHSEED=0 python selector/run_selector.py $f out/SEL_$f.csv; done
EPA_DIR=epa_replay EPA_TABLES=epa_replay/tables PYTHONHASHSEED=0 python selector/run_selector.py epa out/SEL_epa.csv
SEL_SET=3 EPA_DIR=epa_replay EPA_TABLES=epa_replay/oz_tables EPA_EXTRA_ARGS="--seed-starts 9200,9300" PYTHONHASHSEED=0 python selector/run_selector.py epa out/SEL3_ozone.csv
for s in 8100 8101 8102 8103 8104 8105; do SEL_SEED=$s PYTHONHASHSEED=0 python selector/run_selector.py n200 out/SEL_n200_$s.csv; done
python selector/analyze_selector.py out/SEL_*.csv
python selector/run_selector_regret.py holdout out/REGRET_holdout.csv   # FAMILY OUT.csv
```

**CADRE-G and ILP re-plan.** CADRE-G was designed on pilot data only (fresh seeds and the 2024 training year in `group_ilp/pilot_tables_2024/`). It was then frozen with the acceptance test in `group_ilp/CADRE_G_PROTOCOL.md` before any reported run.

```
gunzip -c group_ilp/pilot_tables_2024/monitor_days_2025.csv.gz > group_ilp/pilot_tables_2024/monitor_days_2025.csv
for f in f4 catalog files air2024; do PILOT_SET=2 PYTHONHASHSEED=0 python group_ilp/run_pilot.py $f out/PILOT2_$f.csv; done
EPA_DIR=epa_replay EPA_TABLES=epa_replay/tables PYTHONHASHSEED=0 python group_ilp/run_g3.py epa out/G3_pm25.csv
EPA_DIR=epa_replay EPA_TABLES=epa_replay/tables PYTHONHASHSEED=0 python group_ilp/run_ilp.py epa out/ILP_pm25.csv
python group_ilp/cadre_g_numbers.py
```

**Exact checks and the 200-query study.** The Proposition 1 check takes about 30 seconds. The uncapped two-step group at 200 queries takes about 8 minutes per instance.

```
PYTHONHASHSEED=0 python code/test_unshared.py
python n200_run/run_n200.py --seed 8100 --group fast    # also --group slow, seeds 8100-8105
```

## Notes for reviewers

**Planning times depend on the host.** All times are local Python policy computation, not acquisition latency. Ratios between policies measured in one process are more stable than absolute milliseconds.

**Protocols.** The protocol files (`PROTOCOL.md`, `OZONE_PROTOCOL.md`, `TIERED_PROTOCOL.md`, `SELECTOR_PROTOCOL.md`, `CADRE_G_PROTOCOL.md`, `N200_RUN_SPEC.md`) record what was fixed before each run; their decisions and timestamps are unchanged, with only internal codenames and renamed-file references normalized to the shipped names. One amendment, the tiered-storage budget, is recorded in its protocol and stated in Sec. VI-B of the paper.

**Name correspondence.** CSV labels differ from paper names in a few places. CADRE-F is `cadreF` or `cadre-cover`. CPC is `cadre`, `cadre-audited` or `cadreCPC`. Obligation density is `sssc` or `obligation_density`. CADRE-SEL is `selector`.
