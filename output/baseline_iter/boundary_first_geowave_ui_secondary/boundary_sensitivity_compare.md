# Boundary Sensitivity Verification

- Case A: `rigid_outcrop` (`run-6d2dceb6114f`)
- Case B: `elastic_halfspace_outcrop` (`run-e9a80a760dc2`)

## Config
- Boundary: `rigid` -> `elastic_halfspace`
- Motion input type: `outcrop` -> `outcrop`
- Same upper layers: `True`
- Only last layer or boundary changed: `True`

## Input
- Raw input history NRMSE: `0.0`
- Raw input PSA NRMSE: `0.0`
- Applied input history NRMSE: `0.0`
- Applied input PSA NRMSE: `0.0`

## Surface Response
- Surface history NRMSE: `0.10272313023342522`
- Surface history corrcoef: `0.7775843350268719`
- Surface PGA (g): `0.26652731545622477` -> `0.28851399423114676`
- Surface PGA ratio B/A: `1.0824931536089897`
- Surface PGD (m): `0.0038825004027630214` -> `0.004177708738337171`
- Surface PGD ratio B/A: `1.0760356226528816`
- Surface PSA peak (g): `1.3465771310768437` -> `1.0603243782235594`
- Surface PSA peak ratio B/A: `0.7874219409738743`
- Surface peak period (s): `0.18983052393992603` -> `0.16931815540668732`
- Surface peak period shift B vs A (%): `-10.80562182914802`
- Surface PSA NRMSE: `0.06771381222203522`

## Profile
- Depth points: `5`
- gamma_max NRMSE: `0.05038689779677079`
- PGA profile NRMSE: `0.09296379355230544`
- max displacement NRMSE: `0.05052771868837317`
- max strain NRMSE: `0.050386897796770726`
- max stress ratio NRMSE: `0.05731068431009257`
- effective stress NRMSE: `0.0`
- tau_peak NRMSE: `0.038312690495438374`
- secant G/Gmax NRMSE: `0.012983548096156289`

## Warnings
- none
