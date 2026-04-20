# DEEPSOIL Comparison: run-35ad543c456f

## Inputs
- GeoWave run: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\reload_1p0\run-35ad543c456f`
- DEEPSOIL workbook: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\tests\Results_profile_0_motion_Kocaeli.xlsx`
- DEEPSOIL surface CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p0\_deepsoil_bundle\surface.csv`
- DEEPSOIL input motion CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p0\_deepsoil_bundle\input_motion.csv`
- DEEPSOIL PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p0\_deepsoil_bundle\psa_surface.csv`
- DEEPSOIL input PSA source: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p0\_deepsoil_bundle\psa_input.csv`
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
- PGA (GeoWave): `2.461063` m/s^2
- PGA (DEEPSOIL): `3.016121` m/s^2
- PGA ratio: `0.815970`
- PGA diff: `-18.403` %
- Surface RMSE: `0.272194` m/s^2
- Surface NRMSE: `0.090247`
- Surface correlation: `0.791509`

## PSA
- PSA points compared: `80`
- PSA RMSE: `0.830925` m/s^2
- PSA NRMSE: `0.073895`
- PSA max abs diff: `2.564214` m/s^2
- PSA diff at reference peak: `-22.804` %
- Reference peak period: `0.1694` s
- Surface PSA peak-period diff: `11.732494130275942` %

## Input Motion
- Input history NRMSE: `0.021913421177076252`
- Input PSA NRMSE: `0.014235384034179578`
- Applied input history NRMSE: `0.021913421177076252`
- Applied input PSA NRMSE: `0.00012250314068310337`

## Profile
- Profile CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p0\_deepsoil_bundle\profile.csv`
- Mobilized strength CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p0\_deepsoil_bundle\mobilized_strength.csv`
- Depth points compared: `5`
- Compared metrics: `effective_stress_kpa, pga_g, max_displacement_m, max_strain_pct, max_stress_ratio, mobilized_strength_kpa, mobilized_friction_angle_deg`
- gamma_max NRMSE: `None`
- ru_max NRMSE: `None`
- sigma'_v,min NRMSE: `None`
- Effective stress NRMSE: `0.614482167294058`
- PGA-vs-depth NRMSE: `0.1315896580127307`
- Max displacement NRMSE: `0.3512668306260109`
- Max strain NRMSE: `0.13487726777347173`
- Max stress ratio NRMSE: `0.5397299394253315`
- Vs NRMSE: `None`
- Implied strength NRMSE: `None`
- Normalized implied strength NRMSE: `None`
- Implied friction angle NRMSE: `None`
- Mobilized strength NRMSE: `0.137557471220769`
- Mobilized friction angle NRMSE: `0.5154784964820098`

## Layer-by-Layer Parity
- Layer rows compared: `5`
- gamma_max NRMSE: `0.13487726777347173`
- tau_peak NRMSE: `0.137557471220769`
- Secant G/Gmax NRMSE: `0.1853372162902245`
- Worst gamma layer: `L1`
- Worst tau layer: `L5`
- Worst secant layer: `L4`

| Layer | z_mid (m) | gamma_max sw | gamma_max ref | gamma diff % | tau_peak sw (kPa) | tau_peak ref (kPa) | tau diff % | Gsec/Gmax sw | Gsec/Gmax ref | secant diff % | stress-path NRMSE | loop energy diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 4.617673e-05 | 2.925981e-05 | 57.816 | 10.056259 | 12.100000 | -16.890 | 0.680644 | 0.811359 | -16.111 | 0.269860 | 114.880 |
| L2 | 6.000 | 1.341301e-04 | 1.023814e-04 | 31.010 | 29.760608 | 36.100000 | -17.561 | 0.544584 | 0.691808 | -21.281 |  |  |
| L3 | 10.000 | 2.345522e-04 | 1.855473e-04 | 26.411 | 46.906532 | 57.600000 | -18.565 | 0.450696 | 0.609069 | -26.003 |  |  |
| L4 | 14.000 | 3.177781e-04 | 2.599750e-04 | 22.234 | 60.206897 | 74.700000 | -19.402 | 0.403064 | 0.563752 | -28.503 |  |  |
| L5 | 18.000 | 3.370570e-04 | 3.017603e-04 | 11.697 | 67.202914 | 84.900000 | -20.845 | 0.399040 | 0.552007 | -27.711 |  |  |

