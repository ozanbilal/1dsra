# DEEPSOIL Comparison: run-d99bed375e15

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15\compare_layer_parity\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15\compare_layer_parity\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15\compare_layer_parity\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15\compare_layer_parity\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.869336` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.951333`
- PGA diff: `-4.867` %
- Surface RMSE: `0.329448` m/s^2
- Surface NRMSE: `0.109229`
- Surface correlation: `0.765350`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.857496` m/s^2
- PSA NRMSE: `0.076258`
- PSA max abs diff: `4.124678` m/s^2
- PSA diff at reference peak: `-6.978` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `8.170042486602506e-07`
- Input PSA NRMSE: `0.014240944871516564`
- Applied input history NRMSE: `8.170042486602506e-07`
- Applied input PSA NRMSE: `2.3215137809655103e-07`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15\compare_layer_parity\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15\compare_layer_parity\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.059341409558830334`
- Max displacement NRMSE: `0.34195601276858845`
- Max strain NRMSE: `0.15142569717829496`
- Max stress ratio NRMSE: `0.47574975079035536`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.04073632469583078`
- Mobilized friction angle NRMSE: `0.4488217986452064`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.15142569717829493`
- tau_peak NRMSE: `0.04073632469583078`
- Secant G/Gmax NRMSE: `0.11738829720877794`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.065333e-05 | 2.925981e-05 | 73.116 | 11.729455 | 12.100000 | -3.062 | 0.718113 | 0.811359 | -11.493 | 0.316425 | 146.775 |
| L2 | 6.000 | 1.396079e-04 | 1.023814e-04 | 36.361 | 34.404257 | 36.100000 | -4.697 | 0.597597 | 0.691808 | -13.618 |  |  |
| L3 | 10.000 | 2.406626e-04 | 1.855473e-04 | 29.704 | 54.748448 | 57.600000 | -4.951 | 0.509050 | 0.609069 | -16.422 |  |  |
| L4 | 14.000 | 3.189291e-04 | 2.599750e-04 | 22.677 | 70.361034 | 74.700000 | -5.809 | 0.466877 | 0.563752 | -17.184 |  |  |
| L5 | 18.000 | 3.474008e-04 | 3.017603e-04 | 15.125 | 79.437787 | 84.900000 | -6.434 | 0.460365 | 0.552007 | -16.602 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_local_ref\run-d99bed375e15\compare_layer_parity\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.762048e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.316425`
- sw loop energy: `2.825378e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `146.775` %
- sw tau_peak: `10.353734` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-5.511` %
- gamma_peak diff: `2.831` %

## Warnings
- None
