# DEEPSOIL Comparison: run-0724dfb421f7

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.146046870732979` m/s^2
- Applied input PGA: `1.0730234353664896` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `2.285416` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.757734`
- PGA diff: `-24.227` %
- Surface RMSE: `0.278872` m/s^2
- Surface NRMSE: `0.092461`
- Surface correlation: `0.756348`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.937111` m/s^2
- PSA NRMSE: `0.083338`
- PSA max abs diff: `3.249199` m/s^2
- PSA diff at reference peak: `-28.895` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.16951872497680434`
- Max displacement NRMSE: `0.36469060123666797`
- Max strain NRMSE: `0.11770039400755951`
- Max stress ratio NRMSE: `0.569089498036812`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.18292250204361218`
- Mobilized friction angle NRMSE: `0.54647056755953`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.11770039400755948`
- tau_peak NRMSE: `0.18292250204361218`
- Secant G/Gmax NRMSE: `0.21811175236703492`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.535173e-05 | 2.925981e-05 | 54.997 | 9.301991 | 12.100000 | -23.124 | 0.646489 | 0.811359 | -20.320 | 0.254596 | 102.976 |
| L2 | 6.000 | 1.316066e-04 | 1.023814e-04 | 28.545 | 27.650383 | 36.100000 | -23.406 | 0.516926 | 0.691808 | -25.279 |  |  |
| L3 | 10.000 | 2.310553e-04 | 1.855473e-04 | 24.526 | 43.377856 | 57.600000 | -24.691 | 0.424583 | 0.609069 | -30.290 |  |  |
| L4 | 14.000 | 3.113303e-04 | 2.599750e-04 | 19.754 | 55.429812 | 74.700000 | -25.797 | 0.378144 | 0.563752 | -32.924 |  |  |
| L5 | 18.000 | 3.238055e-04 | 3.017603e-04 | 7.306 | 61.382160 | 84.900000 | -27.701 | 0.377836 | 0.552007 | -31.552 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 0.800 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 0.800 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 0.800 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 0.800 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 0.800 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `0.8`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `102.97644077306941`
- Stress-path NRMSE: `0.2545955141384049`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.0479044964445098`
- Backbone envelope tau NRMSE: `0.02261876061166236`
- Recorded envelope secant NRMSE: `0.29602026713306107`
- Backbone envelope secant NRMSE: `0.20009479467797667`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `True`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.823019e-05`
- Recorded envelope tau NRMSE: `0.0479044964445098`
- Backbone envelope tau NRMSE: `0.02261876061166236`
- Recorded envelope secant NRMSE: `0.29602026713306107`
- Backbone envelope secant NRMSE: `0.20009479467797667`
- Backbone tau closer: `True`
- Backbone secant closer: `True`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_0p8\run-0724dfb421f7\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.489552e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.254596`
- sw loop energy: `2.323919e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `102.976` %
- sw tau_peak: `8.423875` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-23.123` %
- gamma_peak diff: `-7.314` %

## Warnings
- None
