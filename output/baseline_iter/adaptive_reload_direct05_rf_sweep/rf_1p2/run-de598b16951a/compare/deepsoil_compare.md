# DEEPSOIL Comparison: run-de598b16951a

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.131017` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.038094`
- PGA diff: `3.809` %
- Surface RMSE: `0.341951` m/s^2
- Surface NRMSE: `0.113374`
- Surface correlation: `0.747557`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.814767` m/s^2
- PSA NRMSE: `0.072458`
- PSA max abs diff: `3.492906` m/s^2
- PSA diff at reference peak: `-7.430` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.028481598717280295`
- Max displacement NRMSE: `0.33829141353231024`
- Max strain NRMSE: `0.21027408354575758`
- Max stress ratio NRMSE: `0.4411657535621918`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.038493108900684955`
- Mobilized friction angle NRMSE: `0.4138933378499633`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.21027408354575763`
- tau_peak NRMSE: `0.038493108900684955`
- Secant G/Gmax NRMSE: `0.07789039489053769`
- Worst gamma layer: `L1`
- Worst tau layer: `L2`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.247073e-05 | 2.925981e-05 | 79.327 | 12.953298 | 12.100000 | 7.052 | 0.762415 | 0.811359 | -6.032 | 0.330113 | 95.918 |
| L2 | 6.000 | 1.514033e-04 | 1.023814e-04 | 47.882 | 38.716570 | 36.100000 | 7.248 | 0.656163 | 0.691808 | -5.152 |  |  |
| L3 | 10.000 | 1.950487e-04 | 1.855473e-04 | 5.121 | 54.472190 | 57.600000 | -5.430 | 0.623157 | 0.609069 | 2.313 |  |  |
| L4 | 14.000 | 3.586367e-04 | 2.599750e-04 | 37.950 | 79.422729 | 74.700000 | 6.322 | 0.464166 | 0.563752 | -17.665 |  |  |
| L5 | 18.000 | 3.875781e-04 | 3.017603e-04 | 28.439 | 81.193342 | 84.900000 | -4.366 | 0.473347 | 0.552007 | -14.250 |  |  |

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
- Recorded loop diff %: `95.9175265401026`
- Stress-path NRMSE: `0.33011349024574654`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.027254863747360483`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.16519102191780177`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.027254863747360483`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.16519102191780177`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p2\run-de598b16951a\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.077136e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.330113`
- sw loop energy: `2.243100e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `95.918` %
- sw tau_peak: `12.129307` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `10.694` %
- gamma_peak diff: `14.562` %

## Warnings
- None
