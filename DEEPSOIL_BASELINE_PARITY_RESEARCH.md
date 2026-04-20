# DeepSoil Baseline Parity Research

## Summary

This is the living parity dossier for the current DeepSoil baseline campaign.

It does not replace `IMPLEMENTATION_STATUS.md`. It complements it by recording:

- the strongest current diagnosis
- what has already been falsified
- the active experiment families
- the next research sequence

Use this file together with:

- `IMPLEMENTATION_STATUS.md`
- `PARITY_MEMORY.md`
- `parity_experiment_index.json`

## Active Campaign Split

There are currently two different parity problems.

1. Canonical rigid/outcrop baseline parity
   - still points to constitutive multi-layer tangent-history closure
   - still measured against `tests/Results_profile_0_motion_Kocaeli.xlsx`
2. Elastic-vs-rigid boundary verification
   - now runs boundary first
   - uses the DeepSoil semantics pair `elastic_halfspace + outcrop` vs `rigid + within`
   - uses `deepsoilout.db3` from the supplied DeepSoil batch output as the primary truth surface

Do not mix these two acceptance problems.

## Canonical Target

Canonical case:

- `examples/native/deepsoil_gqh_5layer_baseline.yml`

Primary workbook:

- `tests/Results_profile_0_motion_Kocaeli.xlsx`

Secondary workbook:

- `tests/Results_profile_0_motion_Kocaeli-EL.xlsx`

Locked baseline semantics:

- `nonlinear`
- `rigid`
- `outcrop`
- `frequency_independent`
- `newmark`
- `viscous_damping_update = false`

## Latest Measured Signature

Current baseline signature:

- `surface_nrmse = 0.09870589867598616`
- `psa_nrmse = 0.07108930093481652`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `input_history_nrmse = 8.170042486602506e-07`
- `applied_input_psa_nrmse = 2.3215137809655103e-07`
- `gamma_max_nrmse = 0.14464029225429248`
- `secant_g_over_gmax_nrmse = 0.16772921218927922`
- `stress_path_nrmse = 0.28814503592641405`
- `loop_energy_pct_diff = 139.8288639695613`

Best recent non-accepting improvement:

- `surface_nrmse = 0.09784566426405236`
- `psa_nrmse = 0.07056179329734742`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `gamma_max_nrmse = 0.1403686017946717`
- `secant_g_over_gmax_nrmse = 0.1660441579439227`
- `stress_path_nrmse = 0.2882942693825603`
- `loop_energy_pct_diff = 136.20347327498024`

Interpretation:

- input/application closure is already strong
- amplitude metrics can move a little
- peak-period drift remains the most important unresolved signature

## Boundary-First Verification

### Active acceptance pair

Current boundary-first acceptance pair:

- `elastic_halfspace + outcrop`
- `rigid + within`

Secondary UI-only comparison:

- `elastic_halfspace + outcrop`
- `rigid + outcrop`

Primary DeepSoil DB truth:

- `C:/DEEPSOIL/Batch Output/Batch_run_22/.../deepsoilout.db3`
- `C:/DEEPSOIL/Batch Output/Batch_run_23/.../deepsoilout.db3`

Secondary/reference-only:

- `deepsoilout_el.db3`

### Current DeepSoil vs GeoWave delta signature

DeepSoil DB acceptance pair:

- `surface_psa_peak_ratio_b_over_a = 0.456364862735604`
- `surface_peak_period_shift_pct_b_vs_a = -10.80562182914802`
- `surface_pga_ratio_b_over_a = 0.606462884870241`
- `surface_pgd_ratio_b_over_a = 0.615220667162744`

GeoWave acceptance pair after semantic locking:

- `surface_psa_peak_ratio_b_over_a = 0.5919061710181303`
- `surface_peak_period_shift_pct_b_vs_a = -10.80562182914802`
- `surface_pga_ratio_b_over_a = 0.7591068150415613`
- `surface_pgd_ratio_b_over_a = 0.6037920132428813`

Case-local amplification audit:

- DeepSoil rigid-within `surface/input` peak-PSA amplification is about `3.4047x`; GeoWave rigid-within is about `2.3182x`
- DeepSoil elastic-outcrop `surface/input` peak-PSA amplification is about `1.5538x`; GeoWave elastic-outcrop is about `1.3721x`
- the remaining magnitude gap is therefore dominated by under-amplified rigid-within response; the elastic case is closer

Case-truth profile audit:

