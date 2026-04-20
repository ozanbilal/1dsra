# DEEPSOIL Comparison: run-6b609cef88a3

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.870327` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.951662`
- PGA diff: `-4.834` %
- Surface RMSE: `0.320598` m/s^2
- Surface NRMSE: `0.106295`
- Surface correlation: `0.780234`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.858819` m/s^2
- PSA NRMSE: `0.076375`
- PSA max abs diff: `4.135079` m/s^2
- PSA diff at reference peak: `-6.934` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.059161127799497615`
- Max displacement NRMSE: `0.34171843207185`
- Max strain NRMSE: `0.15165142472457763`
- Max stress ratio NRMSE: `0.4759742872309797`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.0406004831733638`
- Mobilized friction angle NRMSE: `0.4490428302565436`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1516514247245776`
- tau_peak NRMSE: `0.0406004831733638`
- Secant G/Gmax NRMSE: `0.11744377378266928`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.059474e-05 | 2.925981e-05 | 72.916 | 11.701682 | 12.100000 | -3.292 | 0.719005 | 0.811359 | -11.383 | 0.315357 | 147.261 |
| L2 | 6.000 | 1.396964e-04 | 1.023814e-04 | 36.447 | 34.385208 | 36.100000 | -4.750 | 0.597006 | 0.691808 | -13.703 |  |  |
| L3 | 10.000 | 2.407565e-04 | 1.855473e-04 | 29.755 | 54.763981 | 57.600000 | -4.924 | 0.508914 | 0.609069 | -16.444 |  |  |
| L4 | 14.000 | 3.191269e-04 | 2.599750e-04 | 22.753 | 70.410256 | 74.700000 | -5.743 | 0.466507 | 0.563752 | -17.250 |  |  |
| L5 | 18.000 | 3.473276e-04 | 3.017603e-04 | 15.101 | 79.435174 | 84.900000 | -6.437 | 0.460379 | 0.552007 | -16.599 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\substeps_8\run-6b609cef88a3\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.781510e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.315357`
- sw loop energy: `2.830946e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `147.261` %
- sw tau_peak: `10.424094` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-4.868` %
- gamma_peak diff: `3.556` %

## Warnings
- None
