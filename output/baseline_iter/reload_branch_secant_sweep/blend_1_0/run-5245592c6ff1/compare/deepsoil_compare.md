# DEEPSOIL Comparison: run-5245592c6ff1

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.262692` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.081751`
- PGA diff: `8.175` %
- Surface RMSE: `0.414232` m/s^2
- Surface NRMSE: `0.137339`
- Surface correlation: `0.700101`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.421329` m/s^2
- PSA NRMSE: `0.126400`
- PSA max abs diff: `7.107830` m/s^2
- PSA diff at reference peak: `-0.821` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.06755483372692458`
- Max displacement NRMSE: `0.30911549476227596`
- Max strain NRMSE: `0.207668850485193`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.20766885048519304`
- tau_peak NRMSE: `0.02863956846660597`
- Secant G/Gmax NRMSE: `0.09926854491987024`
- Worst gamma layer: `L1`
- Worst tau layer: `L1`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.620180e-05 | 2.925981e-05 | 92.079 | 13.156078 | 12.100000 | 8.728 | 0.729444 | 0.811359 | -10.096 | 0.319745 | 207.451 |
| L2 | 6.000 | 1.485566e-04 | 1.023814e-04 | 45.101 | 38.377766 | 36.100000 | 6.310 | 0.623420 | 0.691808 | -9.885 |  |  |
| L3 | 10.000 | 2.601804e-04 | 1.855473e-04 | 40.223 | 60.657775 | 57.600000 | 5.309 | 0.521971 | 0.609069 | -14.300 |  |  |
| L4 | 14.000 | 3.458206e-04 | 2.599750e-04 | 33.021 | 77.750649 | 74.700000 | 4.084 | 0.475802 | 0.563752 | -15.601 |  |  |
| L5 | 18.000 | 3.637093e-04 | 3.017603e-04 | 20.529 | 87.044990 | 84.900000 | 2.526 | 0.476329 | 0.552007 | -13.710 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_1_0\run-5245592c6ff1\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.035434e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.319745`
- sw loop energy: `3.520070e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `207.451` %
- sw tau_peak: `10.777000` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-1.648` %
- gamma_peak diff: `13.009` %

## Warnings
- None
