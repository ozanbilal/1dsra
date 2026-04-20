# DEEPSOIL Comparison: run-06695f88ceb5

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\run-06695f88ceb5`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.678967` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.888216`
- PGA diff: `-11.178` %
- Surface RMSE: `0.331919` m/s^2
- Surface NRMSE: `0.110048`
- Surface correlation: `0.711987`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.870866` m/s^2
- PSA NRMSE: `0.077447`
- PSA max abs diff: `2.939997` m/s^2
- PSA diff at reference peak: `-17.719` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.09006105017551036`
- Max displacement NRMSE: `0.3428714289703721`
- Max strain NRMSE: `0.14730135942565095`
- Max stress ratio NRMSE: `0.5084976625010876`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.091944199742123`
- Mobilized friction angle NRMSE: `0.4828268233524141`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.14730135942565095`
- tau_peak NRMSE: `0.091944199742123`
- Secant G/Gmax NRMSE: `0.15574676819044275`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.825545e-05 | 2.925981e-05 | 64.921 | 10.864523 | 12.100000 | -10.211 | 0.698496 | 0.811359 | -13.910 | 0.271504 | 97.480 |
| L2 | 6.000 | 1.337184e-04 | 1.023814e-04 | 30.608 | 32.051700 | 36.100000 | -11.214 | 0.575379 | 0.691808 | -16.830 |  |  |
| L3 | 10.000 | 2.427083e-04 | 1.855473e-04 | 30.807 | 50.991591 | 57.600000 | -11.473 | 0.470188 | 0.609069 | -22.802 |  |  |
| L4 | 14.000 | 3.216456e-04 | 2.599750e-04 | 23.722 | 65.256437 | 74.700000 | -12.642 | 0.428510 | 0.563752 | -23.990 |  |  |
| L5 | 18.000 | 3.400407e-04 | 3.017603e-04 | 12.686 | 72.494115 | 84.900000 | -14.612 | 0.425633 | 0.552007 | -22.894 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_blend_sweep\blend_0_3\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.420937e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.271504`
- sw loop energy: `2.260985e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `97.480` %
- sw tau_peak: `8.975677` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-18.087` %
- gamma_peak diff: `-9.868` %

## Warnings
- None
