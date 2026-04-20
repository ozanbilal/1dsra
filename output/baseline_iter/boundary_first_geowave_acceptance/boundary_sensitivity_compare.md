# Boundary Sensitivity Verification

- Case A: `rigid_within` (`run-24be21e0eccb`)
- Case B: `elastic_halfspace_outcrop` (`run-e9a80a760dc2`)

## Config
- Boundary: `rigid` -> `elastic_halfspace`
- Motion input type: `within` -> `outcrop`
- Same upper layers: `True`
- Only last layer or boundary changed: `True`

## Input
- Raw input history NRMSE: `0.0`
- Raw input PSA NRMSE: `0.0`
- Applied input history NRMSE: `0.11426298819670662`
- Applied input PSA NRMSE: `0.3412264864583427`
- Raw input PGA (g): `0.21876097017380222` -> `0.21876097017380222`
- Raw input PSA peak (g): `0.7727544284663005` -> `0.7727544284663005`

## Surface Response
- Surface history NRMSE: `0.16534373913285869`
- Surface history corrcoef: `0.77097676510334`
- Surface PGA (g): `0.3800703517796116` -> `0.28851399423114676`
- Surface PGA ratio B/A: `0.7591068150415613`
- Surface PGD (m): `0.006919118912983445` -> `0.004177708738337171`
- Surface PGD ratio B/A: `0.6037920132428813`
- Surface PSA peak (g): `1.7913724001216424` -> `1.0603243782235594`
- Surface PSA peak ratio B/A: `0.5919061710181303`
- Surface peak period (s): `0.18983052393992603` -> `0.16931815540668732`
- Surface peak period shift B vs A (%): `-10.80562182914802`
- Surface PSA NRMSE: `0.19811903757952032`

## Case-Local Amplification
- Surface/Input PGA amplification: `1.7373773369063576` -> `1.3188549767443747`
- Surface/Input peak PSA amplification: `2.318165168819558` -> `1.372136268863582`

## Profile
- Depth points: `5`
- gamma_max NRMSE: `0.46489725975189666`
- PGA profile NRMSE: `0.4055667215439911`
- max displacement NRMSE: `0.48667603610302634`
- max strain NRMSE: `0.4648972597518967`
- max stress ratio NRMSE: `0.28679936564801795`
- effective stress NRMSE: `0.0`
- tau_peak NRMSE: `0.22047763436957601`
- secant G/Gmax NRMSE: `0.13083859946932738`

## Warnings
- none
