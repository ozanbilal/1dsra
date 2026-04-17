# Parity Memory

This file is the human-readable experiment-family memory for the DeepSoil baseline campaign.

Use it to avoid rerunning already-falsified ideas.

The machine-readable companion is:

- `parity_experiment_index.json`

Canonical case:

- `examples/native/deepsoil_gqh_5layer_baseline.yml`

Primary workbook:

- `tests/Results_profile_0_motion_Kocaeli.xlsx`

## Active Do-Not-Repeat Guidance

Do not reopen these as the main parity strategy unless there is genuinely new evidence:

- `exp_scalar_reload_sweeps`
- `exp_mode3_reversal_tangent_preserving`
- `exp_mode4_selective_bottom_layers`
- `exp_fmrdf_evolution_progress_rule`
- `exp_translated_branch_curvature_rule`
- `exp_elastic_halfspace_bedrock_damping_review`
- `exp_boundary_semantics_audit`

## Experiment Families

### `exp_scalar_reload_sweeps`

- family: scalar reload-only tuning
- verdict: `falsified`
- reason:
  - scalar `reload_factor` sweeps do not target the remaining system-level signature
- do not repeat:
  - do not spend more parity cycles on reload-only scalar scans

### `exp_mode3_reversal_tangent_preserving`

- family: reversal-tangent-preserving MRDF branch
- verdict: `falsified`
- reason:
  - loop energy moved, but local path parity regressed and peak period did not improve
- do not repeat:
  - do not rerun unchanged mode 3 as if it were a fresh closure path

### `exp_mode4_translated_local_tangent_restore`

- family: translated-local tangent-restore bridge
- verdict: `improved_non_accepting`
- reason:
  - small amplitude improvement
  - no movement in `surface_psa_peak_period_diff_pct`
- do not repeat:
  - do not treat unchanged mode 4 as the acceptance solution

### `exp_mode4_selective_bottom_layers`

- family: selective deep-layer tangent restore
- verdict: `falsified`
- reason:
  - deep layers dominate compliance, but selective tangent restore still does not move peak period
- do not repeat:
  - do not rerun bottom-layer-only mode 4 variants without a new constitutive idea behind them

### `exp_single_element_direct_debug`

- family: single-element direct replay and branch tracing
- verdict: `diagnostic_only`
- reason:
  - useful for understanding local path parity
  - not itself a closure strategy

### `exp_layer_sweep_current_vs_mode4`

- family: all-layer tangent/compliance audit
- verdict: `diagnostic_only`
- reason:
  - identified lower-layer compliance dominance
  - falsified pure deep-layer tangent restore as the main fix

### `exp_fmrdf_evolution_progress_rule`

- family: branch-progress / reversal-state aware `F_mrdf` evolution
- verdict: `regressed`
- reason:
  - improved local replay and loop-energy behavior
  - regressed full-column parity
  - did not move `surface_psa_peak_period_diff_pct`
- do not repeat:
  - do not rerun unchanged standalone mode 5 progression as a primary closure path

### `exp_translated_branch_curvature_rule`

- family: translated branch curvature, including hybrid curvature+tangent-restore
- verdict: `regressed`
- reason:
  - mode 6 and mode 7 both improved local Layer 1 replay strongly
  - both regressed full-column parity
  - neither moved `surface_psa_peak_period_diff_pct`
- do not repeat:
  - do not rerun unchanged mode 6 or mode 7 as a primary closure path

### `exp_multilayer_path_targeting_rule`

- family: multi-layer response-path targeting
- verdict: `diagnostic_only`
- status note:
  - planned next family
- next if any:
  - compare per-layer `gamma_max`, secant proxy, stress-path signal, and compliance contribution together before opening another branch-law family

### `exp_elastic_halfspace_bedrock_damping_review`

- family: elastic-halfspace bedrock damping review
- verdict: `falsified`
- reason:
  - DeepSoil v7.1 halfspace definition states bedrock damping ratio has no effect in time-domain analyses
  - GeoWave time-domain elastic-halfspace solvers now carry the field for parity/reference but intentionally use only halfspace impedance from `Vs` and unit weight
- do not repeat:
  - do not treat standalone bedrock `% damping` tuning as a primary closure path for time-domain parity

### `exp_boundary_semantics_audit`

- family: rigid vs elastic-halfspace boundary semantics audit
- verdict: `diagnostic_only`
- reason:
  - current GeoWave semantics produce a real and expected response difference between `rigid+outcrop` and `elastic_halfspace+outcrop`
  - in the audited 5-layer `Vs=500` profile over explicit `Vs=760` halfspace, `elastic_halfspace+outcrop` produced about `2.21x` max surface PSA relative to `rigid+outcrop`
  - most of that comes from input application semantics: `rigid+outcrop` halves the applied acceleration, while `elastic_halfspace+outcrop` does not
  - once input application is normalized (`rigid+within` vs `elastic_halfspace+outcrop`), the residual boundary effect drops to about `1.11x` in max surface PSA for that audit
  - on the canonical Kocaeli motion, `elastic_halfspace+outcrop` is about `1.31x` higher than `rigid+outcrop` in max surface PSA, but only about `0.98x` of `rigid+within`
  - on the same Kocaeli audit, the normalized residual boundary effect shows up more clearly as a period increase of about `+5.70%`, not as a large extra PSA amplification
- do not repeat:
  - do not interpret the full `rigid+outcrop` vs `elastic_halfspace+outcrop` gap as a pure halfspace-damping or pure impedance effect without first separating input semantics

### `exp_elastic_halfspace_force_balance_audit`

- family: elastic-halfspace force-balance audit
- verdict: `diagnostic_only`
- reason:
  - on the canonical Kocaeli motion, the elastic-halfspace incident force and dashpot reaction are almost the same size in RMS terms
  - `dashpot_to_incident_rms_ratio` is about `0.989`
  - `dashpot_incident_corr` is about `0.994`
  - the residual net boundary traction is comparatively small, with `net_to_incident_rms_ratio` about `0.108`
  - this supports the interpretation that the remaining halfspace effect is not a large raw-force amplification but the coupled impedance response after near-cancellation
- do not repeat:
  - do not treat elastic-halfspace parity as a standalone “bigger base force” problem without checking force-balance cancellation first

### `exp_elastic_halfspace_frequency_audit`

- family: elastic-halfspace residual traction frequency audit
- verdict: `diagnostic_only`
- reason:
  - on the canonical Kocaeli motion, the residual net boundary traction and the elastic-halfspace surface response share the same dominant frequency at about `5.367 Hz` (`T ≈ 0.1863 s`)
  - this lines up with the boundary-driven period shift seen in the earlier Kocaeli audit
  - at the surface-dominant frequency, the residual net traction amplitude is only about `0.589` of the incident-force amplitude, but it is phase-shifted only about `5.67°` from the surface response
  - this supports the interpretation that the remaining halfspace effect is a frequency-selective residual traction problem, not a gross force-magnitude problem
- do not repeat:
  - do not interpret the elastic-halfspace effect only through total-force RMS; keep the frequency-local residual traction view
