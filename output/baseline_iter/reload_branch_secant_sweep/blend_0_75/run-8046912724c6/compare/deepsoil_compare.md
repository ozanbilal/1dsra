# DEEPSOIL Comparison: run-8046912724c6

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.118609` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.033980`
- PGA diff: `3.398` %
- Surface RMSE: `0.389194` m/s^2
- Surface NRMSE: `0.129038`
- Surface correlation: `0.720109`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.233618` m/s^2
- PSA NRMSE: `0.109706`
- PSA max abs diff: `6.245023` m/s^2
- PSA diff at reference peak: `-3.634` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.05006089045067862`
- Max displacement NRMSE: `0.31785153885369993`
- Max strain NRMSE: `0.18906648410412774`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1890664841041277`
- tau_peak NRMSE: `0.009192777565736845`
- Secant G/Gmax NRMSE: `0.0980575400685002`
- Worst gamma layer: `L1`
- Worst tau layer: `L1`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.370457e-05 | 2.925981e-05 | 83.544 | 12.691918 | 12.100000 | 4.892 | 0.736072 | 0.811359 | -9.279 | 0.309868 | 192.536 |
| L2 | 6.000 | 1.415990e-04 | 1.023814e-04 | 38.305 | 36.859843 | 36.100000 | 2.105 | 0.625497 | 0.691808 | -9.585 |  |  |
| L3 | 10.000 | 2.515185e-04 | 1.855473e-04 | 35.555 | 58.670087 | 57.600000 | 1.858 | 0.526208 | 0.609069 | -13.605 |  |  |
| L4 | 14.000 | 3.386869e-04 | 2.599750e-04 | 30.277 | 75.671603 | 74.700000 | 1.301 | 0.474090 | 0.563752 | -15.904 |  |  |
| L5 | 18.000 | 3.616915e-04 | 3.017603e-04 | 19.861 | 85.069753 | 84.900000 | 0.200 | 0.470286 | 0.552007 | -14.804 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_75\run-8046912724c6\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.296862e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.309868`
- sw loop energy: `3.349306e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `192.536` %
- sw tau_peak: `12.269189` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `11.970` %
- gamma_peak diff: `22.742` %

## Warnings
- None
