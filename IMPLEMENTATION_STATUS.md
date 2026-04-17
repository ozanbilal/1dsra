# GeoWave Implementation Status

Last updated: 2026-04-17

## Summary

This file remains the implementation/status source of truth for the repo.

The repo is operating in `core-only + DeepSoil baseline parity` mode.

Active runtime surface:

- `linear`
- `eql`
- `nonlinear`

Primary engineering target:

- close `DeepSoil rigid/outcrop baseline parity`
- using the native `GQ/H + MRDF (UIUC)` nonlinear path
- judged on response-level compare metrics against the real workbook export

Supporting parity-campaign docs:

- `DEEPSOIL_BASELINE_PARITY_RESEARCH.md`
- `PARITY_MEMORY.md`
- `parity_experiment_index.json`
- `AGENTS.md`

Current repo truth:

- Excel importer is in place
- compare pipeline is in place
- input history and applied-input semantics are effectively closed
- the main remaining mismatch is constitutive hysteresis parity

## Current Product Reality

### Active runtime surface

- Config/runtime defaults come from `python/dsra1d/config/models.py`
- Current parity-critical defaults are:
  - `boundary_condition = rigid`
  - `analysis.solver_backend = nonlinear`
  - `analysis.damping_mode = frequency_independent`
  - `analysis.integration_scheme = newmark`
  - `analysis.viscous_damping_update = false`
  - `motion.input_type = outcrop`

### Active engineering path

- Canonical baseline example:
  - `examples/native/deepsoil_gqh_5layer_baseline.yml`
- Primary DeepSoil reference workbook:
  - `tests/Results_profile_0_motion_Kocaeli.xlsx`
- Secondary cross-check workbook:
  - `tests/Results_profile_0_motion_Kocaeli-EL.xlsx`

### Active parity toolchain

- Workbook import:
  - `python/dsra1d/deepsoil_excel.py`
- Response-level compare:
  - `python/dsra1d/deepsoil_compare.py`
- Constitutive replay and solver audit:
  - `python/dsra1d/constitutive_debug.py`
- Recent parity iteration outputs:
  - `output/baseline_iter/`

## Baseline Parity

### Canonical case

- Case name: `deepsoil_gqh_5layer_baseline`
- Required semantics:
  - `nonlinear`
  - `rigid`
  - `outcrop`
  - `frequency_independent`
  - `newmark`
  - `viscous_damping_update = false`

### Latest measured parity signature

Current baseline (`mode3_current` compare artifact):

- `surface_nrmse = 0.09870589867598616`
- `psa_nrmse = 0.07108930093481652`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `input_history_nrmse = 8.170042486602506e-07`
- `applied_input_psa_nrmse = 2.3215137809655103e-07`
- `gamma_max_nrmse = 0.14464029225429248`
- `secant_g_over_gmax_nrmse = 0.16772921218927922`
- `stress_path_nrmse = 0.28814503592641405`
- `loop_energy_pct_diff = 139.8288639695613`

Best recent non-accepting improvement (`mode4_experimental`):

- `surface_nrmse = 0.09784566426405236`
- `psa_nrmse = 0.07056179329734742`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `gamma_max_nrmse = 0.1403686017946717`
- `secant_g_over_gmax_nrmse = 0.1660441579439227`
- `stress_path_nrmse = 0.2882942693825603`
- `loop_energy_pct_diff = 136.20347327498024`

Meaning:

- input parity is already closed to numerical noise
- small constitutive changes can improve amplitude metrics slightly
- the dominant residual signature is still the unchanged `+11.732%` surface PSA peak-period drift

Standalone `F_mrdf` branch-progress experiment (`mode5_experimental`):

