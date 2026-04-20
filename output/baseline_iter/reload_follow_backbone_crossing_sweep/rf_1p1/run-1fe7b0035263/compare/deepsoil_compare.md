# DEEPSOIL Comparison: run-1fe7b0035263

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.136011` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.039750`
- PGA diff: `3.975` %
- Surface RMSE: `0.314023` m/s^2
- Surface NRMSE: `0.104115`
- Surface correlation: `0.755644`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.854126` m/s^2
- PSA NRMSE: `0.075958`
- PSA max abs diff: `3.209192` m/s^2
- PSA diff at reference peak: `-16.818` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.10268548965293686`
- Max displacement NRMSE: `0.3423763426861308`
- Max strain NRMSE: `0.2690474219398296`
- Max stress ratio NRMSE: `0.47261837164633885`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.05405124028688204`
- Mobilized friction angle NRMSE: `0.4460982435616226`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.2690474219398296`
- tau_peak NRMSE: `0.05405124028688204`
- Secant G/Gmax NRMSE: `0.181179239178588`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L3`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.857283e-05 | 2.925981e-05 | 100.182 | 12.772005 | 12.100000 | 5.554 | 0.674764 | 0.811359 | -16.835 | 0.301961 | 134.879 |
| L2 | 6.000 | 1.623463e-04 | 1.023814e-04 | 58.570 | 34.072954 | 36.100000 | -5.615 | 0.516230 | 0.691808 | -25.379 |  |  |
| L3 | 10.000 | 3.059466e-04 | 1.855473e-04 | 64.889 | 53.818714 | 57.600000 | -6.565 | 0.416977 | 0.609069 | -31.539 |  |  |
| L4 | 14.000 | 3.368837e-04 | 2.599750e-04 | 29.583 | 68.828966 | 74.700000 | -7.859 | 0.430461 | 0.563752 | -23.643 |  |  |
| L5 | 18.000 | 3.917121e-04 | 3.017603e-04 | 29.809 | 77.691349 | 84.900000 | -8.491 | 0.489591 | 0.552007 | -11.307 |  |  |

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
- Recorded loop diff %: `134.87924664835498`
- Stress-path NRMSE: `0.30196145228631976`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.08382680063395083`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.27292032473966116`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `True`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.08382680063395083`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.27292032473966116`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `True`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p1\run-1fe7b0035263\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.146469e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.301961`
- sw loop energy: `2.689181e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `134.879` %
- sw tau_peak: `10.036915` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-8.402` %
- gamma_peak diff: `17.143` %

## Warnings
- None
