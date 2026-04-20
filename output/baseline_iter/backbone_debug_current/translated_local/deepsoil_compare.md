# DEEPSOIL Comparison: run-06695f88ceb5

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_translated_local\run-06695f88ceb5`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\translated_local\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\translated_local\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\translated_local\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\translated_local\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.868772` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.951146`
- PGA diff: `-4.885` %
- Surface RMSE: `0.329387` m/s^2
- Surface NRMSE: `0.109209`
- Surface correlation: `0.765345`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.857141` m/s^2
- PSA NRMSE: `0.076226`
- PSA max abs diff: `4.122133` m/s^2
- PSA diff at reference peak: `-6.983` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\translated_local\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\translated_local\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.059491937355052996`
- Max displacement NRMSE: `0.3421188312109442`
- Max strain NRMSE: `0.15115796966074813`
- Max stress ratio NRMSE: `0.47583666291776494`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.0408624144223456`
- Mobilized friction angle NRMSE: `0.4489113976512777`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.15115796966074813`
- tau_peak NRMSE: `0.0408624144223456`
- Secant G/Gmax NRMSE: `0.1173155108532125`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.064090e-05 | 2.925981e-05 | 73.073 | 11.727196 | 12.100000 | -3.081 | 0.718152 | 0.811359 | -11.488 | 0.316379 | 146.674 |
| L2 | 6.000 | 1.395663e-04 | 1.023814e-04 | 36.320 | 34.397463 | 36.100000 | -4.716 | 0.597652 | 0.691808 | -13.610 |  |  |
| L3 | 10.000 | 2.405790e-04 | 1.855473e-04 | 29.659 | 54.737636 | 57.600000 | -4.969 | 0.509124 | 0.609069 | -16.410 |  |  |
| L4 | 14.000 | 3.188198e-04 | 2.599750e-04 | 22.635 | 70.347873 | 74.700000 | -5.826 | 0.466932 | 0.563752 | -17.174 |  |  |
| L5 | 18.000 | 3.472782e-04 | 3.017603e-04 | 15.084 | 79.422259 | 84.900000 | -6.452 | 0.460438 | 0.552007 | -16.588 |  |  |

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
- Recorded loop diff %: `146.67388396120268`
- Stress-path NRMSE: `0.3163792924440307`
- Backbone loop closer than recorded loop: `True`
- Recorded envelope tau NRMSE: `0.02845961780823889`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.13356279147029387`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `reload_semantics`
- Rationale: Classical backbone/Masing energy is closer to DEEPSOIL than the recorded solver loop, pointing at reload semantics.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.02845961780823889`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.13356279147029387`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\translated_local\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.756982e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.316379`
- sw loop energy: `2.824220e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `146.674` %
- sw tau_peak: `10.337825` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-5.656` %
- gamma_peak diff: `2.643` %

## Warnings
- None
