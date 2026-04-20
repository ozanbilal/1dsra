# DEEPSOIL Comparison: run-b62b11090395

## Inputs
- GeoWave run: `output\baseline_iter\mode3_experimental\run-b62b11090395`
- DEEPSOIL workbook: `tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `output\baseline_iter\mode3_experimental\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `output\baseline_iter\mode3_experimental\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `output\baseline_iter\mode3_experimental\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `output\baseline_iter\mode3_experimental\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `4.948629` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.640727`
- PGA diff: `64.073` %
- Surface RMSE: `0.633901` m/s^2
- Surface NRMSE: `0.210171`
- Surface correlation: `0.609080`

## PSA
- PSA points compared: `80`
- PSA RMSE: `3.414248` m/s^2
- PSA NRMSE: `0.303631`
- PSA max abs diff: `14.454751` m/s^2
- PSA diff at reference peak: `88.701` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `output\baseline_iter\mode3_experimental\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `output\baseline_iter\mode3_experimental\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.3608018335242325`
- Max displacement NRMSE: `0.35426040667062136`
- Max strain NRMSE: `0.17055973793130688`
- Max stress ratio NRMSE: `0.24984862074415307`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.2401982554892125`
- Mobilized friction angle NRMSE: `0.22838400544382947`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1705597379313069`
- tau_peak NRMSE: `0.2401982554892125`
- Secant G/Gmax NRMSE: `0.13677256143066535`
- Worst gamma layer: `L1`
- Worst tau layer: `L1`
- Worst secant layer: `L1`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 6.609142e-05 | 2.925981e-05 | 125.878 | 23.281185 | 12.100000 | 92.406 | 0.993406 | 0.811359 | 22.437 | 0.572859 | 8.669 |
| L2 | 6.000 | 1.598114e-04 | 1.023814e-04 | 56.094 | 49.685927 | 36.100000 | 37.634 | 0.658110 | 0.691808 | -4.871 |  |  |
| L3 | 10.000 | 2.412985e-04 | 1.855473e-04 | 30.047 | 80.094075 | 57.600000 | 39.052 | 0.730216 | 0.609069 | 19.891 |  |  |
| L4 | 14.000 | 2.816602e-04 | 2.599750e-04 | 8.341 | 100.974848 | 74.700000 | 35.174 | 0.663735 | 0.563752 | 17.735 |  |  |
| L5 | 18.000 | 3.725532e-04 | 3.017603e-04 | 23.460 | 108.845576 | 84.900000 | 28.204 | 0.603228 | 0.552007 | 9.279 |  |  |

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
- Recorded loop diff %: `8.668998794785741`
- Stress-path NRMSE: `0.5728587604772782`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.21024619061669497`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.3212011380041741`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `True`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.21024619061669497`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.3212011380041741`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `True`

## Hysteresis
- Hysteresis CSV: `output\baseline_iter\mode3_experimental\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `4.598089e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.572859`
- sw loop energy: `1.244174e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `8.669` %
- sw tau_peak: `23.281185` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `112.467` %
- gamma_peak diff: `71.187` %

## Warnings
- None
