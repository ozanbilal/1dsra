# DEEPSOIL Comparison: run-1dbf17dbe5d1

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `14.074339` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `4.666371`
- PGA diff: `366.637` %
- Surface RMSE: `2.506175` m/s^2
- Surface NRMSE: `0.830927`
- Surface correlation: `0.563556`

## PSA
- PSA points compared: `80`
- PSA RMSE: `18.625900` m/s^2
- PSA NRMSE: `1.656414`
- PSA max abs diff: `39.706855` m/s^2
- PSA diff at reference peak: `309.453` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `-5.39583577224` %

## Input Motion
- Input history NRMSE: `1.0062741449790598`
- Input PSA NRMSE: `3.4412024257890197`
- Applied input history NRMSE: `1.0062741449790598`
- Applied input PSA NRMSE: `3.296672167787897`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.0`
- PGA-vs-depth NRMSE: `3.820365573254952`
- Max displacement NRMSE: `5.600293737385905`
- Max strain NRMSE: `8.099099509773039`
- Max stress ratio NRMSE: `2.374572468139906`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `1.6244852180628877`
- Mobilized friction angle NRMSE: `1.0907792722610388`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit\dc_wide_refit\run-1dbf17dbe5d1\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- Stress-path NRMSE: `1.131196`
- Loop energy diff: `1454.103` %
- tau_peak diff: `335.450` %
- gamma_peak diff: `351.487` %

## Warnings
- None
