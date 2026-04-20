# DEEPSOIL Comparison: run-a1429e04cb37

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.920994` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.968461`
- PGA diff: `-3.154` %
- Surface RMSE: `0.354165` m/s^2
- Surface NRMSE: `0.117424`
- Surface correlation: `0.750306`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.961106` m/s^2
- PSA NRMSE: `0.085472`
- PSA max abs diff: `4.922399` m/s^2
- PSA diff at reference peak: `-3.004` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.05148512998985641`
- Max displacement NRMSE: `0.3332512312001449`
- Max strain NRMSE: `0.16435182637643359`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.16435182637643356`
- tau_peak NRMSE: `0.02133447253437157`
- Secant G/Gmax NRMSE: `0.11173078493922908`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.202639e-05 | 2.925981e-05 | 77.808 | 11.919256 | 12.100000 | -1.494 | 0.713156 | 0.811359 | -12.103 | 0.305521 | 161.853 |
| L2 | 6.000 | 1.404478e-04 | 1.023814e-04 | 37.181 | 35.179757 | 36.100000 | -2.549 | 0.605885 | 0.691808 | -12.420 |  |  |
| L3 | 10.000 | 2.439302e-04 | 1.855473e-04 | 31.465 | 56.269769 | 57.600000 | -2.309 | 0.516732 | 0.609069 | -15.160 |  |  |
| L4 | 14.000 | 3.253579e-04 | 2.599750e-04 | 25.150 | 72.710398 | 74.700000 | -2.663 | 0.473490 | 0.563752 | -16.011 |  |  |
| L5 | 18.000 | 3.532131e-04 | 3.017603e-04 | 17.051 | 81.770075 | 84.900000 | -3.687 | 0.466039 | 0.552007 | -15.574 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_25\run-a1429e04cb37\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `3.160081e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.305521`
- sw loop energy: `2.998009e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `161.853` %
- sw tau_peak: `11.551951` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `5.425` %
- gamma_peak diff: `17.650` %

## Warnings
- None
