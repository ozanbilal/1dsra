# DEEPSOIL Comparison: run-ef52a0607914

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914\compare\_deepsoil_bundle\psa_input.csv`
- Reference kind: `primary_gqh`

## Semantics
- Boundary condition: `rigid`
- Motion input type: `outcrop`
- Damping mode: `frequency_independent`
- Input dt used: `0.004999999999999893` s
- Input PGA as loaded: `2.1460672722560035` m/s^2
- Applied input PGA: `1.0730336361280017` m/s^2
- Base motion semantics ok: `True`

## Surface Acceleration
- GeoWave dt: `0.00500000` s
- DEEPSOIL dt: `0.00500000` s
- Overlap duration: `29.9900` s
- Overlap samples: `5999`
- PGA (GeoWave): `2.617288` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.867767`
- PGA diff: `-13.223` %
- Surface RMSE: `0.320665` m/s^2
- Surface NRMSE: `0.106317`
- Surface correlation: `0.764049`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.773171` m/s^2
- PSA NRMSE: `0.068759`
- PSA max abs diff: `2.970026` m/s^2
- PSA diff at reference peak: `-14.701` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.0676710830192488`
- Max displacement NRMSE: `0.30862649674347636`
- Max strain NRMSE: `0.22049347894916008`
- Max stress ratio NRMSE: `0.4879070309804274`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.05539026291634238`
- Mobilized friction angle NRMSE: `0.46059261708066784`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.22049347894916005`
- tau_peak NRMSE: `0.05539026291634238`
- Secant G/Gmax NRMSE: `0.08429554217766436`
- Worst gamma layer: `L4`
- Worst tau layer: `L2`
- Worst secant layer: `L5`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.224043e-05 | 2.925981e-05 | 44.363 | 10.924962 | 12.100000 | -9.711 | 0.793357 | 0.811359 | -2.219 | 0.289878 | 37.374 |
| L2 | 6.000 | 1.001399e-04 | 1.023814e-04 | -2.189 | 29.894041 | 36.100000 | -17.191 | 0.644798 | 0.691808 | -6.795 |  |  |
| L3 | 10.000 | 1.786650e-04 | 1.855473e-04 | -3.709 | 51.233083 | 57.600000 | -11.054 | 0.575510 | 0.609069 | -5.510 |  |  |
| L4 | 14.000 | 3.787420e-04 | 2.599750e-04 | 45.684 | 79.976934 | 74.700000 | 7.064 | 0.470658 | 0.563752 | -16.513 |  |  |
| L5 | 18.000 | 3.901278e-04 | 3.017603e-04 | 29.284 | 86.415089 | 84.900000 | 1.785 | 0.446831 | 0.552007 | -19.053 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 1.100 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 1.100 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 1.100 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 1.100 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 1.100 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `1.1`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `37.37401178563119`
- Stress-path NRMSE: `0.2898775748310826`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.018463706146953265`
- Backbone envelope tau NRMSE: `0.024904698067186436`
- Recorded envelope secant NRMSE: `0.18910016316234482`
- Backbone envelope secant NRMSE: `0.20027397806527092`
- Backbone envelope tau closer: `False`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.701782e-05`
- Recorded envelope tau NRMSE: `0.018463706146953265`
- Backbone envelope tau NRMSE: `0.024904698067186436`
- Recorded envelope secant NRMSE: `0.18910016316234482`
- Backbone envelope secant NRMSE: `0.20027397806527092`
- Backbone tau closer: `False`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\baseline_current\run-ef52a0607914\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.280975e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.289878`
- sw loop energy: `1.572823e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `37.374` %
- sw tau_peak: `9.461567` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-13.653` %
- gamma_peak diff: `-15.079` %

## Warnings
- None
