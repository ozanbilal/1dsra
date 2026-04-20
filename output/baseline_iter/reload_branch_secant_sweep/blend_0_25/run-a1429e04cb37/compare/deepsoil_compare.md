# DEEPSOIL Comparison: run-a1429e04cb37

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.912067` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.965501`
- PGA diff: `-3.450` %
- Surface RMSE: `0.346611` m/s^2
- Surface NRMSE: `0.114920`
- Surface correlation: `0.752665`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.955088` m/s^2
- PSA NRMSE: `0.084937`
- PSA max abs diff: `4.771292` m/s^2
- PSA diff at reference peak: `-6.549` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.050951468490666466`
- Max displacement NRMSE: `0.3346297935011001`
- Max strain NRMSE: `0.16105181896035098`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.16105181896035095`
- tau_peak NRMSE: `0.02677950445463521`
- Secant G/Gmax NRMSE: `0.11312487758898178`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L5`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.153755e-05 | 2.925981e-05 | 76.138 | 11.828019 | 12.100000 | -2.248 | 0.714453 | 0.811359 | -11.944 | 0.304157 | 161.290 |
| L2 | 6.000 | 1.396948e-04 | 1.023814e-04 | 36.446 | 34.911170 | 36.100000 | -3.293 | 0.604290 | 0.691808 | -12.651 |  |  |
| L3 | 10.000 | 2.416674e-04 | 1.855473e-04 | 30.246 | 55.780641 | 57.600000 | -3.159 | 0.515957 | 0.609069 | -15.288 |  |  |
| L4 | 14.000 | 3.240676e-04 | 2.599750e-04 | 24.653 | 71.963503 | 74.700000 | -3.663 | 0.472305 | 0.563752 | -16.221 |  |  |
| L5 | 18.000 | 3.533685e-04 | 3.017603e-04 | 17.102 | 81.217602 | 84.900000 | -4.337 | 0.462342 | 0.552007 | -16.244 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.751832e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.304157`
- sw loop energy: `2.991562e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `161.290` %
- sw tau_peak: `10.291403` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-6.079` %
- gamma_peak diff: `2.451` %

## Warnings
- None
