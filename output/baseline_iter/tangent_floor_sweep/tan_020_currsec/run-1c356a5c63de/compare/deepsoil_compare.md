# DEEPSOIL Comparison: run-1c356a5c63de

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.602799` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.862963`
- PGA diff: `-13.704` %
- Surface RMSE: `0.324480` m/s^2
- Surface NRMSE: `0.107582`
- Surface correlation: `0.761269`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.784412` m/s^2
- PSA NRMSE: `0.069758`
- PSA max abs diff: `3.315396` m/s^2
- PSA diff at reference peak: `-9.043` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.08308936458123345`
- Max displacement NRMSE: `0.339940432271822`
- Max strain NRMSE: `0.14821958198039814`
- Max stress ratio NRMSE: `0.4995459217284125`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.07824502691189386`
- Mobilized friction angle NRMSE: `0.4733127837550921`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.14821958198039809`
- tau_peak NRMSE: `0.07824502691189386`
- Secant G/Gmax NRMSE: `0.12169143210908094`
- Worst gamma layer: `L1`
- Worst tau layer: `L4`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.044016e-05 | 2.925981e-05 | 38.211 | 10.544007 | 12.100000 | -12.859 | 0.799225 | 0.811359 | -1.496 | 0.308255 | 62.829 |
| L2 | 6.000 | 1.355923e-04 | 1.023814e-04 | 32.438 | 33.625157 | 36.100000 | -6.856 | 0.652758 | 0.691808 | -5.645 |  |  |
| L3 | 10.000 | 2.405625e-04 | 1.855473e-04 | 29.650 | 53.688707 | 57.600000 | -6.790 | 0.488673 | 0.609069 | -19.767 |  |  |
| L4 | 14.000 | 3.235139e-04 | 2.599750e-04 | 24.440 | 60.822344 | 74.700000 | -18.578 | 0.400054 | 0.563752 | -29.037 |  |  |
| L5 | 18.000 | 3.431195e-04 | 3.017603e-04 | 13.706 | 82.847220 | 84.900000 | -2.418 | 0.475986 | 0.552007 | -13.772 |  |  |

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
- Recorded loop diff %: `62.828946394996166`
- Stress-path NRMSE: `0.30825484835422917`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.023288603422098555`
- Backbone envelope tau NRMSE: `0.025391780017449458`
- Recorded envelope secant NRMSE: `0.1992055010298097`
- Backbone envelope secant NRMSE: `0.2004588867703739`
- Backbone envelope tau closer: `False`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.588427e-05`
- Recorded envelope tau NRMSE: `0.023288603422098555`
- Backbone envelope tau NRMSE: `0.025391780017449458`
- Recorded envelope secant NRMSE: `0.1992055010298097`
- Backbone envelope secant NRMSE: `0.2004588867703739`
- Backbone tau closer: `False`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_currsec\run-1c356a5c63de\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.293130e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.308255`
- sw loop energy: `1.864262e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `62.829` %
- sw tau_peak: `9.081636` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-17.120` %
- gamma_peak diff: `-14.627` %

## Warnings
- None
