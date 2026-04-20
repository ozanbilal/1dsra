# DEEPSOIL Comparison: run-420690406f4a

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `21.052719801890525` m/s^2
- Applied input PGA: `10.526359900945263` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `12.934115` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `4.288328`
- PGA diff: `328.833` %
- Surface RMSE: `2.522940` m/s^2
- Surface NRMSE: `0.836485`
- Surface correlation: `0.563687`

## PSA
- PSA points compared: `80`
- PSA RMSE: `19.800561` m/s^2
- PSA NRMSE: `1.760877`
- PSA max abs diff: `45.022584` m/s^2
- PSA diff at reference peak: `339.686` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `39.48852439231403` %

## Input Motion
- Input history NRMSE: `1.0062741449790598`
- Input PSA NRMSE: `3.4412024257890197`
- Applied input history NRMSE: `1.0062741449790598`
- Applied input PSA NRMSE: `3.296672167787897`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.0`
- PGA-vs-depth NRMSE: `3.903993248973987`
- Max displacement NRMSE: `5.455152523447251`
- Max strain NRMSE: `7.773613786821537`
- Max stress ratio NRMSE: `2.4448443027099787`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `1.6996779365228514`
- Mobilized friction angle NRMSE: `1.1093716861113836`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs\mrd_wide\run-420690406f4a\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- Stress-path NRMSE: `1.108035`
- Loop energy diff: `4124.213` %
- tau_peak diff: `339.434` %
- gamma_peak diff: `392.385` %

## Warnings
- None
