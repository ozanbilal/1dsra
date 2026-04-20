# StrataWave DEEPSOIL Example Parity Report

- Generated UTC: `2026-03-23T13:33:39.036565+00:00`
- Best current case: `nonlinear_5a_rigid_dt0025_tuned`

## Executive verdict

- StrataWave ana analiz yollari calisiyor.
- OpenSees destekli effective-stress adapter calisiyor.
- DEEPSOIL parity araci mevcut, ancak tam esdegerlik kapanmadi.
- En iyi mevcut vaka `nonlinear_5a_rigid_dt0025_tuned` ve bu vaka icin `PSA NRMSE=0.1939`.

## Case matrix

| Case | Boundary | dt_sw (s) | Surface NRMSE | Surface Corr | PGA diff (%) | PSA NRMSE | Verdict |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| linear_1b | rigid | 0.0200 | 0.4572 | -0.0120 | -23.14 | 0.2346 | partial |
| linear_1b_mkz0 | rigid | 0.0200 | 0.5858 | 0.0004 | -12.25 | 0.3216 | partial |
| nonlinear_5a | elastic_halfspace | 0.0200 | 5.0995 | 0.0131 | 523.98 | 3.7486 | poor |
| nonlinear_5a_rigid | rigid | 0.0200 | 5.0937 | 0.0131 | 523.25 | 3.7470 | poor |
| nonlinear_5a_rigid_dt005 | rigid | 0.0050 | 0.4426 | 0.0018 | -57.40 | 0.2026 | partial |
| nonlinear_5a_rigid_dt0025 | rigid | 0.0025 | 0.4389 | -0.0032 | -57.15 | 0.2007 | partial |
| nonlinear_5a_rigid_dt0025_tuned | rigid | 0.0025 | 0.4364 | -0.0015 | -68.40 | 0.1939 | partial |
| nonlinear_5a_elastic_dt005 | elastic_halfspace | 0.0050 | 0.4425 | -0.0005 | -63.87 | 0.2092 | partial |
| nonlinear_5a_elastic_dt0025 | elastic_halfspace | 0.0025 | 0.4384 | 0.0004 | -64.03 | 0.2074 | partial |

## Key findings

- Best case: `nonlinear_5a_rigid_dt0025_tuned` (Example 5A nonlinear rigid-base dt=0.0025 tuned)
- Best-case PSA NRMSE: `0.1939`
- Best-case PGA diff: `-68.40%`
- Best-case surface correlation: `-0.0015`

## Technical caveats

- Native linear/nonlinear solvers are currently fixed-base oriented, while some DEEPSOIL examples use elastic halfspace.
- Small-strain damping treatment is not yet closed to DEEPSOIL formulations.
- Current nonlinear MKZ/GQH path is operational, but not yet published-reference calibrated for full parity.

## Best-case warnings

- Time-step mismatch detected (StrataWave=0.0025s, DEEPSOIL=0.02s).
