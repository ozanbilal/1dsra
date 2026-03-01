# 1DSRA Implementation Status

Last updated: 2026-03-01

## 1. Summary

This file tracks implementation progress against the original v1.0 plan.
Current state is: **core scaffold complete, effective-stress OpenSees adapter in advanced scaffold stage, production hardening still pending**.

## 2. Phase-by-Phase Status

### Phase 0 - Bootstrap and Repository Skeleton
Status: **Completed**

Implemented:
- Standalone git repo structure under `1DSRA`
- Packaging (`pyproject.toml`), license, README
- CI workflow (`.github/workflows/ci.yml`)
- Developer quality gates (`ruff`, `mypy`, `pytest`, pre-commit)
- Docker scaffolding

### Phase 1 - Schema, I/O, Motion Processing
Status: **Completed (v1 scope)**

Implemented:
- Pydantic config schema (`ProjectConfig`, profile, analysis, motion, output, opensees)
- YAML/JSON config load + template writer
- Motion load and preprocessing (baseline correction, scale modes)
- Material-level parameter validation for PM4Sand/PM4Silt/elastic (`material_params`)
- Material-level parameter validation for MKZ/GQH (required params + damping bounds)
- Backend-aware validation: OpenSees runs now require PM4 mandatory parameter sets per layer
- Backend-aware guard: OpenSees backend rejects MKZ/GQH in v1 pipeline
- PM4 validation profiles: `basic` and `strict` (strict adds conservative range checks)
- PM4 validation profiles: `basic`, `strict`, and `strict_plus` (`strict_plus` adds u-p setup sanity checks for OpenSees)
- `strict_plus` validation tightened: PM4-only layer stacks and permeability anisotropy ratio bounds (`h_perm/v_perm`)
- Motion unit validation + conversion to SI (`m/s2`) for consistent downstream calculations

Notes:
- Input validation works for current config model.
- Extended schema (full PM4 calibration catalog, richer constraints) is still pending.

### Phase 2 - OpenSees Adapter Core
Status: **Completed (functional) / Partial (production depth)**

Implemented:
- TCL generation from config
- OpenSees subprocess runner with timeout/error handling
- Retries and fallback behavior
- Parser support for recorder formats (1-column and 2-column time series)
- Structured OpenSees artifact logging (`run_meta.json`, stdout/stderr logs, SQLite `artifacts`)
- Boundary-condition aware TCL assembly:
  - `rigid` base fixity
  - `elastic_halfspace` base with Lysmer-style dashpot (`uniaxialMaterial Viscous` + `zeroLength`)
- Configurable u-p assembly constants in `opensees` config:
  - `column_width_m`, `thickness_m`, `fluid_bulk_modulus`, `fluid_mass_density`, `h_perm`, `v_perm`, `gravity_steps`
- CLI backend preflight check (`validate --check-backend`) for deterministic OpenSees path validation
- Optional real-binary integration test harness (`DSRA1D_RUN_OPENSEES_INTEGRATION=1`)

Current level:
- `render_tcl` now emits u-p-style assembly with materials, nodes, `quadUP` elements, BCs, gravity+dynamic stages, and recorders.
- It is calibration-ready scaffold, not yet full benchmark-validated engineering template set.

### Phase 3 - Effective Stress (PM4Sand/PM4Silt)
Status: **Partial**

Implemented:
- PM4Sand/PM4Silt command blocks in generated TCL
- Layer-level material parameter plumbing via `material_params`
- Layer-level PM4 positional tail arguments via `material_optional_args` for calibration runs
- Example config includes PM4 placeholder calibration parameters
- Effective-stress normalization outputs in result stores:
  - HDF5 `/pwp`: `ru`, `delta_u`, `sigma_v_ref`, `sigma_v_eff`
  - SQLite `metrics`: `delta_u_max`, `sigma_v_ref`, `sigma_v_eff_min`

Not completed:
- Full parameter coverage and robust validation of PM4 inputs
- Verified physics-level parity against reference OpenSees/DEEPSOIL datasets
- Dissipation model tuning and advanced pore-pressure workflows
- MKZ/GQH native nonlinear solver coupling (currently helper/backbone + mock proxy only)

### Phase 4 - Result Store and Reporting
Status: **Completed (v1 base)**

