# EPA AirData replay results

## Calibration (global failure rate)

| obligation | 2024 (planner) | 2025 (truth) |
|---|---|---|
| reg | 0.0 | 0.0 |
| method | 0.04953 | 0.02422 |
| complete | 0.02118 | 0.02293 |
| event | 0.02929 | 0.02025 |

## n = 25 (60 instances, page 4096; mean items 36.8, mean truly refutable queries 1.58)

| policy | mean decided | mean sec/run | CADRE-F minus policy [95% CI] | F wins/losses |
|---|---|---|---|---|
| cadreF | 19.450 | 0.0110 | reference | |
| myopic | 18.033 | 0.0069 | +1.417 [+0.460, +2.373] | 18/9 |
| cadreCPC | 19.450 | 0.0161 | +0.000 [+0.000, +0.000] | 0/0 |
| two_step | 20.067 | 0.5858 | -0.617 [-1.281, +0.048] | 4/19 |
| cheapest_first | 16.533 | 0.0069 | +2.917 [+2.239, +3.595] | 40/0 |
| obligation_density | 19.400 | 0.0024 | +0.050 [-0.190, +0.290] | 3/4 |

## n = 50 (60 instances, page 4096; mean items 72.7, mean truly refutable queries 3.17)

| policy | mean decided | mean sec/run | CADRE-F minus policy [95% CI] | F wins/losses |
|---|---|---|---|---|
| cadreF | 42.400 | 0.0328 | reference | |
| myopic | 38.667 | 0.0248 | +3.733 [+2.315, +5.152] | 35/6 |
| cadreCPC | 42.400 | 0.0597 | +0.000 [+0.000, +0.000] | 0/0 |
| two_step | 43.133 | 4.3341 | -0.733 [-1.357, -0.110] | 9/24 |
| cheapest_first | 34.950 | 0.0189 | +7.450 [+6.200, +8.700] | 57/0 |
| obligation_density | 42.433 | 0.0062 | -0.033 [-0.370, +0.303] | 7/8 |

## Page-size sensitivity (primary contrast CADRE-F minus myopic)

| page | n | diff [95% CI] | wins/losses |
|---|---|---|---|
| 4096 | 25 | +1.417 [+0.460, +2.373] | 18/9 |
| 4096 | 50 | +3.733 [+2.315, +5.152] | 35/6 |
