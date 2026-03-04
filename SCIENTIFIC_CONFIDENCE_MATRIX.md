# Scientific Confidence Matrix

Last updated: 2026-03-04

This matrix tracks confidence by benchmark suite and reference basis.
It is the single table used for release sign-off discussions.

| Suite | Case Count | Reference Basis | Metrics & Tolerances (Current) | Published/Reference Alignment | Confidence |
|---|---:|---|---|---|---|
| `core-es` | 3 | Internal golden envelope (effective-stress pipeline) | `pga` abs `1e-6`, `ru_max` abs `1e-9`, `delta_u_max` abs `1e-9`, `sigma_v_eff_min` abs `1e-9`, dt-sensitivity threshold `5.0` | No published dataset lock yet | Medium |
| `core-hyst` | 3 | Internal MKZ/GQH nonlinear regression envelope | `pga` abs `1e-6`, `ru_max` abs `1e-8`, `delta_u_max` abs `1e-8`, `sigma_v_eff_min` abs `1e-6`, dt-sensitivity threshold `5.0` | No published dataset lock yet | Medium |
| `core-linear` | 3 | Internal linear SH regression + transfer response checks | `pga/ru/delta_u/sigma_v_eff_min` abs `1e-6`..`1e-9`, `transfer_abs_max` rel `5%`, `transfer_peak_freq_hz` abs `0.5 Hz`, dt-sensitivity `5.0` | Partially physics-grounded, not yet external publication lock | Medium-High |
| `core-eql` | 3 | Internal EQL regression envelope + convergence persistence | `pga/ru/delta_u/sigma_v_eff_min` abs `1e-6`..`1e-9`, `transfer_abs_max` rel `5%`, `transfer_peak_freq_hz` abs `0.5 Hz`, dt-sensitivity `5.0` | No published SHAKE/DEEPSOIL lock yet | Medium |
| `opensees-parity` | 6 | OpenSees backend parity suite (dedicated real-binary runner required) | Explicit-check schema enforced; current tolerances are intentionally broad placeholders pending final lock with production binary | Published/reference parity lock **in progress** (pending final envelope freeze); PM4 runtime convergence hardening applied (`FirstCall` + permeability staging) | Low-Medium (rising after lock) |

Notes:
- “Published/reference alignment” means comparison against external references (published studies, official example sets, or locked real-binary parity envelopes).
- After dedicated runner lock, update `opensees-parity` tolerances from broad placeholders to measured envelopes and raise confidence tier.
- UI parity note: React/FastAPI wizard and motion tools only orchestrate config/motion/run flow; scientific confidence remains gated by numerical backend benchmarks and parity suites, not by UI layer behavior alone.