Implemented:
- HDF5 output (`/time`, `/depth`, `/signals`, `/pwp`, `/spectra`, `/mesh`)
- SQLite output tables (runs, layers, motions, metrics, spectra, transfer_function, pwp_stats, mesh_slices, artifacts)
- Transfer-function outputs now persisted (`/spectra/freq_hz`, `/spectra/transfer_abs`, SQLite `transfer_function`)
- SQLite write path is idempotent for deterministic reruns (run-id scoped rows are replaced)
- Checksum table + run verification commands (`verify`, `verify-batch`) for HDF5/SQLite/meta consistency checks
- `verify` checks extended to effective-stress metrics (`delta_u_max`, `sigma_v_ref`, `sigma_v_eff_min`)
- `verify` now also checks `pwp_effective_stats` table-level consistency vs HDF5
- `verify-batch` now emits machine-readable policy verdicts (`require_runs`, condition flags, `passed`) including path/directory guards
- HTML/PDF report generation (includes effective-stress KPI summary and additional time-history plots)

### Phase 5 - Benchmark and Regression
Status: **Completed (basic) / Partial (scientific depth)**

Implemented:
- `benchmark` command
- Core benchmark suite with multi-case pass/fail output and metric-level tolerance checks
- Added `core-hyst` benchmark suite for MKZ/GQH mock regression coverage (3-case matrix)
- OpenSees parity suite scaffold (`opensees-parity`) with auto-skip when executable is unavailable
- Strict benchmark policy options (`--fail-on-skip`, `--require-runs`) for CI gating
- Manual parity workflow (`.github/workflows/opensees-parity.yml`) with executable override input
- Parity suite expanded to multi-case set (3 baseline scenarios) for stronger coverage
- Campaign summary aggregation (`summarize`) for benchmark + verify outputs (`campaign_summary.json/.md`)
- Campaign orchestration command (`campaign`) for benchmark + verify + summarize pipeline
- Parity workflow now publishes campaign summary into GitHub Step Summary
- Automated test coverage including TCL generation, parser robustness, fallback behavior
- Time-step sensitivity utility command (`dt-check`) for Δt vs Δt/2 comparison
- Additional benchmark guards:
  - physical ru bounds checks
  - ru monotonicity option and lower-bound checks for `delta_u` / `sigma_v_eff`
  - PGA min/max guard checks
  - deterministic repeat-signature checks
  - effective-stress metric checks (`delta_u_max`, `sigma_v_eff_min`)
  - varied case matrix (`pm4sand`, `pm4silt`, mixed profile + scaling modes)
  - optional per-case Δt vs Δt/2 PSA sensitivity checks
- Batch runner now deduplicates identical motions to prevent output collisions and redundant runs

Not completed:
- Broad benchmark library (multiple soil profiles, strong-motion sets, edge cases)
- Strict published reference matching (DEEPSOIL/OpenSees parity matrix)

### Phase 6 - v1.0 Hardening and Release
Status: **In progress (early)**

Missing:
- Release process execution policy (tagging rules/checklist) still needs final sign-off
- Artifact publishing policy finalization (GitHub release workflow + release tag/version + changelog guards are now added)
- Organization-level sign-off for release gates (CI/release now enforce `core-es` + `core-hyst` campaign gates)
- User manual completeness and migration notes

## 3. What Is Working Today

