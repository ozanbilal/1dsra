# DEEPSOIL Comparison: run-4e36aff16e5d

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.070438` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.018009`
- PGA diff: `1.801` %
- Surface RMSE: `0.350559` m/s^2
- Surface NRMSE: `0.116228`
- Surface correlation: `0.747779`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.902315` m/s^2
- PSA NRMSE: `0.080243`
- PSA max abs diff: `4.394142` m/s^2
- PSA diff at reference peak: `-2.839` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.056850680175589606`
- Max displacement NRMSE: `0.344563120658458`
- Max strain NRMSE: `0.18990072944882552`
- Max stress ratio NRMSE: `0.4150192702377727`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.06401350807213255`
- Mobilized friction angle NRMSE: `0.38751894207635545`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.18990072944882552`
- tau_peak NRMSE: `0.06401350807213255`
- Secant G/Gmax NRMSE: `0.05639404298060982`
- Worst gamma layer: `L1`
- Worst tau layer: `L3`
- Worst secant layer: `L5`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.679593e-05 | 2.925981e-05 | 94.109 | 13.435254 | 12.100000 | 11.035 | 0.749417 | 0.811359 | -7.634 | 0.314704 | 54.583 |
| L2 | 6.000 | 1.502506e-04 | 1.023814e-04 | 46.756 | 38.731988 | 36.100000 | 7.291 | 0.656369 | 0.691808 | -5.123 |  |  |
| L3 | 10.000 | 2.557010e-04 | 1.855473e-04 | 37.809 | 64.933413 | 57.600000 | 12.732 | 0.565617 | 0.609069 | -7.134 |  |  |
| L4 | 14.000 | 3.323231e-04 | 2.599750e-04 | 27.829 | 82.942215 | 74.700000 | 11.034 | 0.526779 | 0.563752 | -6.558 |  |  |
| L5 | 18.000 | 3.584482e-04 | 3.017603e-04 | 18.786 | 80.745600 | 84.900000 | -4.893 | 0.505962 | 0.552007 | -8.341 |  |  |

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
- Recorded loop diff %: `54.58320262629291`
- Stress-path NRMSE: `0.3147040937229936`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.01576809427862861`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.6513867770861359`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `False`
- Backbone envelope secant closer: `True`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.01576809427862861`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.6513867770861359`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `False`
- Backbone secant closer: `True`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\adaptive_reload_direct05_rf_sweep\rf_1p4\run-4e36aff16e5d\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.087002e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.314704`
- sw loop energy: `1.769855e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `54.583` %
- sw tau_peak: `11.304682` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `3.168` %
- gamma_peak diff: `14.929` %

## Warnings
- None