- `surface_nrmse = 0.10650708966370438`
- `psa_nrmse = 0.08096349146053539`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`
- `gamma_max_nrmse = 0.1659109966823451`
- `secant_g_over_gmax_nrmse = 0.14502475357300681`
- `stress_path_nrmse = 0.300855359393076`
- `loop_energy_pct_diff = 212.55845555241683`

Meaning:

- local Layer 1 replay improved
- system-level parity regressed
- standalone branch-progress `F_mrdf` evolution is not sufficient as a closure path

Translated-branch curvature experiments (`mode6_experimental` / `mode7_experimental`):

- `mode6 surface_nrmse = 0.11831004510158506`
- `mode6 psa_nrmse = 0.09562715448573829`
- `mode6 surface_psa_peak_period_diff_pct = 11.732494130275942`
- `mode7 surface_nrmse = 0.11771469066700418`
- `mode7 psa_nrmse = 0.09489100396522135`
- `mode7 surface_psa_peak_period_diff_pct = 11.732494130275942`

Meaning:

- both mode 6 and mode 7 improved local Layer 1 replay strongly
- both regressed full-column parity relative to current baseline and mode 4
- mode 4 remains the best observed non-accepting system-level variant

### What is already ruled out

The remaining mismatch is not primarily:

- input `dt`
- rigid vs outcrop semantics
- plotting/displacement UI artifacts
- monotonic literal `theta` / backbone mismatch

Recent falsifications add:

- increasing tangent floor or local tangent restore alone does not close peak-period drift
- deep layers do dominate compliance, but selective deep-layer tangent restore still does not move peak period
- standalone branch-progress `F_mrdf` evolution improved local loop behavior but regressed full-column response and left peak period unchanged
- standalone translated-branch curvature shaping, with or without tangent restore, improved local replay but regressed full-column response and left peak period unchanged
- DeepSoil v7.1 halfspace definition notes bedrock damping ratio has no effect in time-domain analyses; for elastic-halfspace parity the primary lever is impedance boundary semantics (`Vs`, unit weight), not a standalone bedrock `% damping` tweak
- canonical Kocaeli boundary audit confirms that most `rigid+outcrop` vs `elastic_halfspace+outcrop` amplitude gap is still input-semantics-driven; once compared against `rigid+within`, the residual boundary effect is modest in PSA amplitude and clearer in peak period (`+5.703592242778525%`)
- canonical Kocaeli elastic-halfspace force-balance audit shows the incident force and dashpot reaction nearly cancel (`dashpot_to_incident_rms_ratio ≈ 0.989`, correlation `≈ 0.994`); the residual net boundary traction RMS is only about `10.85%` of the incident-force RMS
- canonical Kocaeli elastic-halfspace frequency audit shows that the residual net boundary traction and surface response share the same dominant frequency (`≈ 5.3667 Hz`, `T ≈ 0.1863 s`); the remaining halfspace effect is therefore frequency-selective and phase-coupled, not a bulk force amplification

### Current mismatch interpretation

The strongest current diagnosis is:

- not an input application problem
- not a monotonic backbone problem
- not a simple deep-layer stiffness-floor problem
- not a standalone branch-progress `F_mrdf` problem
- not a standalone translated-branch curvature problem
- most likely a cyclic branch-evolution problem

The likely remaining cause is now centered on:

- layer-distributed constitutive evolution across the full column
- active tangent history as it accumulates over all layers, not only Layer 1 replay quality
- `F_mrdf` evolution and translated-branch curvature only insofar as they improve the multi-layer response path
- active tangent evolution and how that tangent reaches the global solver

## Latest Diagnostic Findings

### Single-element replay

Current baseline direct replay:

- `stress_path_nrmse = 0.015184199057194654`
- `secant_path_nrmse = 0.010475989816892187`
- `secant_envelope_nrmse = 0.13034828283465213`
- `loop_energy_pct_diff = 60.11186908406478`
- branch kind is effectively `translated_local_bridge`

Mode 3 reversal-tangent-preserving replay:

- `stress_path_nrmse = 0.03868166454105839`
- `secant_path_nrmse = 0.031393935013354225`
- `secant_envelope_nrmse = 0.408112824163333`
- `loop_energy_pct_diff = 39.39043271636329`
- peak-period closure did not improve at system level

Interpretation:

- mode 3 altered loop energy, but degraded local path parity and did not move the system-period signature

### Solver tangent audit

Current direct debug, Layer 1:

- `g_ref_min_kpa = 460221.23764`
- `g_t_ref_min_kpa = 255116.44108`

Mode 4 direct debug, Layer 1:

- `g_ref_min_kpa = 460344.11462`
- `g_t_ref_min_kpa = 300808.71321`

Interpretation:

- mode 4 does raise the tangent reference floor
- that change produces only small amplitude improvement
- peak-period drift remains unchanged

### Layer sweep

Current all-layer audit:

- dominant layer by mean compliance: `Layer 5`
- dominant mean compliance fraction: `0.20733761653761226`
- lower-layer compliance share (`Layer 3-5`) is about `0.6128809573684435`
- equivalent stiffness minimum: `8558.666197495662`

Mode 4 all-layer audit:

- dominant layer by mean compliance: `Layer 5`
- dominant mean compliance fraction: `0.20587104941325168`
- equivalent stiffness minimum: `10361.731182540727`

Selective deep-layer experiments:

- `mode4_bottom3` and `mode4_bottom2` slightly improve amplitude metrics
- both leave `surface_psa_peak_period_diff_pct` unchanged at `11.732494130275942`

Interpretation:

- the residual is not explained by only “which layer got more tangent”
- the residual is more likely driven by how tangent evolves through branch progress over the full cyclic history

### Mode 5 branch-progress audit

Single-element replay, mode 5:

- `stress_path_nrmse = 0.015088039604454448`
- `secant_path_nrmse = 0.011210464172541816`
- `loop_energy_pct_diff = 48.93282270680512`
- `f_mrdf` now evolves from `1.0` at reversal to `0.82` deeper into the branch

System compare, mode 5:

- `surface_nrmse = 0.10650708966370438`
- `psa_nrmse = 0.08096349146053539`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`

