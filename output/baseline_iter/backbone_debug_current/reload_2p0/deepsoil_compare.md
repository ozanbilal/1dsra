# DEEPSOIL Comparison: run-1f27fd0edc1e

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_2p0\run-1f27fd0edc1e`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\reload_2p0\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\reload_2p0\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\reload_2p0\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\reload_2p0\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `3.051934` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `1.011874`
- PGA diff: `1.187` %
- Surface RMSE: `0.351485` m/s^2
- Surface NRMSE: `0.116535`
- Surface correlation: `0.768493`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.978596` m/s^2
- PSA NRMSE: `0.087027`
- PSA max abs diff: `5.088577` m/s^2
- PSA diff at reference peak: `5.667` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\reload_2p0\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\reload_2p0\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.04776309194627547`
- Max displacement NRMSE: `0.3444725738023106`
- Max strain NRMSE: `0.14696116067398576`
- Max stress ratio NRMSE: `0.44794392583213744`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.004508831504185013`
- Mobilized friction angle NRMSE: `0.4202298150327233`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.14696116067398576`
- tau_peak NRMSE: `0.004508831504185013`
- Secant G/Gmax NRMSE: `0.07934608095386318`
- Worst gamma layer: `L1`
- Worst tau layer: `L1`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 5.169626e-05 | 2.925981e-05 | 76.680 | 12.396841 | 12.100000 | 2.453 | 0.739866 | 0.811359 | -8.811 | 0.308791 | 158.831 |
| L2 | 6.000 | 1.389091e-04 | 1.023814e-04 | 35.678 | 36.522635 | 36.100000 | 1.171 | 0.631064 | 0.691808 | -8.780 |  |  |
| L3 | 10.000 | 2.389330e-04 | 1.855473e-04 | 28.772 | 58.198761 | 57.600000 | 1.040 | 0.542742 | 0.609069 | -10.890 |  |  |
| L4 | 14.000 | 3.160389e-04 | 2.599750e-04 | 21.565 | 74.957010 | 74.700000 | 0.344 | 0.500373 | 0.563752 | -11.242 |  |  |
| L5 | 18.000 | 3.465088e-04 | 3.017603e-04 | 14.829 | 84.696593 | 84.900000 | -0.240 | 0.492801 | 0.552007 | -10.726 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 2.000 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 2.000 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 2.000 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 2.000 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 2.000 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `2.0`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `158.83082147449548`
- Stress-path NRMSE: `0.30879127533033396`
- Backbone loop closer than recorded loop: `True`
- Suspected dominant source: `reload_semantics`
- Rationale: Classical backbone/Masing energy is closer to DEEPSOIL than the recorded solver loop, pointing at reload semantics.

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current\reload_2p0\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.890594e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.308791`
- sw loop energy: `2.963408e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `158.831` %
- sw tau_peak: `11.102471` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `1.322` %
- gamma_peak diff: `7.617` %

## Warnings
- None
