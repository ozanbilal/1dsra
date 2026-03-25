# Scientific Confidence Matrix

Last updated: 2026-03-25

This matrix is the single source of truth for release scientific signoff.

## Confidence Tier Definitions

| Tier | Meaning | Criteria |
|------|---------|----------|
| High | Publication-grade | Validated against published reference data; tolerances match peer-reviewed thresholds |
| Medium-High | Physics-grounded | Internally consistent, physics-based checks pass; partial external reference |
| Medium | Internal regression | Deterministic regression gates pass; external validation pending |
| Low | Scaffold only | Code exists but no formal validation |

## Suite Matrix

| suite | case_count | reference_basis | tolerance_policy | binary_fingerprint | last_verified_utc | confidence_tier | status_notes |
|---|---:|---|---|---|---|---|---|
| `core-es` | 3 | internal effective-stress regression set | `pga` abs `1e-6`, `ru_max` abs `1e-9`, `delta_u_max` abs `1e-9`, `sigma_v_eff_min` abs `1e-9`, dt-sensitivity `<=5.0%` | n/a (native/mock path) | `2026-03-25T00:00:00Z` | Medium | Internal-only reference lock; external publication lock pending |
| `core-hyst` | 3 | internal MKZ/GQH hysteretic regression set | `pga` abs+rel `5%`, `ru_max` abs `1e-8`, `delta_u_max` abs `1e-8`, `sigma_v_eff_min` abs `1e-6`, dt-sensitivity `<=5.0%` | n/a (native path) | `2026-03-25T00:00:00Z` | Medium | Published loop/reference lock pending; G/Gmax floor validated against DEEPSOIL Example 5A |
| `core-linear` | 3 | internal linear SH + transfer checks; Seed & Idriss (1970) amplification range | `pga` rel `5%`, `transfer_abs_max` rel `5%`, `transfer_peak_freq_hz` abs `0.5 Hz`, dt-sensitivity `<=6.0%` | n/a (native path) | `2026-03-25T00:00:00Z` | Medium-High | Linear amplification physically bounded; transfer function stabilized with amplitude-floor masking |
| `core-eql` | 3 | internal EQL regression + convergence persistence; Darendeli (2001) modulus reduction/damping targets | `pga` rel `5%`, `transfer_abs_max` rel `5%`, `transfer_peak_freq_hz` abs `0.5 Hz`, dt-sensitivity `<=5.0%` | n/a (native path) | `2026-03-25T00:00:00Z` | Medium | SHAKE/DEEPSOIL external lock pending; Darendeli calibration validated through `calibrate-darendeli` CLI |
| `opensees-parity` | 6 | dedicated OpenSees parity envelope (`parity01..06`) | explicit locked checks + solver diagnostic constraints + dt-sensitivity gates | `5aa4e9c80c410c510ca62ac3b2f1d64a8e50679f0238e140b5bebcd6d5ddbe6d` | `2026-03-04T16:31:31Z` | Medium | Fingerprint locked from local OpenSees binary; dedicated runner must match exactly at release signoff |

## Published Reference Mapping

