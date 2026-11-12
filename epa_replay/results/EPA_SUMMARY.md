# EPA AirData replay results

## Calibration (global failure rate)

| obligation | 2024 (planner) | 2025 (truth) |
|---|---|---|
| reg | 0.00451 | 0.00105 |
| method | 0.02556 | 0.01185 |
| complete | 0.01145 | 0.01057 |
| event | 0.05603 | 0.04371 |

## n = 25 (60 instances, page 4096; mean items 36.5, mean truly refutable queries 1.62)

| policy | mean decided | mean sec/run | CADRE-F minus policy [95% CI] | F wins/losses |
|---|---|---|---|---|
| cadreF | 17.283 | 0.0081 | reference | |
| myopic | 15.617 | 0.0048 | +1.667 [+0.596, +2.737] | 19/13 |
| cadreCPC | 17.200 | 0.0143 | +0.083 [-0.090, +0.257] | 4/1 |
| two_step | 18.683 | 0.4901 | -1.400 [-2.026, -0.774] | 7/31 |
| cheapest_first | 16.667 | 0.0040 | +0.617 [+0.021, +1.213] | 24/10 |
| obligation_density | 17.567 | 0.0015 | -0.283 [-0.905, +0.339] | 13/17 |

## n = 50 (60 instances, page 4096; mean items 73.1, mean truly refutable queries 3.40)

| policy | mean decided | mean sec/run | CADRE-F minus policy [95% CI] | F wins/losses |
|---|---|---|---|---|
| cadreF | 38.633 | 0.0370 | reference | |
| myopic | 33.850 | 0.0242 | +4.783 [+3.022, +6.545] | 43/13 |
| cadreCPC | 38.467 | 0.0780 | +0.167 [-0.012, +0.346] | 4/0 |
| two_step | 40.583 | 5.3880 | -1.950 [-2.726, -1.174] | 5/41 |
| cheapest_first | 37.050 | 0.0155 | +1.583 [+0.974, +2.193] | 36/7 |
| obligation_density | 38.983 | 0.0062 | -0.350 [-1.026, +0.326] | 14/20 |

## Page-size sensitivity (primary contrast CADRE-F minus myopic)

| page | n | diff [95% CI] | wins/losses |
|---|---|---|---|
| 1024 | 25 | +1.400 [+0.221, +2.579] | 13/7 |
| 1024 | 50 | +3.600 [+2.151, +5.049] | 32/6 |
| 4096 | 25 | +1.667 [+0.596, +2.737] | 19/13 |
| 4096 | 50 | +4.783 [+3.022, +6.545] | 43/13 |
| 16384 | 25 | +0.500 [-0.097, +1.097] | 11/7 |
| 16384 | 50 | +1.233 [+0.250, +2.217] | 20/13 |
