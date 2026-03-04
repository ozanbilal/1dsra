# Scientific Confidence Matrix

Last updated: 2026-03-04

This matrix is the single source of truth for release scientific signoff.

| suite | case_count | reference_basis | tolerance_policy | binary_fingerprint | last_verified_utc | confidence_tier | status_notes |
|---|---:|---|---|---|---|---|---|
| `core-es` | 3 | internal effective-stress regression set | `pga` abs `1e-6`, `ru_max` abs `1e-9`, `delta_u_max` abs `1e-9`, `sigma_v_eff_min` abs `1e-9`, dt-sensitivity `<=5.0` | n/a (native/mock path) | `2026-03-04T00:00:00Z` | Medium | Internal-only reference lock; external publication lock pending |
| `core-hyst` | 3 | internal MKZ/GQH hysteretic regression set | `pga` abs `1e-6`, `ru_max` abs `1e-8`, `delta_u_max` abs `1e-8`, `sigma_v_eff_min` abs `1e-6`, dt-sensitivity `<=5.0` | n/a (native path) | `2026-03-04T00:00:00Z` | Medium | Published loop/reference lock pending |
| `core-linear` | 3 | internal linear SH + transfer checks | `pga/ru/delta_u/sigma_v_eff_min` abs `1e-6..1e-9`, `transfer_abs_max` rel `5%`, `transfer_peak_freq_hz` abs `0.5 Hz`, dt-sensitivity `<=5.0` | n/a (native path) | `2026-03-04T00:00:00Z` | Medium-High | Physics-grounded but not yet publication-locked |
| `core-eql` | 3 | internal EQL regression + convergence persistence | `pga/ru/delta_u/sigma_v_eff_min` abs `1e-6..1e-9`, `transfer_abs_max` rel `5%`, `transfer_peak_freq_hz` abs `0.5 Hz`, dt-sensitivity `<=5.0` | n/a (native path) | `2026-03-04T00:00:00Z` | Medium | SHAKE/DEEPSOIL external lock pending |
| `opensees-parity` | 6 | dedicated OpenSees parity envelope (`parity01..06`) | explicit locked checks + solver diagnostic constraints + dt-sensitivity gates | policy-managed (`benchmarks/policies/release_signoff.yml:opensees_fingerprint`) | `2026-03-04T00:00:00Z` | Medium | Must be re-confirmed on dedicated release runner before final RC signoff |

Notes:
- UI parity does not increase scientific confidence by itself; confidence is gated by numerical benchmark/parity evidence.
- Confidence tiers can only be raised when reference basis and verification timestamp are updated together.
