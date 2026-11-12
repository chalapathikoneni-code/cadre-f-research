# n=200 lookahead scaling summary

Instances found: [8100, 8101, 8102, 8103, 8104, 8105]

## Means per instance (decided, plan ms/run)

| seed | variant | decided | plan ms |
|---|---|---|---|
| 8100 | cadreF | 169.6 | 984.01 |
| 8100 | cadreF_timeref | 169.6 | 979.85 |
| 8100 | myopic | 167.6 | 1021.83 |
| 8100 | two_step_100ms | 104.8 | 17929.33 |
| 8100 | two_step_unrestricted | 172.3 | 466528.17 |
| 8101 | cadreF | 176.3 | 973.81 |
| 8101 | cadreF_timeref | 176.3 | 984.54 |
| 8101 | myopic | 172.3 | 983.59 |
| 8101 | two_step_100ms | 111 | 17773.5 |
| 8101 | two_step_unrestricted | 176.3 | 465552.62 |
| 8102 | cadreF | 167.4 | 775.18 |
| 8102 | cadreF_timeref | 167.4 | 790.42 |
| 8102 | myopic | 165.1 | 791.0 |
| 8102 | two_step_100ms | 115.5 | 15826.19 |
| 8102 | two_step_unrestricted | 171.8 | 343672.21 |
| 8103 | cadreF | 178.9 | 1250.46 |
| 8103 | cadreF_timeref | 178.9 | 1286.64 |
| 8103 | myopic | 176.8 | 1173.62 |
| 8103 | two_step_100ms | 112.5 | 19216.71 |
| 8103 | two_step_unrestricted | 180 | 582793.15 |
| 8104 | cadreF | 174.5 | 896.08 |
| 8104 | cadreF_timeref | 174.5 | 956.07 |
| 8104 | myopic | 172.4 | 903.63 |
| 8104 | two_step_100ms | 111.7 | 16546.87 |
| 8104 | two_step_unrestricted | 176.3 | 397305.28 |
| 8105 | cadreF | 168.1 | 715.41 |
| 8105 | cadreF_timeref | 168.1 | 732.97 |
| 8105 | myopic | 167.1 | 817.46 |
| 8105 | two_step_100ms | 113 | 16988.32 |
| 8105 | two_step_unrestricted | 172.9 | 391793.56 |

## Pre-declared contrasts (95% paired t, instance units)

- A cadreF - myopic: n=6: +2.250 [+1.229, +3.271]
- B cadreF - two_step_100ms: n=6: +61.050 [+54.701, +67.399]
- C two_step_unrestricted - cadreF: n=6: +2.467 [+0.496, +4.438]
- D1 time two_step_100ms / cadreF: n=6: geo-mean 18.9x (min 15.4x, max 23.7x)
- D2 time two_step_unrestricted / cadreF (same process): n=6: geo-mean 463.0x (min 415.6x, max 534.5x)
