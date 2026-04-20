# Boundary Sensitivity Verification

- Case A: `rigid_within` (`Motion_Kocaeli`)
- Case B: `elastic_halfspace_outcrop` (`Motion_Kocaeli`)

## Config
- Boundary: `rigid` -> `elastic_halfspace`
- Motion input type: `within` -> `outcrop`

## Input
- Raw input history NRMSE: `0.0`
- Raw input PSA NRMSE: `0.0`
- Applied input history NRMSE: `0.0`
- Applied input PSA NRMSE: `0.0`
- Raw input PGA (g): `0.2188357` -> `0.2188357`
- Raw input PSA peak (g): `0.7730184051898091` -> `0.7730184051898091`

## Surface Response
- Surface history NRMSE: `0.2289931475884608`
- Surface history corrcoef: `0.6376635202772304`
- Surface PGA (g): `0.5069620690623701` -> `0.3074536789233513`
- Surface PGA ratio B/A: `0.606462884870241`
- Surface PGD (m): `0.007664623427635184` -> `0.004715434738700916`
- Surface PGD ratio B/A: `0.615220667162744`
- Surface PSA peak (g): `2.6318912431648163` -> `1.2011026859219496`
- Surface PSA peak ratio B/A: `0.456364862735604`
- Surface peak period (s): `0.18983052393992603` -> `0.16931815540668732`
- Surface peak period shift B vs A (%): `-10.80562182914802`

## Case-Local Amplification
- Surface/Input PGA amplification: `2.316633296406254` -> `1.4049521121249928`
- Surface/Input peak PSA amplification: `3.4046941515170963` -> `1.5537827791138135`

## Profile
- gamma_max NRMSE: `0.7979525366032328`
- PGA profile NRMSE: `0.48820206860867044`
- max displacement NRMSE: `0.45518795213739704`
- max strain NRMSE: `0.7979525366032328`
- max stress ratio NRMSE: `0.5773479727439024`
- effective stress NRMSE: `0.0`

## Warnings
- none
