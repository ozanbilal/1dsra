# DEEPSOIL Comparison: run-3c08c6064cba

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.658987` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.881592`
- PGA diff: `-11.841` %
- Surface RMSE: `0.290406` m/s^2
- Surface NRMSE: `0.096285`
- Surface correlation: `0.788911`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.803846` m/s^2
- PSA NRMSE: `0.071487`
- PSA max abs diff: `2.924722` m/s^2
- PSA diff at reference peak: `-16.174` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.09467467898411558`
- Max displacement NRMSE: `0.3439886374836812`
- Max strain NRMSE: `0.14896306076654486`
- Max stress ratio NRMSE: `0.5097957831038771`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.09187463761677812`
- Mobilized friction angle NRMSE: `0.4841342016408166`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1489630607665448`
- tau_peak NRMSE: `0.09187463761677812`
- Secant G/Gmax NRMSE: `0.16390271934571052`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.056360e-05 | 2.925981e-05 | 72.809 | 10.834865 | 12.100000 | -10.456 | 0.671253 | 0.811359 | -17.268 | 0.293283 | 159.090 |
| L2 | 6.000 | 1.396587e-04 | 1.023814e-04 | 36.410 | 31.876425 | 36.100000 | -11.700 | 0.557183 | 0.691808 | -19.460 |  |  |
| L3 | 10.000 | 2.387238e-04 | 1.855473e-04 | 28.659 | 50.649641 | 57.600000 | -12.067 | 0.476892 | 0.609069 | -21.702 |  |  |
| L4 | 14.000 | 3.201084e-04 | 2.599750e-04 | 23.130 | 64.994420 | 74.700000 | -12.993 | 0.432748 | 0.563752 | -23.238 |  |  |
| L5 | 18.000 | 3.443727e-04 | 3.017603e-04 | 14.121 | 72.972414 | 84.900000 | -14.049 | 0.425369 | 0.552007 | -22.941 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_uiuc_inverted\run-3c08c6064cba\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.448739e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.293283`
- sw loop energy: `2.966373e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `159.090` %
- sw tau_peak: `8.541539` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-22.049` %
- gamma_peak diff: `-8.833` %

## Warnings
- None
