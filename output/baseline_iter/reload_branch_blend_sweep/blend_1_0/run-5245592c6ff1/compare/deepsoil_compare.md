# DEEPSOIL Comparison: run-5245592c6ff1

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.064774` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.016131`
- PGA diff: `1.613` %
- Surface RMSE: `0.454074` m/s^2
- Surface NRMSE: `0.150549`
- Surface correlation: `0.694599`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.524419` m/s^2
- PSA NRMSE: `0.135568`
- PSA max abs diff: `7.897063` m/s^2
- PSA diff at reference peak: `14.339` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.059793267783169055`
- Max displacement NRMSE: `0.3295456344399345`
- Max strain NRMSE: `0.16906541087495255`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.16906541087495255`
- tau_peak NRMSE: `0.031173003972831077`
- Secant G/Gmax NRMSE: `0.06964188060554397`
- Worst gamma layer: `L1`
- Worst tau layer: `L4`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.140545e-05 | 2.925981e-05 | 75.686 | 12.512059 | 12.100000 | 3.405 | 0.750679 | 0.811359 | -7.479 | 0.364147 | 225.834 |
| L2 | 6.000 | 1.397827e-04 | 1.023814e-04 | 36.531 | 36.769261 | 36.100000 | 1.854 | 0.636671 | 0.691808 | -7.970 |  |  |
| L3 | 10.000 | 2.451599e-04 | 1.855473e-04 | 32.128 | 60.022776 | 57.600000 | 4.206 | 0.550045 | 0.609069 | -9.691 |  |  |
| L4 | 14.000 | 3.274599e-04 | 2.599750e-04 | 25.958 | 78.514662 | 74.700000 | 5.107 | 0.508443 | 0.563752 | -9.811 |  |  |
| L5 | 18.000 | 3.566842e-04 | 3.017603e-04 | 18.201 | 88.639378 | 84.900000 | 4.404 | 0.500057 | 0.552007 | -9.411 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.258051e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.364147`
- sw loop energy: `3.730540e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `225.834` %
- sw tau_peak: `12.454712` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `13.663` %
- gamma_peak diff: `21.297` %

## Warnings
- None
