# DEEPSOIL Comparison: run-a5d128877e23

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.071283` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.018289`
- PGA diff: `1.829` %
- Surface RMSE: `0.476341` m/s^2
- Surface NRMSE: `0.157932`
- Surface correlation: `0.676070`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.640102` m/s^2
- PSA NRMSE: `0.145855`
- PSA max abs diff: `8.350580` m/s^2
- PSA diff at reference peak: `12.121` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.06796387273525906`
- Max displacement NRMSE: `0.314370938578447`
- Max strain NRMSE: `0.1937540966925158`
- Max stress ratio NRMSE: `0.4330589264655593`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.0356734522630859`
- Mobilized friction angle NRMSE: `0.4047818266762956`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\literal_rigid_outcrop\run-a5d128877e23\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- Stress-path NRMSE: `0.343197`
- Loop energy diff: `229.485` %
- tau_peak diff: `4.794` %
- gamma_peak diff: `12.173` %

## Warnings
- None
