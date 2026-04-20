# DEEPSOIL Comparison: run-031a9bd90493

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.697604` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.225947`
- PGA diff: `22.595` %
- Surface RMSE: `0.647586` m/s^2
- Surface NRMSE: `0.214708`
- Surface correlation: `0.580422`

## PSA
- PSA points compared: `80`
- PSA RMSE: `2.932092` m/s^2
- PSA NRMSE: `0.260753`
- PSA max abs diff: `13.136695` m/s^2
- PSA diff at reference peak: `116.826` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `0.0` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.0`
- PGA-vs-depth NRMSE: `0.20152678527993825`
- Max displacement NRMSE: `0.2995593371625774`
- Max strain NRMSE: `0.21786697156950963`
- Max stress ratio NRMSE: `0.254336343330539`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.21126261379752292`
- Mobilized friction angle NRMSE: `0.20352763614385044`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\variant_runs_refit_mps2\dc_wide_refit\run-031a9bd90493\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- Stress-path NRMSE: `0.382750`
- Loop energy diff: `27.035` %
- tau_peak diff: `20.205` %
- gamma_peak diff: `7.938` %

## Warnings
- None