Interpretation:

- improving a local hysteresis replay signature is not enough on its own
- the remaining problem is more likely in translated-branch curvature at system scale than in standalone `F_mrdf` progression

### Mode 6 / Mode 7 curvature-family audit

Mode 6 single-element replay:

- `stress_path_nrmse = 0.014380843963461912`
- `secant_path_nrmse = 0.01137543607915916`
- `loop_energy_pct_diff = 32.83278145613474`

Mode 7 single-element replay:

- `stress_path_nrmse = 0.014380843963461912`
- `secant_path_nrmse = 0.01137543607915916`
- `loop_energy_pct_diff = 32.83278145613474`

Mode 6 system compare:

- `surface_nrmse = 0.11831004510158506`
- `psa_nrmse = 0.09562715448573829`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`

Mode 7 system compare:

- `surface_nrmse = 0.11771469066700418`
- `psa_nrmse = 0.09489100396522135`
- `surface_psa_peak_period_diff_pct = 11.732494130275942`

Interpretation:

- making Layer 1 translated-branch shape look better does not automatically improve the column response
- current acceptance should not be driven by Layer 1 replay quality alone
- the next diagnostic step should target multi-layer response path closure, not another isolated branch-shape family

## Next Technical Iterations

The next work is decision-complete and should proceed in this order:

1. add multi-layer path targeting diagnostics
   - compare per-layer `gamma_max`, secant proxy, stress-path signal, and compliance contribution together
   - stop treating Layer 1 replay improvement as a sufficient proxy for column parity
2. revisit mode 4 as the best non-accepting baseline
   - use new multi-layer diagnostics to target constitutive changes where they matter system-wide
3. revisit `F_mrdf evolution / branch-progress` or translated-branch curvature only if coupled to the multi-layer target
   - do not reopen standalone mode 5, 6, or 7 as primary strategies
4. revisit previous-cycle memory only if new multi-layer data supports it
   - do not reopen generic replay work without evidence
5. rerun full primary compare against `tests/Results_profile_0_motion_Kocaeli.xlsx`
6. only after meaningful primary improvement, rerun the secondary workbook cross-check

## Legacy Context

Older roadmap language still exists elsewhere in the repo and may mention:

- OpenSees-heavy product direction
- PM4 calibration paths
- broader feature-expansion goals

Treat that as legacy context, not current engineering direction.

For dated research notes, see:

- `deep-research-report.md`
- `deep-research-report_15042026.md`

Those remain useful as historical context, but the active parity campaign now lives in:

- `IMPLEMENTATION_STATUS.md`
- `DEEPSOIL_BASELINE_PARITY_RESEARCH.md`
- `PARITY_MEMORY.md`
- `parity_experiment_index.json`
