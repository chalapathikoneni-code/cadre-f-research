# Source-file stress workloads

Four synthetic 25-query regimes test sparse, complementary, heterogeneous,
and hub-correlated source-file coverage. Each regime uses 20 independently
generated instances, 10 common latent worlds per instance, and a budget of
40% of the aggregate item price. The evaluation compares the same fixed
CADRE-F, myopic, CPC, and cluster-coverage policies.

`TRANSFER_FROZEN_HOLDOUT.csv` stores the four policies' mean decisions,
spending, and computation time for each generated instance. The paper's
95% intervals are computed from instance-level paired differences.

From the artifact root:

```
PYTHONHASHSEED=0 python transfer/run_transfer.py --smoke
PYTHONHASHSEED=0 python transfer/run_transfer.py --instances 2 --worlds 10 --output transfer/REPLAY_SAMPLE.csv
PYTHONHASHSEED=0 python transfer/run_transfer.py --instances 20 --worlds 10 --output transfer/REPLAY_ALL.csv
```

The full replay checks decided counts and spending against the supplied
frozen CSV. Timing results vary by execution environment. All source
outcome probabilities, evidence costs, and query obligations are synthetic.
