# DEEPSOIL Comparison: run-126ef349b930

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.870642` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.951766`
- PGA diff: `-4.823` %
- Surface RMSE: `0.320635` m/s^2
- Surface NRMSE: `0.106307`
- Surface correlation: `0.780222`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.859239` m/s^2
- PSA NRMSE: `0.076413`
- PSA max abs diff: `4.138148` m/s^2
- PSA diff at reference peak: `-6.924` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.05900760180751365`
- Max displacement NRMSE: `0.3416394236386133`
- Max strain NRMSE: `0.1517372566974431`
- Max stress ratio NRMSE: `0.4759184113620918`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.04053570235251297`
- Mobilized friction angle NRMSE: `0.4489855690075867`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.15173725669744306`
- tau_peak NRMSE: `0.04053570235251297`
- Secant G/Gmax NRMSE: `0.11711825330079974`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.059692e-05 | 2.925981e-05 | 72.923 | 11.702989 | 12.100000 | -3.281 | 0.719042 | 0.811359 | -11.378 | 0.315036 | 147.454 |
| L2 | 6.000 | 1.397225e-04 | 1.023814e-04 | 36.473 | 34.389145 | 36.100000 | -4.739 | 0.596993 | 0.691808 | -13.705 |  |  |
| L3 | 10.000 | 2.407862e-04 | 1.855473e-04 | 29.771 | 54.772171 | 57.600000 | -4.909 | 0.508908 | 0.609069 | -16.445 |  |  |
| L4 | 14.000 | 3.192100e-04 | 2.599750e-04 | 22.785 | 70.426912 | 74.700000 | -5.720 | 0.467780 | 0.563752 | -17.024 |  |  |
| L5 | 18.000 | 3.472914e-04 | 3.017603e-04 | 15.089 | 79.433884 | 84.900000 | -6.438 | 0.460389 | 0.552007 | -16.597 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_12\run-126ef349b930\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.786931e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.315036`
- sw loop energy: `2.833147e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `147.454` %
- sw tau_peak: `10.441957` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-4.705` %
- gamma_peak diff: `3.758` %

## Warnings
- None
