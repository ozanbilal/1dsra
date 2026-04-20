# DEEPSOIL Comparison: run-cbc25a371ce3

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `within`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.1467799709269246` m/s^2
- Applied input PGA: `2.1467799709269246` m/s^2
- Base motion semantics ok: `False`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `5.522301` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.830928`
- PGA diff: `83.093` %
- Surface RMSE: `0.950009` m/s^2
- Surface NRMSE: `0.314977`
- Surface correlation: `0.679217`

## PSA
- PSA points compared: `80`
- PSA RMSE: `5.813989` m/s^2
- PSA NRMSE: `0.517042`
- PSA max abs diff: `22.991457` m/s^2
- PSA diff at reference peak: `101.305` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.0`
- PGA-vs-depth NRMSE: `0.7916184379672639`
- Max displacement NRMSE: `0.5729094389890628`
- Max strain NRMSE: `1.1570488476939889`
- Max stress ratio NRMSE: `0.785116802150827`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.6153208838980619`
- Mobilized friction angle NRMSE: `0.5413700179052776`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\semantics_check\baseline_rigid_within\run-cbc25a371ce3\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- Stress-path NRMSE: `0.522392`
- Loop energy diff: `709.662` %
- tau_peak diff: `67.917` %
- gamma_peak diff: `75.837` %

## Warnings
- None
