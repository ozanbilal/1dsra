# DEEPSOIL Comparison: run-21809b0964f4

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: ``
- Motion input type: ``
- Damping mode: ``
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.146046870732979` m/s^2
- Applied input PGA: `1.0730234353664896` m/s^2
- Base motion semantics ok: `None`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `3.051922` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.011870`
- PGA diff: `1.187` %
- Surface RMSE: `0.355956` m/s^2
- Surface NRMSE: `0.118018`
- Surface correlation: `0.760875`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.978593` m/s^2
- PSA NRMSE: `0.087027`
- PSA max abs diff: `5.088407` m/s^2
- PSA diff at reference peak: `5.668` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.04776309439565175`
- Max displacement NRMSE: `0.34448618906819717`
- Max strain NRMSE: `0.1469396151625486`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.14693961516254864`
- tau_peak NRMSE: `0.004507322912916972`
- Secant G/Gmax NRMSE: `0.07933398849413238`
- Worst gamma layer: `L1`
- Worst tau layer: `L1`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.169504e-05 | 2.925981e-05 | 76.676 | 12.396717 | 12.100000 | 2.452 | 0.739874 | 0.811359 | -8.811 | 0.307993 | 158.385 |
| L2 | 6.000 | 1.389063e-04 | 1.023814e-04 | 35.675 | 36.522519 | 36.100000 | 1.170 | 0.631073 | 0.691808 | -8.779 |  |  |
| L3 | 10.000 | 2.389273e-04 | 1.855473e-04 | 28.769 | 58.198558 | 57.600000 | 1.039 | 0.542752 | 0.609069 | -10.888 |  |  |
| L4 | 14.000 | 3.160300e-04 | 2.599750e-04 | 21.562 | 74.956478 | 74.700000 | 0.343 | 0.500383 | 0.563752 | -11.241 |  |  |
| L5 | 18.000 | 3.464975e-04 | 3.017603e-04 | 14.825 | 84.696107 | 84.900000 | -0.240 | 0.492813 | 0.552007 | -10.723 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_local\run-21809b0964f4\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.751542e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.307993`
- sw loop energy: `2.958301e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `158.385` %
- sw tau_peak: `10.641985` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-2.880` %
- gamma_peak diff: `2.440` %

## Warnings
- None
