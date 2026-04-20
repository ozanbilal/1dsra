# DEEPSOIL Comparison: run-287bc5b46f6c

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\runs\run-287bc5b46f6c`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.1467799709269246` m/s^2
- Applied input PGA: `1.0733899854634623` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `3.286402` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.089612`
- PGA diff: `8.961` %
- Surface RMSE: `0.390071` m/s^2
- Surface NRMSE: `0.129329`
- Surface correlation: `0.689139`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.221035` m/s^2
- PSA NRMSE: `0.108587`
- PSA max abs diff: `5.873911` m/s^2
- PSA diff at reference peak: `-1.803` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.06783217636336523`
- Max displacement NRMSE: `0.3333763501327739`
- Max strain NRMSE: `0.17225164307971247`
- Max stress ratio NRMSE: `0.42924920767447045`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.03689382211194845`
- Mobilized friction angle NRMSE: `0.4015178398713855`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1722516430797125`
- tau_peak NRMSE: `0.03689382211194845`
- Secant G/Gmax NRMSE: `0.093444222258389`
- Worst gamma layer: `L1`
- Worst tau layer: `L2`
- Worst secant layer: `L1`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.363629e-05 | 2.925981e-05 | 83.310 | 11.988156 | 12.100000 | -0.924 | 0.687428 | 0.811359 | -15.274 | 0.321790 | 117.799 |
| L2 | 6.000 | 1.542868e-04 | 1.023814e-04 | 50.698 | 41.616649 | 36.100000 | 15.282 | 0.643211 | 0.691808 | -7.025 |  |  |
| L3 | 10.000 | 2.512905e-04 | 1.855473e-04 | 35.432 | 60.136659 | 57.600000 | 4.404 | 0.538354 | 0.609069 | -11.610 |  |  |
| L4 | 14.000 | 3.234777e-04 | 2.599750e-04 | 24.426 | 77.199573 | 74.700000 | 3.346 | 0.500952 | 0.563752 | -11.140 |  |  |
| L5 | 18.000 | 3.449550e-04 | 3.017603e-04 | 14.314 | 87.334673 | 84.900000 | 2.868 | 0.506445 | 0.552007 | -8.254 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 1.100 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 1.100 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 1.100 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 1.100 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 1.100 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `1.1`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `117.79853717770554`
- Stress-path NRMSE: `0.32178990988031553`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.03303164280163054`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.1674243557373202`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.03303164280163054`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.1674243557373202`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_explicit_gref_latched\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.903942e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.321790`
- sw loop energy: `2.493621e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `117.799` %
- sw tau_peak: `9.913750` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-9.526` %
- gamma_peak diff: `8.114` %

## Warnings
- None