- rigid-within:
  - `gamma_max` is already close (`GeoWave / DeepSoil mean ratio ~1.10`)
  - `max_stress_ratio` is low (`~0.75`)
  - profile PGA is low (`~0.74`)
  - the reusable all-layer truth+tangent audit now shows Layer 5 as the dominant mean-compliance carrier (`~0.2097`), with Layers 2-5 all staying in the same soft band (`~0.18-0.21`)
  - the derived proxy audit now shows `stress_proxy` is low across the full column (`~0.75x`) while `secant_proxy` is even lower (`~0.70x` mean), with the strongest secant deficit in Layer 1 (`~0.52x`) and Layers 2-4 still materially soft (`~0.66-0.76x`)
  - after correcting the layer-index alignment, the time-history ratios show `mean kt / ref secant` is not low on average (`~1.74x` mean), but `min kt / ref secant` still falls to about `0.49x` and `tau_peak_proxy` drops from `~1.12x` in Layer 1 to `~0.75x` in Layer 5
- elastic-outcrop:
  - `gamma_max` is high (`~1.44`)
  - `max_stress_ratio` is much closer (`~0.92`)
  - profile PGA is still low (`~0.82`)
- interpretation:
  - the remaining magnitude gap is no longer best described as a pure boundary-input scaling problem
  - rigid-within especially now points back to constitutive stress development / tangent-history closure under the already-locked boundary semantics
  - the rigid-case deficit is not just deepest-layer compliance; the upper-to-mid column is also carrying too little stress per unit strain
  - the updated time-history view says the problem is not a low average tangent alone; it is more likely low-end tangent excursions and insufficient cyclic stress mobilization

Delta-to-delta interpretation:

- peak RS ratio direction: matched
- peak-period direction: matched
- surface PGA direction: matched
- surface PGD / max-displacement direction: matched

Meaning:

- the boundary-first semantics refactor corrected the earlier sign/direction error for response spectra
- the relative-displacement fix also corrected the PGD direction
- the boundary-first acceptance pair has now passed the directional gate
- constitutive family work should still remain paused until first-order boundary magnitude closure is cleaner
- first-order magnitude closure should target rigid-within amplification before opening another constitutive family
- after the case-truth profile audit, the next targeted constitutive work should be rigid-within stress-path/tangent audit, not another boundary semantic rewrite

## What Is Already Falsified

The remaining mismatch is not primarily:

- input `dt`
- rigid/outcrop semantics
- plotting or displacement-animation artifacts
- monotonic literal `theta` / backbone mismatch

Recent parity work also falsifies the following as standalone strategies:

- `exp_scalar_reload_sweeps`
  - scalar `reload_factor` sweeps are not a viable primary closure path
- `exp_mode3_reversal_tangent_preserving`
  - reversal-tangent-preserving branch form changed loop behavior but regressed overall parity and did not reduce peak-period drift
- `exp_mode4_selective_bottom_layers`
  - selective deep-layer tangent restore did not move `surface_psa_peak_period_diff_pct`
- `exp_elastic_halfspace_bedrock_damping_review`
  - DeepSoil v7.1 notes bedrock damping ratio has no effect in time-domain analyses, so standalone halfspace `% damping` tuning is not a primary parity lever

Recent diagnostics also establish:

- `exp_boundary_semantics_audit`
  - `rigid+outcrop` vs `elastic_halfspace+outcrop` is expected to show a large difference in GeoWave because rigid-base outcrop input is halved before application, while elastic-halfspace outcrop input is not
  - in the audited 5-layer `Vs=500` profile over explicit `Vs=760` halfspace, the full response gap was about `2.21x` in max surface PSA, but the boundary-only residual after normalizing input semantics was only about `1.11x`
  - on the canonical Kocaeli motion, the same normalization reduces the elastic-halfspace amplitude gap much further: `elastic_halfspace+outcrop` is about `1.31x` of `rigid+outcrop` in max surface PSA, but only about `0.98x` of `rigid+within`
  - the Kocaeli residual boundary effect appears more clearly in period than amplitude, with about `+5.70%` surface peak-period increase for `elastic_halfspace+outcrop`
- `exp_elastic_halfspace_force_balance_audit`
  - on the canonical Kocaeli motion, the elastic-halfspace incident base force and dashpot reaction are almost equal in RMS magnitude (`~0.989x`) and very highly correlated (`~0.994`)
  - the residual net boundary traction RMS is only about `10.85%` of the incident-force RMS
  - this means the remaining elastic-halfspace effect is better interpreted as coupled impedance cancellation behavior than as a large standalone base-force amplification
- `exp_elastic_halfspace_frequency_audit`
  - on the canonical Kocaeli motion, the residual net boundary traction and the elastic-halfspace surface response share the same dominant frequency at about `5.367 Hz` (`T ≈ 0.1863 s`)
  - at that frequency, the residual net traction amplitude is only about `0.589x` of incident-force amplitude, but its phase is close to the surface response (`~5.67°` difference)
  - this supports a frequency-selective residual traction interpretation of the halfspace effect, not a gross-force-magnitude interpretation
