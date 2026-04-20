# DEEPSOIL Comparison: run-4d511c1cd874

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.868772` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.951146`
- PGA diff: `-4.885` %
- Surface RMSE: `0.329387` m/s^2
- Surface NRMSE: `0.109209`
- Surface correlation: `0.765345`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.857141` m/s^2
- PSA NRMSE: `0.076226`
- PSA max abs diff: `4.122133` m/s^2
- PSA diff at reference peak: `-6.983` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.059491937355052996`
- Max displacement NRMSE: `0.3421188312109442`
- Max strain NRMSE: `0.15115796966074813`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.15115796966074813`
- tau_peak NRMSE: `0.0408624144223456`
- Secant G/Gmax NRMSE: `0.1173155108532125`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.064090e-05 | 2.925981e-05 | 73.073 | 11.727196 | 12.100000 | -3.081 | 0.718152 | 0.811359 | -11.488 | 0.316379 | 146.674 |
| L2 | 6.000 | 1.395663e-04 | 1.023814e-04 | 36.320 | 34.397463 | 36.100000 | -4.716 | 0.597652 | 0.691808 | -13.610 |  |  |
| L3 | 10.000 | 2.405790e-04 | 1.855473e-04 | 29.659 | 54.737636 | 57.600000 | -4.969 | 0.509124 | 0.609069 | -16.410 |  |  |
| L4 | 14.000 | 3.188198e-04 | 2.599750e-04 | 22.635 | 70.347873 | 74.700000 | -5.826 | 0.466932 | 0.563752 | -17.174 |  |  |
| L5 | 18.000 | 3.472782e-04 | 3.017603e-04 | 15.084 | 79.422259 | 84.900000 | -6.452 | 0.460438 | 0.552007 | -16.588 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_blend_sweep\blend_0_0\run-4d511c1cd874\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.756982e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.316379`
- sw loop energy: `2.824220e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `146.674` %
- sw tau_peak: `10.337825` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-5.656` %
- gamma_peak diff: `2.643` %

## Warnings
- None
