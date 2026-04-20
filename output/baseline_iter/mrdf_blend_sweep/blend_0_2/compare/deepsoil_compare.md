# DEEPSOIL Comparison: run-06695f88ceb5

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\run-06695f88ceb5`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.743024` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.909454`
- PGA diff: `-9.055` %
- Surface RMSE: `0.328456` m/s^2
- Surface NRMSE: `0.108900`
- Surface correlation: `0.733338`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.873632` m/s^2
- PSA NRMSE: `0.077693`
- PSA max abs diff: `3.412137` m/s^2
- PSA diff at reference peak: `-15.368` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.07629870429440878`
- Max displacement NRMSE: `0.33722694974348494`
- Max strain NRMSE: `0.1569534136301349`
- Max stress ratio NRMSE: `0.4959561090123237`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.07112154070549204`
- Mobilized friction angle NRMSE: `0.46973870618161273`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1569534136301349`
- tau_peak NRMSE: `0.07112154070549204`
- Secant G/Gmax NRMSE: `0.1432758370225994`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.887718e-05 | 2.925981e-05 | 67.045 | 11.177724 | 12.100000 | -7.622 | 0.708388 | 0.811359 | -12.691 | 0.286246 | 118.104 |
| L2 | 6.000 | 1.369821e-04 | 1.023814e-04 | 33.796 | 32.898163 | 36.100000 | -8.869 | 0.579995 | 0.691808 | -16.162 |  |  |
| L3 | 10.000 | 2.429282e-04 | 1.855473e-04 | 30.925 | 52.425602 | 57.600000 | -8.983 | 0.486491 | 0.609069 | -20.125 |  |  |
| L4 | 14.000 | 3.243461e-04 | 2.599750e-04 | 24.760 | 67.313302 | 74.700000 | -9.888 | 0.439458 | 0.563752 | -22.048 |  |  |
| L5 | 18.000 | 3.486398e-04 | 3.017603e-04 | 15.535 | 75.420528 | 84.900000 | -11.165 | 0.433733 | 0.552007 | -21.426 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_2\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.440809e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.286246`
- sw loop energy: `2.497120e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `118.104` %
- sw tau_peak: `9.184806` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-16.178` %
- gamma_peak diff: `-9.129` %

## Warnings
- None
