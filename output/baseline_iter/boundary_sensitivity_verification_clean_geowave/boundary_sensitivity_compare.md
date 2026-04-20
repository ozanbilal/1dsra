# Boundary Sensitivity Verification

- Case A: `geowave_rigid` (`run-6d2dceb6114f`)
- Case B: `geowave_elastic` (`run-c98e4ddd1066`)

## Config
- Boundary: `rigid` -> `elastic_halfspace`
- Motion input type: `outcrop` -> `outcrop`
- Same upper layers: `True`
- Only last layer or boundary changed: `True`

## Input
- Raw input history NRMSE: `0.0`
- Raw input PSA NRMSE: `0.0`
- Applied input history NRMSE: `0.05713149409835331`
- Applied input PSA NRMSE: `0.17061324322917135`

## Surface Response
- Surface history NRMSE: `0.09621421585254757`
- Surface history corrcoef: `0.6843379557027798`
- Surface PGA (g): `0.26652731545622477` -> `0.39539179131854923`
- Surface PGA ratio B/A: `1.48349444274311`
- Surface PSA peak (g): `1.3465771310768437` -> `1.371852308917403`
- Surface PSA peak ratio B/A: `1.0187699443702471`
- Surface peak period (s): `0.18983052393992603` -> `0.19720604305082343`
- Surface peak period shift B vs A (%): `3.8853177865280846`
- Surface PSA NRMSE: `0.12178390238325766`

## Profile
- Depth points: `5`
- gamma_max NRMSE: `0.33639785603701144`
- PGA profile NRMSE: `0.2613599977114288`
- max displacement NRMSE: `0.989371335411385`
- max strain NRMSE: `0.3363978560370114`
- max stress ratio NRMSE: `0.2758017267312882`
- effective stress NRMSE: `0.0`
- tau_peak NRMSE: `0.21177679157778775`
- secant G/Gmax NRMSE: `0.17676124657892964`

## Warnings
- none