## GQ/H Backbone Diagnostic
- Layer rows compared: `5`
- Backbone tau_peak NRMSE: `0.00032434026175287247`
- Backbone secant G/Gmax NRMSE: `0.001194232004210919`
- Backbone Masing loop energy NRMSE: `1.4303591295408211`
- Worst backbone tau layer: `L1`
- Worst backbone secant layer: `L1`

| Layer | z_mid (m) | reload | ref gamma | backbone tau (kPa) | ref tau (kPa) | tau diff % | backbone secant | ref secant | secant diff % | tangent/Gmax | Masing loop diff % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| L1 | 2.000 | 1.000 | 2.925981e-05 | 12.129744 | 12.100000 | 0.246 | 0.813353 | 0.811359 | 0.246 | 0.682273 | 143.036 |
| L2 | 6.000 | 1.000 | 1.023814e-04 | 36.058119 | 36.100000 | -0.116 | 0.691005 | 0.691808 | -0.116 | 0.497334 |  |
| L3 | 10.000 | 1.000 | 1.855473e-04 | 57.585063 | 57.600000 | -0.026 | 0.608911 | 0.609069 | -0.026 | 0.399227 |  |
| L4 | 14.000 | 1.000 | 2.599750e-04 | 74.723612 | 74.700000 | 0.032 | 0.563930 | 0.563752 | 0.032 | 0.351819 |  |
| L5 | 18.000 | 1.000 | 3.017603e-04 | 84.919287 | 84.900000 | 0.023 | 0.552132 | 0.552007 | 0.023 | 0.339831 |  |

## Reload Semantics Diagnostic
- Layer index: `L1`
- reload_factor: `1.0`
- Backbone tau diff %: `0.24581432018291677`
- Backbone secant diff %: `0.2458135182164175`
- Backbone Masing loop diff %: `143.0359129540821`
- Recorded loop diff %: `114.87962192069385`
- Stress-path NRMSE: `0.26986019501478636`
- Backbone loop closer than recorded loop: `False`
- Recorded envelope tau NRMSE: `0.037188901650494884`
- Backbone envelope tau NRMSE: `0.021865463395652714`
- Recorded envelope secant NRMSE: `3.859675058365204`
- Backbone envelope secant NRMSE: `0.1999802330765689`
- Backbone envelope tau closer: `True`
- Backbone envelope secant closer: `True`
- Suspected dominant source: `inconclusive`
- Rationale: Backbone and cyclic metrics are not separated enough to isolate a single dominant source.

## Hysteresis Envelope Diagnostic
- Layer index: `L1`
- Points compared: `48`
- Gamma range: `1.009656e-12` to `2.898782e-05`
- Recorded envelope tau NRMSE: `0.037188901650494884`
- Backbone envelope tau NRMSE: `0.021865463395652714`
- Recorded envelope secant NRMSE: `3.859675058365204`
- Backbone envelope secant NRMSE: `0.1999802330765689`
- Backbone tau closer: `True`
- Backbone secant closer: `True`

## Hysteresis
- Hysteresis CSV: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\baseline_iter\backbone_debug_current_reload\reload_1p0\_deepsoil_bundle\hysteresis_layer1.csv`
- Layer index: `0`
- Resampled points: `240`
- sw gamma_peak: `2.288887e-05`
- ref gamma_peak: `2.686004e-05`
- Stress-path NRMSE: `0.269860`
- sw loop energy: `2.460201e-04`
- ref loop energy: `1.144921e-04`
- Loop energy diff: `114.880` %
- sw tau_peak: `7.614401` kPa
- ref tau_peak: `10.957557` kPa
- tau_peak diff: `-30.510` %
- gamma_peak diff: `-14.785` %

## Warnings
- None
