#!/bin/sh
# Planning-time ratios CADRE-SEL / CADRE-F (paper Sec. VI-D), measured
# sequentially, one process per family, with nothing else running.
# Run from the artifact root after preparing epa_replay/tables (see README).
# Output used in the paper: selector/results/TIMING.txt
export PYTHONHASHSEED=0 PYTHONPATH=selector EPA_DIR=epa_replay EPA_TABLES=epa_replay/tables
{
  python selector/time_selector.py holdout
  python selector/time_selector.py epa
  for s in 8100 8101 8102 8103 8104 8105; do SEL_SEED=$s python selector/time_selector.py n200; done
} > out/TIMING.txt 2>&1
