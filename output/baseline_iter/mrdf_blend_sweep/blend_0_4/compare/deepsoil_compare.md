# DEEPSOIL Comparison: run-06695f88ceb5

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\run-06695f88ceb5`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.590666` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.858940`
- PGA diff: `-14.106` %
- Surface RMSE: `0.335719` m/s^2
- Surface NRMSE: `0.111308`
- Surface correlation: `0.689457`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.866691` m/s^2
- PSA NRMSE: `0.077075`
- PSA max abs diff: `2.533487` m/s^2
- PSA diff at reference peak: `-20.141` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `18.105259998153333` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.10533035899889767`
- Max displacement NRMSE: `0.3537097044086901`
- Max strain NRMSE: `0.13278720784753986`
- Max stress ratio NRMSE: `0.525583764590563`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.11742284059476095`
- Mobilized friction angle NRMSE: `0.5006584978712821`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.13278720784753986`
- tau_peak NRMSE: `0.11742284059476095`
- Secant G/Gmax NRMSE: `0.16867898565991687`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.623812e-05 | 2.925981e-05 | 58.026 | 10.545240 | 12.100000 | -12.849 | 0.702087 | 0.811359 | -13.468 | 0.259623 | 82.731 |
| L2 | 6.000 | 1.316565e-04 | 1.023814e-04 | 28.594 | 30.234206 | 36.100000 | -16.249 | 0.553676 | 0.691808 | -19.967 |  |  |
| L3 | 10.000 | 2.415595e-04 | 1.855473e-04 | 30.188 | 49.164616 | 57.600000 | -14.645 | 0.454554 | 0.609069 | -25.369 |  |  |
| L4 | 14.000 | 3.148077e-04 | 2.599750e-04 | 21.092 | 62.582099 | 74.700000 | -16.222 | 0.418570 | 0.563752 | -25.753 |  |  |
| L5 | 18.000 | 3.289394e-04 | 3.017603e-04 | 9.007 | 69.340417 | 84.900000 | -18.327 | 0.419045 | 0.552007 | -24.087 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_4\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.393187e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.259623`
- sw loop energy: `2.092128e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `82.731` %
- sw tau_peak: `8.908395` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-18.701` %
- gamma_peak diff: `-10.902` %

## Warnings
- None