- `exp_boundary_case_truth_profile_compare`
  - rigid-within `gamma_max` is already close to DeepSoil (`~1.10x`) while `max_stress_ratio` and profile PGA remain low (`~0.75x`)
  - elastic-outcrop is closer in stress ratio (`~0.92x`) even though its `gamma_max` overshoots (`~1.44x`)
  - this means the next magnitude-closure step should target rigid-case constitutive stress/tangent evolution, not another boundary semantic rewrite
  - the reusable artifact `output/baseline_iter/rigid_within_case_truth_layer_audit/case_truth_compare.json` now ties the rigid-within profile truth directly to the GeoWave layer-sweep tangent audit
  - that artifact shows Layer 5 is still the dominant compliance carrier (`~0.2097`) and that low stress-ratio / PGA is a full-column pattern, not a single-layer anomaly
- `exp_boundary_first_semantic_locking`
  - a shared boundary-input adapter now locks the same incident-wave meaning across rigid and elastic paths
  - DeepSoil DB delta ingestion is in place, so GeoWave and DeepSoil boundary signatures are now compared in the same report shape
  - after this change, GeoWave matches DeepSoil direction for peak RS ratio, peak-period shift, surface PGA, and surface PGD
  - the first hard gate now passes; the remaining work is first-order boundary magnitude closure

## Current Strongest Diagnosis

The best current interpretation is:

- the canonical rigid/outcrop baseline gap is not dominated by monotonic envelope mismatch
- the canonical rigid/outcrop baseline gap is not explained by which single layer owns the most compliance
- the canonical rigid/outcrop baseline gap is likely generated by cyclic branch evolution
- the current elastic-vs-rigid boundary verification gap is no longer primarily a direction/sign problem in PSA, period, or PGA
- the current elastic-vs-rigid boundary verification gap is no longer primarily a direction/sign problem in PSA, period, PGA, or PGD
- the active boundary-first task is now first-order magnitude closure under the locked semantics pair

Most likely residual mechanisms:

- F_mrdf evolution is too static
- translated branch curvature is not evolving the same way DeepSoil does
- reversal-state / branch-progress semantics are under-modeled
- the important missing behavior may be distributed through the full cyclic tangent history, not just reversal onset
- for the boundary-first pair specifically, the remaining work is now magnitude closure, not sign closure

## Experiment Family Matrix

### `exp_scalar_reload_sweeps`

- status: completed
- verdict: `falsified`
- summary:
  - scalar reload-only tuning is not closing the system-level residual

### `exp_mode3_reversal_tangent_preserving`

- status: completed
- verdict: `falsified`
- summary:
  - changed loop energy materially
  - degraded local path parity
  - did not reduce `surface_psa_peak_period_diff_pct`

### `exp_mode4_translated_local_tangent_restore`

- status: completed
- verdict: `improved_non_accepting`
- summary:
  - slightly improved `surface_nrmse`, `psa_nrmse`, `gamma_max_nrmse`, and `secant_g_over_gmax_nrmse`
  - did not change the `+11.732%` peak-period signature

### `exp_mode4_selective_bottom_layers`

- status: completed
- verdict: `falsified`
- summary:
  - applying the same tangent-restore idea only to bottom layers did not move peak period

### `exp_single_element_direct_debug`

- status: completed
- verdict: `diagnostic_only`
- summary:
  - local stress/secant path parity is much better than system-level parity
  - this supports the idea that the residual is in accumulated cyclic branch/tangent history

### `exp_layer_sweep_current_vs_mode4`

- status: completed
- verdict: `diagnostic_only`
- summary:
  - lower layers dominate compliance share
  - mode 4 increases equivalent stiffness minimum
  - peak-period drift still does not move

### `exp_fmrdf_evolution_progress_rule`

- status: completed
- verdict: `regressed`
- summary:
  - branch-progress or reversal-state aware `F_mrdf` evolution improved local replay metrics
  - full-column response regressed
  - peak period did not move

### `exp_translated_branch_curvature_rule`

- status: completed
- verdict: `regressed`
- summary:
  - mode 6 and mode 7 both improved local Layer 1 replay strongly
  - both regressed full-column response
  - peak period did not move

### `exp_boundary_first_semantic_locking`

- status: completed
- verdict: `improved_non_accepting`
- summary:
  - introduced a shared boundary-input semantic adapter used by both rigid and elastic solver paths
  - added solver-level reconstructed-vs-assembled boundary-force audit
  - added DeepSoil DB ingestion for `RESPONSE_SPECTRA`, `PROFILES`, and `TIME_HISTORIES`
  - GeoWave now matches DeepSoil direction for peak RS ratio, peak-period shift, surface PGA, and surface PGD on the acceptance pair
  - this family passed the directional gate and is now in first-order magnitude closure

### `exp_multilayer_path_targeting_rule`

