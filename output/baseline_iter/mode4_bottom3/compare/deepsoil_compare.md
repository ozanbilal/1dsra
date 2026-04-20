# DEEPSOIL Comparison: run-2b0b19c0ee05

## Inputs
- GeoWave run: `output\baseline_iter\mode4_bottom3\run-2b0b19c0ee05`
- DEEPSOIL workbook: `tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `output\baseline_iter\mode4_bottom3\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `output\baseline_iter\mode4_bottom3\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `output\baseline_iter\mode4_bottom3\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `output\baseline_iter\mode4_bottom3\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.608437` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.864832`
- PGA diff: `-13.517` %
- Surface RMSE: `0.295211` m/s^2
- Surface NRMSE: `0.097878`
- Surface correlation: `0.770903`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.793404` m/s^2
- PSA NRMSE: `0.070558`
- PSA max abs diff: `2.621539` m/s^2
- PSA diff at reference peak: `-16.792` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `output\baseline_iter\mode4_bottom3\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `output\baseline_iter\mode4_bottom3\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.10788513287929809`
- Max displacement NRMSE: `0.34807566383943384`
- Max strain NRMSE: `0.1405040963146027`
- Max stress ratio NRMSE: `0.5175953310074518`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.10395186447976959`
- Mobilized friction angle NRMSE: `0.4922797958648985`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.14050409631460267`
- tau_peak NRMSE: `0.10395186447976959`
- Secant G/Gmax NRMSE: `0.16636556352193044`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.878566e-05 | 2.925981e-05 | 66.733 | 10.647203 | 12.100000 | -12.007 | 0.681691 | 0.811359 | -15.982 | 0.288632 | 136.718 |
| L2 | 6.000 | 1.366702e-04 | 1.023814e-04 | 33.491 | 31.301315 | 36.100000 | -13.293 | 0.556922 | 0.691808 | -19.498 |  |  |
| L3 | 10.000 | 2.377122e-04 | 1.855473e-04 | 28.114 | 49.668823 | 57.600000 | -13.769 | 0.468250 | 0.609069 | -23.120 |  |  |
| L4 | 14.000 | 3.160801e-04 | 2.599750e-04 | 21.581 | 63.697507 | 74.700000 | -14.729 | 0.426223 | 0.563752 | -24.395 |  |  |
| L5 | 18.000 | 3.412856e-04 | 3.017603e-04 | 13.098 | 71.470480 | 84.900000 | -15.818 | 0.420293 | 0.552007 | -23.861 |  |  |

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
- Recorded loop diff %: `136.71817642641307`
- Stress-path NRMSE: `0.2886316206754098`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.03777681368944781`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.18834501565128553`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.03777681368944781`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.18834501565128553`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `output\baseline_iter\mode4_bottom3\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.394390e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.288632`
- sw loop energy: `2.710235e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `136.718` %
- sw tau_peak: `8.302246` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-24.233` %
- gamma_peak diff: `-10.857` %

## Warnings
- None
