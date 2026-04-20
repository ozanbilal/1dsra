# DEEPSOIL Comparison: run-06695f88ceb5

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\run-06695f88ceb5`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.802501` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.929174`
- PGA diff: `-7.083` %
- Surface RMSE: `0.327646` m/s^2
- Surface NRMSE: `0.108632`
- Surface correlation: `0.751243`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.873742` m/s^2
- PSA NRMSE: `0.077702`
- PSA max abs diff: `3.832653` m/s^2
- PSA diff at reference peak: `-12.312` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.06326870332158853`
- Max displacement NRMSE: `0.33767954057453997`
- Max strain NRMSE: `0.15519311604751776`
- Max stress ratio NRMSE: `0.4857821855768556`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.05461387494514708`
- Mobilized friction angle NRMSE: `0.45916446668393146`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.15519311604751776`
- tau_peak NRMSE: `0.05461387494514708`
- Secant G/Gmax NRMSE: `0.13152982032497856`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.034856e-05 | 2.925981e-05 | 72.074 | 11.432348 | 12.100000 | -5.518 | 0.705998 | 0.811359 | -12.986 | 0.306017 | 132.558 |
| L2 | 6.000 | 1.371323e-04 | 1.023814e-04 | 33.943 | 33.620703 | 36.100000 | -6.868 | 0.591728 | 0.691808 | -14.466 |  |  |
| L3 | 10.000 | 2.399216e-04 | 1.855473e-04 | 29.305 | 53.535593 | 57.600000 | -7.056 | 0.498832 | 0.609069 | -18.099 |  |  |
| L4 | 14.000 | 3.240139e-04 | 2.599750e-04 | 24.633 | 69.076651 | 74.700000 | -7.528 | 0.451988 | 0.563752 | -19.825 |  |  |
| L5 | 18.000 | 3.492562e-04 | 3.017603e-04 | 15.740 | 77.636279 | 84.900000 | -8.556 | 0.446255 | 0.552007 | -19.158 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_1\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.928809e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.306017`
- sw loop energy: `2.662605e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `132.558` %
- sw tau_peak: `10.217329` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-6.755` %
- gamma_peak diff: `9.040` %

## Warnings
- None
