# DEEPSOIL Comparison: run-65d4ce5f6fe0

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.747685` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.911000`
- PGA diff: `-8.900` %
- Surface RMSE: `0.304034` m/s^2
- Surface NRMSE: `0.100803`
- Surface correlation: `0.785461`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.814708` m/s^2
- PSA NRMSE: `0.072453`
- PSA max abs diff: `3.488029` m/s^2
- PSA diff at reference peak: `-12.184` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.07372123467987328`
- Max displacement NRMSE: `0.3422580904047174`
- Max strain NRMSE: `0.1504527835659583`
- Max stress ratio NRMSE: `0.49456456295863827`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.06774475401593014`
- Mobilized friction angle NRMSE: `0.46826605446520125`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1504527835659582`
- tau_peak NRMSE: `0.06774475401593014`
- Secant G/Gmax NRMSE: `0.13868985717145058`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.959750e-05 | 2.925981e-05 | 69.507 | 11.205282 | 12.100000 | -7.394 | 0.703560 | 0.811359 | -13.286 | 0.306269 | 138.273 |
| L2 | 6.000 | 1.381413e-04 | 1.023814e-04 | 34.928 | 32.988444 | 36.100000 | -8.619 | 0.580739 | 0.691808 | -16.055 |  |  |
| L3 | 10.000 | 2.389871e-04 | 1.855473e-04 | 28.801 | 52.429840 | 57.600000 | -8.976 | 0.492726 | 0.609069 | -19.102 |  |  |
| L4 | 14.000 | 3.212087e-04 | 2.599750e-04 | 23.554 | 67.615309 | 74.700000 | -9.484 | 0.447534 | 0.563752 | -20.615 |  |  |
| L5 | 18.000 | 3.465747e-04 | 3.017603e-04 | 14.851 | 76.068536 | 84.900000 | -10.402 | 0.441045 | 0.552007 | -20.102 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p4\run-65d4ce5f6fe0\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.855773e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.306269`
- sw loop energy: `2.728032e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `138.273` %
- sw tau_peak: `9.869552` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-9.929` %
- gamma_peak diff: `6.321` %

## Warnings
- None
