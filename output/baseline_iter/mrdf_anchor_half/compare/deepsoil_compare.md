# DEEPSOIL Comparison: run-06695f88ceb5

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\run-06695f88ceb5`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.146046870732979` m/s^2
- Applied input PGA: `1.0730234353664896` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9950` s
- Overlap samples: `6000`
- PGA (GeoWave): `2.485909` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.824207`
- PGA diff: `-17.579` %
- Surface RMSE: `0.337975` m/s^2
- Surface NRMSE: `0.112056`
- Surface correlation: `0.667221`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.864251` m/s^2
- PSA NRMSE: `0.076858`
- PSA max abs diff: `2.535374` m/s^2
- PSA diff at reference peak: `-22.547` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `18.105259998153333` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `3.9028023283585766e-05`
- Applied input PSA NRMSE: `0.00012773466201254687`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.12490925729910367`
- Max displacement NRMSE: `0.3625390004365574`
- Max strain NRMSE: `0.12210821804781562`
- Max stress ratio NRMSE: `0.5388003671549769`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.1416039049207977`
- Mobilized friction angle NRMSE: `0.5146183210054196`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.12210821804781559`
- tau_peak NRMSE: `0.1416039049207977`
- Secant G/Gmax NRMSE: `0.18457818093954292`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L3`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.603466e-05 | 2.925981e-05 | 57.331 | 10.184235 | 12.100000 | -15.833 | 0.684752 | 0.811359 | -15.604 | 0.256413 | 72.467 |
| L2 | 6.000 | 1.348366e-04 | 1.023814e-04 | 31.700 | 29.899238 | 36.100000 | -17.177 | 0.538504 | 0.691808 | -22.160 |  |  |
| L3 | 10.000 | 2.385731e-04 | 1.855473e-04 | 28.578 | 47.250259 | 57.600000 | -17.968 | 0.441144 | 0.609069 | -27.571 |  |  |
| L4 | 14.000 | 3.072157e-04 | 2.599750e-04 | 18.171 | 59.983347 | 74.700000 | -19.701 | 0.409390 | 0.563752 | -27.381 |  |  |
| L5 | 18.000 | 3.220212e-04 | 3.017603e-04 | 6.714 | 66.009621 | 84.900000 | -22.250 | 0.408546 | 0.552007 | -25.989 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\mrdf_anchor_half\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.359977e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.256413`
- sw loop energy: `1.974615e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `72.467` %
- sw tau_peak: `8.545310` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-22.014` %
- gamma_peak diff: `-12.138` %

## Warnings
- None
