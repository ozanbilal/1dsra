# Boundary Sensitivity Verification

- Case A: `rigid_bedrock` (`run-e5b1767d8efd`)
- Case B: `elastic_halfspace` (`run-c98e4ddd1066`)

## Config
- Boundary: `rigid` -> `elastic_halfspace`
- Motion input type: `outcrop` -> `outcrop`
- Same upper layers: `False`
- Only last layer or boundary changed: `False`

## Input
- Raw input history NRMSE: `0.021917128628244898`
- Raw input PSA NRMSE: `3.6056491298434086e-05`
- Applied input history NRMSE: `0.05920083966270444`
- Applied input PSA NRMSE: `0.17061007678357085`

## Surface Response
- Surface history NRMSE: `0.18484026468444617`
- Surface history corrcoef: `0.46493985910450464`
- Surface PGA (g): `0.34719282910217164` -> `0.39539179131854923`
- Surface PGA ratio B/A: `1.1388247630027912`
- Surface PSA peak (g): `2.25233457471054` -> `1.371852308917403`
- Surface PSA peak ratio B/A: `0.6090801625658602`
- Surface peak period (s): `0.18983052393992603` -> `0.19720604305082343`
- Surface peak period shift B vs A (%): `3.8853177865280846`
- Surface PSA NRMSE: `0.16538680486714627`

## Profile
- Depth points: `5`
- gamma_max NRMSE: `None`
- PGA profile NRMSE: `0.14479419658849405`
- max displacement NRMSE: `0.9897700054465939`
- max strain NRMSE: `None`
- max stress ratio NRMSE: `None`
- effective stress NRMSE: `3.4648824731834145e-17`
- tau_peak NRMSE: `None`
- secant G/Gmax NRMSE: `None`

## Warnings
- none
