# DEEPSOIL Comparison: run-b019877a2d32

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.1467799709269246` m/s^2
- Applied input PGA: `1.0733899854634623` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `3.707517` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.229234`
- PGA diff: `22.923` %
- Surface RMSE: `0.645781` m/s^2
- Surface NRMSE: `0.214110`
- Surface correlation: `0.585489`

## PSA
- PSA points compared: `80`
- PSA RMSE: `2.938956` m/s^2
- PSA NRMSE: `0.261363`
- PSA max abs diff: `13.228837` m/s^2
- PSA diff at reference peak: `117.645` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `0.0` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.0`
- PGA-vs-depth NRMSE: `0.19886223079139717`
- Max displacement NRMSE: `0.3048532615986548`
- Max strain NRMSE: `0.20870191905309834`
- Max stress ratio NRMSE: `0.2551119524356263`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.2092640631706308`
- Mobilized friction angle NRMSE: `0.20387905691719235`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\mrd_soft90_refit\run-b019877a2d32\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- Stress-path NRMSE: `0.380392`
- Loop energy diff: `142.582` %
- tau_peak diff: `21.162` %
- gamma_peak diff: `15.666` %

## Warnings
- None