- CLI commands: `init`, `validate`, `render-tcl`, `run`, `quickstart`, `batch`, `benchmark`, `campaign`, `summarize`, `report`, `dt-check`, `verify`, `verify-batch`, `ui`
- `init` now supports both `effective-stress` and `mkz-gqh-mock` templates
- `init` now supports `effective-stress`, `effective-stress-strict-plus`, and `mkz-gqh-mock` templates
- `benchmark`/`campaign` support direct OpenSees override option: `--opensees-executable`
- `run`/`batch`/`dt-check` now support runtime backend override: `--backend config|auto|opensees|mock|linear`
- `--backend auto` now enables OpenSees->mock fallback for immediate analyzable runs when executable is unavailable
- `--backend linear` now enables native linear SH baseline analysis without OpenSees dependency
- `quickstart` command now creates a self-contained sample case, runs analysis, and writes `quickstart_summary.json`
- `benchmark`/`campaign` support OpenSees readiness enforcement: `--require-opensees` (parity suites fail fast when backend is missing)
- `benchmark`/`campaign` support execution coverage enforcement: `--min-execution-coverage` (ratio gate for executed/non-skipped cases)
- Campaign summaries now carry backend coverage telemetry (`backend_ready`, `skipped_backend`, `execution_coverage`)
- Benchmark reports now include explicit backend skip diagnostics (`backend_missing_cases`, `skip_kind`)
- CI/release workflow campaign gates now enforce full coverage (`--min-execution-coverage 1.0`)
- Campaign summary now includes machine-readable policy verdicts (`policy.benchmark`, `policy.verify_batch`, `policy.campaign`)
- Verify policy metadata is now preserved/merged across CLI/UI campaign outputs and propagated in summary conditions
- CLI backend preflight: `validate --check-backend`
- Python SDK entry points: `run_analysis`, `run_batch`, `load_result`, `compute_spectra`, `verify_run`, `verify_batch`
- Streamlit UI with run/benchmark/report controls and plot panels
- Streamlit UI now shows effective-stress metrics/plots (`ru`, `delta_u`, `sigma_v_eff`)
- Streamlit UI now shows transfer-function visualization (`|H(f)|`) when available
- Streamlit UI includes campaign controls and inline campaign summary rendering
- Streamlit UI includes config preset switch (`effective-stress`, `effective-stress-strict-plus`, `mkz-gqh-mock`)
- Streamlit UI run panel includes backend mode selector (`config/auto/opensees/mock/linear`) and run-level OpenSees executable override
- Streamlit UI now visualizes transfer function (`|H(f)|`) for runs with stored spectral ratio outputs
- Streamlit UI includes `Render Tcl` flow with inline preview and downloadable `model.tcl` / `motion_processed.csv`
- Streamlit UI includes MKZ/GQH curve inspector plots (`G/Gmax`, damping proxy) for config-level sanity checks
- Streamlit UI MKZ/GQH inspector now includes Masing-style hysteresis loop preview and per-layer loop energy proxy
- MKZ/GQH helper module (`python/dsra1d/materials/hysteretic.py`) with backbone/reduction utilities
- MKZ/GQH helper module now includes `generate_masing_loop` for calibration-oriented loop generation
- Mock backend now uses layer-material-aware proxy behavior for MKZ/GQH campaigns
- OpenSees TCL generator with boundary-specific base handling (`rigid` / `elastic_halfspace`)
- Version synchronization guard (`pyproject.toml`, `python/dsra1d/__init__.py`, `core/src/version.cpp`) + `scripts/release_bump.py`
- Release tag/version consistency guard (`scripts/check_release_tag.py`, release workflow integration)
- Release changelog guard (`scripts/check_changelog.py`, release workflow integration)
- Stable run-id generation now hashes full config payload + motion series digest
- Quality gate currently green in local runs:
  - `ruff check .`
  - `mypy python`
  - `pytest` (currently passing)

## 4. What Is Not Yet Production-Ready

- No confirmed OpenSees binary execution in this environment (binary not present at runtime checks)
- No full scientific validation campaign for PM4 calibration fidelity
- No formal acceptance thresholds for all engineering KPIs across scenario matrix
- Native solver path (`core/` C++ runtime) is scaffold-only

## 5. Recommended Next Development Steps

Priority 1:
- Run real OpenSees binary integration tests on a machine with OpenSees installed.
- Lock a validated TCL template family for PM4Sand and PM4Silt (document required parameters).

Priority 2:
- Expand benchmark suite with published/reference scenarios and stricter tolerances.
- Add scenario-specific assertions for boundary behavior and pore-pressure evolution under strong motions.

Priority 3:
- Add config-level validation profiles for PM4 parameter ranges and compatibility checks.
- Complete release automation details (changelog discipline + tagged build policy + artifact publication controls).

Priority 4:
- Start native solver roadmap (linear/EQL first), while preserving OpenSees interop mode.

## 6. Quick Milestone Estimate From Current State

- To "engineering beta" (real OpenSees validated templates + extended benchmark): short-to-medium effort.
- To "v1.0 release candidate" (hardening, docs, release automation): medium effort.
- To "native effective-stress solver beyond OpenSees adapter": major follow-on phase.

## 7. Deep Research Traceability Matrix

This section maps `deep-research-report.md` scope items to current implementation state.
Use it as the single backlog bridge once current v1 hardening tasks are completed.

