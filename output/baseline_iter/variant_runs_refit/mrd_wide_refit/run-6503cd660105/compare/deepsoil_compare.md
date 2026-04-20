# DEEPSOIL Comparison: run-6503cd660105

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `16.107933` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `5.340613`
- PGA diff: `434.061` %
- Surface RMSE: `2.533777` m/s^2
- Surface NRMSE: `0.840078`
- Surface correlation: `0.564740`

## PSA
- PSA points compared: `80`
- PSA RMSE: `19.590976` m/s^2
- PSA NRMSE: `1.742239`
- PSA max abs diff: `42.978080` m/s^2
- PSA diff at reference peak: `329.107` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `39.48852439231403` %

## Input Motion
- Input history NRMSE: `1.0062741449790598`
- Input PSA NRMSE: `3.4412024257890197`
- Applied input history NRMSE: `1.0062741449790598`
- Applied input PSA NRMSE: `3.296672167787897`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.0`
- PGA-vs-depth NRMSE: `3.7660638836417935`
- Max displacement NRMSE: `5.51025408686436`
- Max strain NRMSE: `7.973269514252634`
- Max stress ratio NRMSE: `2.5356938001027083`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `1.5962072332296813`
- Mobilized friction angle NRMSE: `1.1000697045790109`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\mrd_wide_refit\run-6503cd660105\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- Stress-path NRMSE: `1.117856`
- Loop energy diff: `4832.269` %
- tau_peak diff: `436.063` %
- gamma_peak diff: `684.003` %

## Warnings
- None
