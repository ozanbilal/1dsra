# DEEPSOIL Comparison: run-3c08c6064cba

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.869452` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.951372`
- PGA diff: `-4.863` %
- Surface RMSE: `0.320774` m/s^2
- Surface NRMSE: `0.106353`
- Surface correlation: `0.779988`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.858464` m/s^2
- PSA NRMSE: `0.076344`
- PSA max abs diff: `4.129701` m/s^2
- PSA diff at reference peak: `-6.995` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.05912735337135454`
- Max displacement NRMSE: `0.3417410494524027`
- Max strain NRMSE: `0.15172753113867773`
- Max stress ratio NRMSE: `0.4755139148863543`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.040584146263807595`
- Mobilized friction angle NRMSE: `0.44858279994566974`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.15172753113867765`
- tau_peak NRMSE: `0.040584146263807595`
- Secant G/Gmax NRMSE: `0.11741451619398412`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.066813e-05 | 2.925981e-05 | 73.166 | 11.750472 | 12.100000 | -2.889 | 0.718240 | 0.811359 | -11.477 | 0.315297 | 147.726 |
| L2 | 6.000 | 1.396146e-04 | 1.023814e-04 | 36.367 | 34.406259 | 36.100000 | -4.692 | 0.597562 | 0.691808 | -13.623 |  |  |
| L3 | 10.000 | 2.406960e-04 | 1.855473e-04 | 29.722 | 54.752296 | 57.600000 | -4.944 | 0.509032 | 0.609069 | -16.425 |  |  |
| L4 | 14.000 | 3.190406e-04 | 2.599750e-04 | 22.720 | 70.371694 | 74.700000 | -5.794 | 0.466831 | 0.563752 | -17.192 |  |  |
| L5 | 18.000 | 3.476595e-04 | 3.017603e-04 | 15.210 | 79.466215 | 84.900000 | -6.400 | 0.460231 | 0.552007 | -16.626 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\newmark_iterative\run-3c08c6064cba\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.642596e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.315297`
- sw loop energy: `2.836265e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `147.726` %
- sw tau_peak: `9.980507` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-8.917` %
- gamma_peak diff: `-1.616` %

## Warnings
- None
