# DEEPSOIL Comparison: run-d4e79812323b

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b\compare\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b\compare\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b\compare\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b\compare\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.774101` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.919758`
- PGA diff: `-8.024` %
- Surface RMSE: `0.326079` m/s^2
- Surface NRMSE: `0.108112`
- Surface correlation: `0.763306`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.828209` m/s^2
- PSA NRMSE: `0.073653`
- PSA max abs diff: `3.713293` m/s^2
- PSA diff at reference peak: `-13.621` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b\compare\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b\compare\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.04240753418422675`
- Max displacement NRMSE: `0.317139410509376`
- Max strain NRMSE: `0.18686482659795445`
- Max stress ratio NRMSE: `0.49694017695635506`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.08727582283439976`
- Mobilized friction angle NRMSE: `0.47120876635720965`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.18686482659795445`
- tau_peak NRMSE: `0.08727582283439976`
- Secant G/Gmax NRMSE: `0.1380273005857874`
- Worst gamma layer: `L1`
- Worst tau layer: `L3`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.113081e-05 | 2.925981e-05 | 74.748 | 12.203097 | 12.100000 | 0.852 | 0.764332 | 0.811359 | -5.796 | 0.293911 | 63.724 |
| L2 | 6.000 | 1.306492e-04 | 1.023814e-04 | 27.610 | 32.863477 | 36.100000 | -8.965 | 0.661188 | 0.691808 | -4.426 |  |  |
| L3 | 10.000 | 1.701497e-04 | 1.855473e-04 | -8.298 | 47.898597 | 57.600000 | -16.843 | 0.530978 | 0.609069 | -12.821 |  |  |
| L4 | 14.000 | 3.468435e-04 | 2.599750e-04 | 33.414 | 66.192988 | 74.700000 | -11.388 | 0.397090 | 0.563752 | -29.563 |  |  |
| L5 | 18.000 | 3.844501e-04 | 3.017603e-04 | 27.402 | 75.023393 | 84.900000 | -11.633 | 0.391742 | 0.552007 | -29.033 |  |  |

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
- Recorded loop diff %: `63.72402431566899`
- Stress-path NRMSE: `0.29391058303242756`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.0239250469517946`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.1994246326629194`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `False`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.925981e-05`
- Recorded envelope tau NRMSE: `0.0239250469517946`
- Backbone envelope tau NRMSE: `0.021648510501363877`
- Recorded envelope secant NRMSE: `0.1994246326629194`
- Backbone envelope secant NRMSE: `0.1999409446815331`
- Backbone tau closer: `True`
- Backbone secant closer: `False`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\tangent_floor_sweep\tan_020_e10\run-d4e79812323b\compare\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.620947e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.293911`
- sw loop energy: `1.874510e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `63.724` %
- sw tau_peak: `9.777771` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-10.767` %
- gamma_peak diff: `-2.422` %

## Warnings
- None