| Domain | Reference | Applicable Suites | Acceptance Criteria | Current Status |
|--------|-----------|-------------------|---------------------|----------------|
| Modulus reduction curves | Darendeli (2001) | `core-eql`, `core-hyst` | G/Gmax fit RMSE < 0.05 over strain range 1e-6 to 0.1 | Implemented in `calibrate-darendeli`; fit quality tracked per calibration |
| Damping curves | Darendeli (2001) | `core-eql`, `core-hyst` | D_min within 0.5-3% for clean sands (PI=0); monotonic increase with strain | Darendeli formulation bugfix applied (masing_scaling clip); damping curve shape validated |
| Masing hysteresis rules | Phillips & Hashash (2009) | `core-hyst` | MRDF F(gamma) bounded [0, 1.5]; Masing loop energy increases monotonically | MRDF module implemented; over-correction documented when combined with G/Gmax floor |
| MKZ backbone | Matasovic & Vucetic (1993) | `core-hyst`, `core-eql` | Backbone stress monotonically increasing; G/Gmax = 1/(1+(gamma/gamma_ref)^beta) | Validated; `g_reduction_min` floor prevents excessive softening at large strains |
| GQ/H backbone | Groholski et al. (2016) | `core-hyst`, `core-eql` | Shape parameters a1, a2, m produce physically reasonable G/Gmax; taumax bounded | Validated through Darendeli calibration fit |
| Linear site response | Kramer (1996) Ch. 7 | `core-linear` | 1D SH transfer function: peak at f_n = Vs/(4H) for uniform layer; amplification bounded by impedance contrast | Transfer function peaks verified; amplitude-floor masking prevents low-energy blow-up |
| EQL iteration | Seed & Idriss (1969), Schnabel et al. (1972) SHAKE | `core-eql` | Strain-compatible iteration converges within 15 iterations; effective strain ratio 0.65 | Convergence tracked and stored; max 15 iterations default |
| Nonlinear time integration | Newmark (1959), DEEPSOIL manual | `core-hyst` | Average-acceleration (beta=0.25, gamma=0.5) unconditionally stable; energy balance consistent | Implicit Newmark solver validated; PGA within 3% of DEEPSOIL for Example 5A with G/Gmax floor |
| Rayleigh damping | Chopra (2012) | all native solvers | alpha/beta from two-frequency formulation; damping ratio exact at target frequencies | Shared damping module with validated Rayleigh coefficient computation |
| PM4Sand constitutive | Boulanger & Ziotopoulou (2017) | `core-es`, `opensees-parity` | Dr, G0, hpo mandatory; strict_plus profile validates u-p setup | Schema validation implemented; full physics parity pending real-binary tests |
| PM4Silt constitutive | Boulanger & Ziotopoulou (2018) | `core-es`, `opensees-parity` | Su, Su_Rat, G_o, h_po mandatory | Schema validation implemented; calibration template available |

## Tolerance Rationale

| Metric | Tolerance | Basis |
|--------|-----------|-------|
| PGA | rel 5% or abs 0.002 m/s2 | Engineering practice: site response PGA within 5% is excellent agreement (Stewart et al., 2014) |
| PSA NRMSE | < 10% | Normalized root-mean-square error below 10% indicates good spectral match (Hashash et al., 2010) |
| Transfer function peak | rel 5% | Amplification factor within 5% of reference is acceptable for engineering design |
| Transfer peak frequency | abs 0.5 Hz | Fundamental frequency within 0.5 Hz accounts for discretization and Vs uncertainty |
| dt-sensitivity | < 6% max relative PSA diff | Time-step halving produces < 6% PSA change confirms convergence (DEEPSOIL validation protocol) |
| Damping ratio | abs 1% at small strain | Small-strain damping uncertainty of 1% is standard for laboratory measurements |
| ru_max | abs 1e-8 | Numerical precision for total-stress analyses (should be exactly 0) |

## Upgrade Path

To raise a suite from Medium to Medium-High:
1. Lock golden values from a published/reference case (not just internal regression)
2. Document the reference source and scenario mapping
3. Update `reference_basis` column and `last_verified_utc`

To raise from Medium-High to High:
1. Match at least 3 published scenarios per suite with documented acceptance
2. Include external peer review or reproduction by independent implementation
3. Publish comparison report under `output/pdf/validation/`

Notes:
- UI parity does not increase scientific confidence by itself; confidence is gated by numerical benchmark/parity evidence.
- Confidence tiers can only be raised when reference basis and verification timestamp are updated together.
- MRDF correction module is available but not currently activated in default configs; it requires case-specific Darendeli damping calibration and should NOT be combined with `g_reduction_min` floor (causes over-correction).
