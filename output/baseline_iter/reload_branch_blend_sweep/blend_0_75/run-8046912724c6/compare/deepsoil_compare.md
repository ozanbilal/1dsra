# DEEPSOIL Comparison: run-8046912724c6

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: ``
- Motion input type: ``
- Damping mode: ``
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.146046870732979` m/s^2
- Applied input PGA: `1.0730234353664896` m/s^2
- Base motion semantics ok: `None`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `3.022249` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.002032`
- PGA diff: `0.203` %
- Surface RMSE: `0.415716` m/s^2
- Surface NRMSE: `0.137831`
- Surface correlation: `0.715540`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.293578` m/s^2
- PSA NRMSE: `0.115039`
- PSA max abs diff: `6.781082` m/s^2
- PSA diff at reference peak: `7.992` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.04769685782245845`
- Max displacement NRMSE: `0.32710925058158913`
- Max strain NRMSE: `0.17499174731019232`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.17499174731019232`
- tau_peak NRMSE: `0.01543555831602521`
- Secant G/Gmax NRMSE: `0.09038305400568375`
- Worst gamma layer: `L1`
- Worst tau layer: `L4`
- Worst secant layer: `L5`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.304380e-05 | 2.925981e-05 | 81.286 | 12.338953 | 12.100000 | 1.975 | 0.722587 | 0.811359 | -10.941 | 0.332339 | 198.560 |
| L2 | 6.000 | 1.420023e-04 | 1.023814e-04 | 38.699 | 36.422434 | 36.100000 | 0.893 | 0.622537 | 0.691808 | -10.013 |  |  |
| L3 | 10.000 | 2.461367e-04 | 1.855473e-04 | 32.654 | 58.914239 | 57.600000 | 2.282 | 0.537575 | 0.609069 | -11.738 |  |  |
| L4 | 14.000 | 3.276844e-04 | 2.599750e-04 | 26.045 | 76.683824 | 74.700000 | 2.656 | 0.495844 | 0.563752 | -12.046 |  |  |
| L5 | 18.000 | 3.613505e-04 | 3.017603e-04 | 19.748 | 86.562206 | 84.900000 | 1.958 | 0.485022 | 0.552007 | -12.135 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.827243e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.332339`
- sw loop energy: `3.418271e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `198.560` %
- sw tau_peak: `10.692975` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-2.415` %
- gamma_peak diff: `5.258` %

## Warnings
- None