- status: planned
- verdict: `diagnostic_only`
- summary:
  - paused while boundary-first first-order magnitude closure remains open
  - target is multi-layer response-path closure, not more isolated Layer 1 branch shaping

## Current Diagnostic Highlights

Single-element replay, current:

- `stress_path_nrmse = 0.015184199057194654`
- `secant_path_nrmse = 0.010475989816892187`
- `loop_energy_pct_diff = 60.11186908406478`
- branch kind: `translated_local_bridge`

Single-element replay, mode 3:

- `stress_path_nrmse = 0.03868166454105839`
- `secant_path_nrmse = 0.031393935013354225`
- `loop_energy_pct_diff = 39.39043271636329`
- branch kind: `reversal_tangent_preserving`

Solver audit, current Layer 1:

- `g_ref_min_kpa = 460221.23764`
- `g_t_ref_min_kpa = 255116.44108`

Solver audit, mode 4 Layer 1:

- `g_ref_min_kpa = 460344.11462`
- `g_t_ref_min_kpa = 300808.71321`

Layer sweep, current:

- dominant layer by mean compliance: `Layer 5`
- dominant mean compliance fraction: `0.20733761653761226`
- lower-layer compliance share (`Layer 3-5`): `0.6128809573684435`

Layer sweep, mode 4:

- dominant layer by mean compliance: `Layer 5`
- dominant mean compliance fraction: `0.20587104941325168`
- equivalent stiffness minimum rises from `8558.666197495662` to `10361.731182540727`

Interpretation:

- mode 4 shifts tangent reference behavior in the expected direction
- that is still insufficient to change the governing peak-period signature

Mode 5 branch-progress replay:

- `stress_path_nrmse = 0.015088039604454448`
- `secant_path_nrmse = 0.011210464172541816`
- `loop_energy_pct_diff = 48.93282270680512`
- `f_mrdf_min = 0.8199999999999985`
- `f_mrdf_max = 0.9999999999999989`

Mode 5 system compare:

- `surface_nrmse = 0.10650708966370438`
- `psa_nrmse = 0.08096349146053539`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `gamma_max_nrmse = 0.1659109966823451`
- `secant_g_over_gmax_nrmse = 0.14502475357300681`
- `stress_path_nrmse = 0.300855359393076`
- `loop_energy_pct_diff = 212.55845555241683`

Interpretation:

- local Layer 1 loop improvement alone is not a reliable closure signal
- standalone F_mrdf evolution regressed system parity
- the next hypothesis should target translated branch curvature directly

Mode 6 / Mode 7 single-element replay:

- `stress_path_nrmse = 0.014380843963461912`
- `secant_path_nrmse = 0.01137543607915916`
- `loop_energy_pct_diff = 32.83278145613474`

Mode 6 system compare:

- `surface_nrmse = 0.11831004510158506`
- `psa_nrmse = 0.09562715448573829`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `gamma_max_nrmse = 0.18863643874997899`
- `secant_g_over_gmax_nrmse = 0.14709538344433926`
- `stress_path_nrmse = 0.2766060333440179`

Mode 7 system compare:

- `surface_nrmse = 0.11771469066700418`
- `psa_nrmse = 0.09489100396522135`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `gamma_max_nrmse = 0.18472123811880561`
- `secant_g_over_gmax_nrmse = 0.1461020512759384`
- `stress_path_nrmse = 0.27785674787899906`

Interpretation:

- translated-branch curvature shaping improved local replay more than mode 5
- the full-column response still regressed
- even the hybrid curvature+tangent-restore branch did not outperform mode 4
- this points away from more isolated Layer 1 branch-shape tuning and toward multi-layer response-path closure

## Ordered Next Hypotheses

Research order is currently locked to:

1. `exp_boundary_first_semantic_locking`
   - keep the acceptance pair at `elastic_halfspace + outcrop` vs `rigid + within`
   - keep the DeepSoil truth surface at `deepsoilout.db3`
   - keep closing first-order magnitude before reopening constitutive retuning
2. boundary magnitude audit
   - compare compliant-base displacement and spectra magnitude, not only direction
   - keep using the same delta-to-delta report shape for GeoWave and DeepSoil
3. rerun the DeepSoil DB boundary comparison
   - direction is already aligned for peak RS ratio, peak period, PGA, and PGD
   - first-order magnitude is next
4. only after boundary-first closure, return to `exp_multilayer_path_targeting_rule`
5. revisit `exp_mode4_translated_local_tangent_restore` only as the best non-accepting constitutive reference
6. revisit `F_mrdf evolution`, `branch-progress`, or `previous-cycle memory` only if coupled to the multi-layer target

## Legacy Research Context

Historical notes remain useful but are not the active parity truth:

- `deep-research-report.md`
- `deep-research-report_15042026.md`

Treat them as legacy research context, not the current execution dossier.
