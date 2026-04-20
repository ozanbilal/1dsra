# DEEPSOIL Comparison: run-3c08c6064cba

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.1460672722560035` m/s^2
- Applied input PGA: `1.0730336361280017` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9900` s
- Overlap samples: `5999`
- PGA (GeoWave): `2.077996` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.688963`
- PGA diff: `-31.104` %
- Surface RMSE: `0.321800` m/s^2
- Surface NRMSE: `0.106693`
- Surface correlation: `0.623405`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.172388` m/s^2
- PSA NRMSE: `0.104261`
- PSA max abs diff: `3.460203` m/s^2
- PSA diff at reference peak: `-29.618` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.22251149253432698`
- Max displacement NRMSE: `0.39833002494907555`
- Max strain NRMSE: `0.1024123670687055`
- Max stress ratio NRMSE: `0.6080689775087351`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.24691390322970877`
- Mobilized friction angle NRMSE: `0.5880304156162922`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.10241236706870548`
- tau_peak NRMSE: `0.24691390322970877`
- Secant G/Gmax NRMSE: `0.27057825565011273`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L3`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.292748e-05 | 2.925981e-05 | 46.711 | 8.345632 | 12.100000 | -31.028 | 0.601704 | 0.811359 | -25.840 | 0.251572 | 17.995 |
| L2 | 6.000 | 1.326890e-04 | 1.023814e-04 | 29.603 | 24.953712 | 36.100000 | -30.876 | 0.451494 | 0.691808 | -34.737 |  |  |
| L3 | 10.000 | 2.371498e-04 | 1.855473e-04 | 27.811 | 38.998643 | 57.600000 | -32.294 | 0.365577 | 0.609069 | -39.978 |  |  |
| L4 | 14.000 | 2.845863e-04 | 2.599750e-04 | 9.467 | 48.673383 | 74.700000 | -34.842 | 0.349538 | 0.563752 | -37.998 |  |  |
| L5 | 18.000 | 2.817256e-04 | 3.017603e-04 | -6.639 | 52.720744 | 84.900000 | -37.903 | 0.367349 | 0.552007 | -33.452 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_scale_reversal\run-3c08c6064cba\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.181368e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.251572`
- sw loop energy: `1.350952e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `17.995` %
- sw tau_peak: `6.821459` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-37.747` %
- gamma_peak diff: `-18.788` %

## Warnings
- None
