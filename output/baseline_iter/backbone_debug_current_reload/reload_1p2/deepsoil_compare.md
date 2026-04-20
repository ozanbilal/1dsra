# DEEPSOIL Comparison: run-4ae945e0523c

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p2\run-4ae945e0523c`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p2\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p2\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p2\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p2\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.1460672722560035` m/s^2
- Applied input PGA: `1.0730336361280017` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9900` s
- Overlap samples: `5999`
- PGA (GeoWave): `2.615952` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.867323`
- PGA diff: `-13.268` %
- Surface RMSE: `0.287616` m/s^2
- Surface NRMSE: `0.095360`
- Surface correlation: `0.789494`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.799617` m/s^2
- PSA NRMSE: `0.071110`
- PSA max abs diff: `2.756595` m/s^2
- PSA diff at reference peak: `-17.320` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p2\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p2\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.10012111261406094`
- Max displacement NRMSE: `0.34476951846325665`
- Max strain NRMSE: `0.14632273761043052`
- Max stress ratio NRMSE: `0.5158846101167622`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.09972752590366923`
- Mobilized friction angle NRMSE: `0.49045738291968954`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.14632273761043052`
- tau_peak NRMSE: `0.09972752590366923`
- Secant G/Gmax NRMSE: `0.16191862619560318`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.816661e-05 | 2.925981e-05 | 64.617 | 10.643926 | 12.100000 | -12.034 | 0.689838 | 0.811359 | -14.977 | 0.289492 | 131.458 |
| L2 | 6.000 | 1.360579e-04 | 1.023814e-04 | 32.893 | 31.385999 | 36.100000 | -13.058 | 0.563031 | 0.691808 | -18.614 |  |  |
| L3 | 10.000 | 2.380046e-04 | 1.855473e-04 | 28.272 | 49.949122 | 57.600000 | -13.283 | 0.472619 | 0.609069 | -22.403 |  |  |
| L4 | 14.000 | 3.201602e-04 | 2.599750e-04 | 23.150 | 64.130190 | 74.700000 | -14.150 | 0.426684 | 0.563752 | -24.314 |  |  |
| L5 | 18.000 | 3.451476e-04 | 3.017603e-04 | 14.378 | 72.099984 | 84.900000 | -15.077 | 0.419573 | 0.552007 | -23.991 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 1.200 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 1.200 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 1.200 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 1.200 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 1.200 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `1.2`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `131.45797279550814`
- Stress-path NRMSE: `0.28949205918212606`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.03521813974929291`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.2020777351771466`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `True`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.03521813974929291`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.2020777351771466`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `True`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p2\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.556880e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.289492`
- sw loop energy: `2.650010e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `131.458` %
- sw tau_peak: `9.271083` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-15.391` %
- gamma_peak diff: `-4.807` %

## Warnings
- None
