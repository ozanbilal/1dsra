# DEEPSOIL Comparison: run-dd9d454813dc

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.014720` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.999536`
- PGA diff: `-0.046` %
- Surface RMSE: `0.335960` m/s^2
- Surface NRMSE: `0.111388`
- Surface correlation: `0.754772`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.818548` m/s^2
- PSA NRMSE: `0.072794`
- PSA max abs diff: `3.864672` m/s^2
- PSA diff at reference peak: `-8.473` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.03460579330752586`
- Max displacement NRMSE: `0.35407510552672217`
- Max strain NRMSE: `0.13971033316644313`
- Max stress ratio NRMSE: `0.4553201108650113`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.02611219637486544`
- Mobilized friction angle NRMSE: `0.4278803877197665`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.13971033316644318`
- tau_peak NRMSE: `0.02611219637486544`
- Secant G/Gmax NRMSE: `0.07744049764136066`
- Worst gamma layer: `L1`
- Worst tau layer: `L1`
- Worst secant layer: `L5`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.497830e-05 | 2.925981e-05 | 87.897 | 12.801582 | 12.100000 | 5.798 | 0.741920 | 0.811359 | -8.558 | 0.310996 | 77.460 |
| L2 | 6.000 | 1.138539e-04 | 1.023814e-04 | 11.206 | 34.082159 | 36.100000 | -5.590 | 0.699893 | 0.691808 | 1.169 |  |  |
| L3 | 10.000 | 2.406084e-04 | 1.855473e-04 | 29.675 | 59.021549 | 57.600000 | 2.468 | 0.537325 | 0.609069 | -11.779 |  |  |
| L4 | 14.000 | 2.568308e-04 | 2.599750e-04 | -1.209 | 70.478121 | 74.700000 | -5.652 | 0.582404 | 0.563752 | 3.309 |  |  |
| L5 | 18.000 | 3.728395e-04 | 3.017603e-04 | 23.555 | 85.305995 | 84.900000 | 0.478 | 0.455275 | 0.552007 | -17.524 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 1.400 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 1.400 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 1.400 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 1.400 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 1.400 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `1.4`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `77.45966925798484`
- Stress-path NRMSE: `0.3109961001730878`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.016309727575892156`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.1431661266377923`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `False`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.016309727575892156`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.1431661266377923`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `False`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_follow_backbone_crossing_sweep\rf_1p4\run-dd9d454813dc\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.248945e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.310996`
- sw loop energy: `2.031772e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `77.460` %
- sw tau_peak: `12.402510` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `13.187` %
- gamma_peak diff: `20.958` %

## Warnings
- None
