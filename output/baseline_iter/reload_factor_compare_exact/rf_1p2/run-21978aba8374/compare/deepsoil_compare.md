# DEEPSOIL Comparison: run-21978aba8374

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.615939` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.867319`
- PGA diff: `-13.268` %
- Surface RMSE: `0.302161` m/s^2
- Surface NRMSE: `0.100182`
- Surface correlation: `0.765508`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.799623` m/s^2
- PSA NRMSE: `0.071111`
- PSA max abs diff: `2.756426` m/s^2
- PSA diff at reference peak: `-17.319` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.10012060173060758`
- Max displacement NRMSE: `0.3447867524007979`
- Max strain NRMSE: `0.14629541325866682`
- Max stress ratio NRMSE: `0.5158864388355572`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.09973068168715593`
- Mobilized friction angle NRMSE: `0.4904593007045894`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.14629541325866685`
- tau_peak NRMSE: `0.09973068168715593`
- Secant G/Gmax NRMSE: `0.16190453704687677`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.816571e-05 | 2.925981e-05 | 64.614 | 10.643897 | 12.100000 | -12.034 | 0.689848 | 0.811359 | -14.976 | 0.289076 | 131.540 |
| L2 | 6.000 | 1.360545e-04 | 1.023814e-04 | 32.890 | 31.385844 | 36.100000 | -13.059 | 0.563041 | 0.691808 | -18.613 |  |  |
| L3 | 10.000 | 2.379972e-04 | 1.855473e-04 | 28.268 | 49.948844 | 57.600000 | -13.283 | 0.472630 | 0.609069 | -22.401 |  |  |
| L4 | 14.000 | 3.201488e-04 | 2.599750e-04 | 23.146 | 64.129990 | 74.700000 | -14.150 | 0.426696 | 0.563752 | -24.311 |  |  |
| L5 | 18.000 | 3.451333e-04 | 3.017603e-04 | 14.373 | 72.099490 | 84.900000 | -15.077 | 0.419587 | 0.552007 | -23.989 |  |  |

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
- Recorded loop diff %: `131.5401633127553`
- Stress-path NRMSE: `0.28907644901628726`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.03530374238186226`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.18912085775191487`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.03530374238186226`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.18912085775191487`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_factor_compare_exact\rf_1p2\run-21978aba8374\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.521550e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.289076`
- sw loop energy: `2.650951e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `131.540` %
- sw tau_peak: `9.166578` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-16.345` %
- gamma_peak diff: `-6.123` %

## Warnings
- None
