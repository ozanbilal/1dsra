# DEEPSOIL Comparison: run-3c08c6064cba

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p6\run-3c08c6064cba`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p6\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p6\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p6\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p6\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.868785` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.951151`
- PGA diff: `-4.885` %
- Surface RMSE: `0.320419` m/s^2
- Surface NRMSE: `0.106236`
- Surface correlation: `0.780274`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.857134` m/s^2
- PSA NRMSE: `0.076226`
- PSA max abs diff: `4.122302` m/s^2
- PSA diff at reference peak: `-6.983` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p6\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p6\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.059492079321823974`
- Max displacement NRMSE: `0.3421038998813892`
- Max strain NRMSE: `0.15118192612961817`
- Max stress ratio NRMSE: `0.47583381693235405`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.04085903279484528`
- Mobilized friction angle NRMSE: `0.44890847843806647`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1511819261296182`
- tau_peak NRMSE: `0.04085903279484528`
- Secant G/Gmax NRMSE: `0.11732816468053321`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.064243e-05 | 2.925981e-05 | 73.078 | 11.727352 | 12.100000 | -3.080 | 0.718144 | 0.811359 | -11.489 | 0.316825 | 146.448 |
| L2 | 6.000 | 1.395693e-04 | 1.023814e-04 | 36.323 | 34.397541 | 36.100000 | -4.716 | 0.597643 | 0.691808 | -13.611 |  |  |
| L3 | 10.000 | 2.405854e-04 | 1.855473e-04 | 29.663 | 54.737893 | 57.600000 | -4.969 | 0.509113 | 0.609069 | -16.411 |  |  |
| L4 | 14.000 | 3.188297e-04 | 2.599750e-04 | 22.639 | 70.348230 | 74.700000 | -5.826 | 0.466921 | 0.563752 | -17.176 |  |  |
| L5 | 18.000 | 3.472907e-04 | 3.017603e-04 | 15.088 | 79.422715 | 84.900000 | -6.451 | 0.460425 | 0.552007 | -16.591 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 1.600 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 1.600 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 1.600 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 1.600 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 1.600 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `1.6`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `146.44795709168835`
- Stress-path NRMSE: `0.3168248705866137`
- Backbone loop closer than recorded loop: `True`
- Recorded envelope tau NRMSE: `0.028496078222619414`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.254603411852768`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `True`
- Suspected dominant source: `reload_semantics`
- Rationale: Classical backbone/Masing energy is closer to DEEPSOIL than the recorded solver loop, pointing at reload semantics.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.028496078222619414`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.254603411852768`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `True`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p6\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.804954e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.316825`
- sw loop energy: `2.821634e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `146.448` %
- sw tau_peak: `10.489457` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-4.272` %
- gamma_peak diff: `4.429` %

## Warnings
- None
