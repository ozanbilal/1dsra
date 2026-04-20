# DEEPSOIL Comparison: run-39d836a96524

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.416028` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.132590`
- PGA diff: `13.259` %
- Surface RMSE: `0.455763` m/s^2
- Surface NRMSE: `0.151109`
- Surface correlation: `0.694609`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.715102` m/s^2
- PSA NRMSE: `0.152525`
- PSA max abs diff: `8.631316` m/s^2
- PSA diff at reference peak: `10.903` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.09514511721170325`
- Max displacement NRMSE: `0.31369218454680164`
- Max strain NRMSE: `0.1989039433664118`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1989039433664118`
- tau_peak NRMSE: `0.07327991260195686`
- Secant G/Gmax NRMSE: `0.058411992978147455`
- Worst gamma layer: `L1`
- Worst tau layer: `L1`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.649616e-05 | 2.925981e-05 | 93.085 | 13.829159 | 12.100000 | 14.291 | 0.755743 | 0.811359 | -6.855 | 0.340127 | 215.463 |
| L2 | 6.000 | 1.478783e-04 | 1.023814e-04 | 44.439 | 40.416033 | 36.100000 | 11.956 | 0.652716 | 0.691808 | -5.651 |  |  |
| L3 | 10.000 | 2.563685e-04 | 1.855473e-04 | 38.169 | 63.901273 | 57.600000 | 10.940 | 0.558353 | 0.609069 | -8.327 |  |  |
| L4 | 14.000 | 3.405313e-04 | 2.599750e-04 | 30.986 | 82.701795 | 74.700000 | 10.712 | 0.513112 | 0.563752 | -8.983 |  |  |
| L5 | 18.000 | 3.625553e-04 | 3.017603e-04 | 20.147 | 93.157131 | 84.900000 | 9.726 | 0.513633 | 0.552007 | -6.952 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_semantics_probe\rf2_secant\run-39d836a96524\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.876961e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.340127`
- sw loop energy: `3.611802e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `215.463` %
- sw tau_peak: `11.427020` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `4.284` %
- gamma_peak diff: `7.109` %

## Warnings
- None