Status legend:
- `Done`: implemented in repo and covered in tests/flows.
- `Partial`: implemented scaffold or subset only.
- `Pending`: planned but not implemented yet.
- `Out-of-v1`: intentionally deferred beyond current delivery scope.

| Deep-Research Workstream | Status | Current Coverage | Next Action |
|---|---|---|---|
| 1D SH effective-stress workflow via OpenSees adapter | Done | u-p style TCL generation, run orchestration, parsing, artifacts | Keep parity checks in CI and validate with real binaries |
| Boundary conditions (`rigid`, `elastic_halfspace` + dashpot) | Done | Both modes available in TCL generator | Add stronger scenario assertions in parity suite |
| Motion preprocessing (baseline/scaling/unit normalization) | Done | Motion load/preprocess and unit conversion in pipeline | Add advanced filters (optional) as separate enhancement |
| Config schema + validation (`ProjectConfig` family) | Done | Pydantic schema, backend-aware checks, PM4 strict profiles | Extend with richer calibration catalogs |
| PM4Sand support for effective-stress runs | Partial | Parameterized material blocks and strict validation profiles | Complete parameter coverage and reference-calibrated templates |
| PM4Silt support for effective-stress runs | Partial | Material blocks, params, and strict_plus profile checks | Add deeper PM4Silt benchmark/validation matrix |
| PWP output normalization (`ru`, `delta_u`, `sigma_v_eff`) | Done | Stored in HDF5/SQLite + verified in `verify` checks | Add richer depth-dependent diagnostics |
| PWP model family (Dobry/Matasovic/GMP/Park-Ahn etc.) | Pending | Not implemented as native model family | Implement first simplified model + dissipation strategy |
| Nonlinear total-stress MKZ/GQH native coupling | Partial | MKZ/GQH helpers, curve inspector, Masing loop preview | Integrate into native solver path (not only mock/proxy) |
| Masing/non-Masing production hysteresis rules | Partial | Masing-style loop generation helper exists | Add time-stepping constitutive update and non-Masing option |
| Small-strain damping package (freq-independent + Rayleigh) | Pending | Not yet implemented as solver damping module | Design/implement damping module with tests |
| Linear native solver (time/frequency domain) | Partial | Python native linear SH backend (lumped shear-beam + Newmark) is now available via `--backend linear` | Add frequency-domain transfer-function mode and broader validation tests |
| EQL solver (SHAKE-like + deconv/conv) | Pending | Not implemented | Implement iterative EQL and convergence diagnostics |
| f_max-driven auto sublayering / mesh controls | Partial | Element slicing logic exists in OpenSees TCL path | Expose as common mesh service across backends |
| Result store (HDF5 + SQLite) | Done | Implemented with deterministic run-id consistency checks | Add optional DuckDB/Parquet query utilities |
| CLI coverage (`run/batch/benchmark/campaign/verify/report/ui`) | Done | End-to-end command set available | Maintain backward compatibility and docs |
| Python SDK stable entry points | Done | `run_analysis`, `run_batch`, `load_result`, `compute_spectra` | Add examples for calibration and campaign automation |
| GUI capability (engineering monitoring UI) | Partial | Streamlit UI available with run/campaign/plots/TCL preview | Decide whether to keep Streamlit or move to full product UI |
| Benchmark + regression framework | Partial | `core-es`, `core-hyst`, `opensees-parity`, policy gates | Expand with published reference sets and stricter tolerances |
| Scientific parity against DEEPSOIL/OpenSees references | Pending | Scaffold and policy telemetry exist; no full parity qualification | Build full parity matrix and acceptance envelopes |
| Real-binary OpenSees integration validation | Partial | Optional integration harness exists | Run and lock on machine/CI runner with installed OpenSees |
| Deterministic reproducibility (hash/checksum/policy) | Done | Checksums, verify commands, campaign policies, stable run-id | Add release-level reproducibility checklist |
| Release hardening and governance | Partial | Release/tag/changelog guards added | Finalize org sign-off, manuals, and artifact policy |
| Native effective-stress solver beyond OpenSees interop | Out-of-v1 | Explicitly deferred | Start after linear/EQL native milestones |

Tracking rule for continuation:
- When a `Partial`/`Pending` item advances, update both this matrix and the corresponding phase section above in the same commit.
