# DEEPSOIL Comparison: run-2141d2709b7e

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.992939` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.992314`
- PGA diff: `-0.769` %
- Surface RMSE: `0.366558` m/s^2
- Surface NRMSE: `0.121533`
- Surface correlation: `0.737725`

## PSA
- PSA points compared: `80`
- PSA RMSE: `1.080363` m/s^2
- PSA NRMSE: `0.096077`
- PSA max abs diff: `5.476098` m/s^2
- PSA diff at reference peak: `-5.494` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `3.9028023283585766e-05`
- Input PSA NRMSE: `0.014235105834099681`
- Applied input history NRMSE: `0.057151003838187726`
- Applied input PSA NRMSE: `0.1872332908040134`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `pga_g, max_displacement_m, max_strain_pct`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `None`
- PGA-vs-depth NRMSE: `0.043725171983308234`
- Max displacement NRMSE: `0.3264484209954244`
- Max strain NRMSE: `0.17336026509689206`
- Max stress ratio NRMSE: `None`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `None`
- Mobilized friction angle NRMSE: `None`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.1733602650968921`
- tau_peak NRMSE: `0.011394391591485373`
- Secant G/Gmax NRMSE: `0.10491676875351084`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.175832e-05 | 2.925981e-05 | 76.892 | 12.154811 | 12.100000 | 0.453 | 0.728092 | 0.811359 | -10.263 | 0.304788 | 175.099 |
| L2 | 6.000 | 1.417665e-04 | 1.023814e-04 | 38.469 | 35.714894 | 36.100000 | -1.067 | 0.610735 | 0.691808 | -11.719 |  |  |
| L3 | 10.000 | 2.434267e-04 | 1.855473e-04 | 31.194 | 56.970065 | 57.600000 | -1.094 | 0.525703 | 0.609069 | -13.688 |  |  |
| L4 | 14.000 | 3.314362e-04 | 2.599750e-04 | 27.488 | 73.718849 | 74.700000 | -1.313 | 0.472376 | 0.563752 | -16.209 |  |  |
| L5 | 18.000 | 3.580565e-04 | 3.017603e-04 | 18.656 | 83.120008 | 84.900000 | -2.097 | 0.465834 | 0.552007 | -15.611 |  |  |

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_branch_secant_sweep\blend_0_5\run-2141d2709b7e\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.640459e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.304788`
- sw loop energy: `3.149664e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `175.099` %
- sw tau_peak: `10.260472` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-6.362` %
- gamma_peak diff: `-1.696` %

## Warnings
- None
