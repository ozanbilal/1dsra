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
- SQLite output tables (runs, layers, motions, metrics, spectra, pwp_stats, mesh_slices, artifacts)
- SQLite write path is idempotent for deterministic reruns (run-id scoped rows are replaced)
- Checksum table + run verification commands (`verify`, `verify-batch`) for HDF5/SQLite/meta consistency checks
- `verify` checks extended to effective-stress metrics (`delta_u_max`, `sigma_v_ref`, `sigma_v_eff_min`)
- `verify` now also checks `pwp_effective_stats` table-level consistency vs HDF5
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

- CLI commands: `init`, `validate`, `render-tcl`, `run`, `batch`, `benchmark`, `campaign`, `summarize`, `report`, `dt-check`, `verify`, `verify-batch`, `ui`
- `init` now supports both `effective-stress` and `mkz-gqh-mock` templates
- `init` now supports `effective-stress`, `effective-stress-strict-plus`, and `mkz-gqh-mock` templates
- `benchmark`/`campaign` support direct OpenSees override option: `--opensees-executable`
- `benchmark`/`campaign` support OpenSees readiness enforcement: `--require-opensees` (parity suites fail fast when backend is missing)
- `benchmark`/`campaign` support execution coverage enforcement: `--min-execution-coverage` (ratio gate for executed/non-skipped cases)
- Campaign summaries now carry backend coverage telemetry (`backend_ready`, `skipped_backend`, `execution_coverage`)
- Benchmark reports now include explicit backend skip diagnostics (`backend_missing_cases`, `skip_kind`)
- CLI backend preflight: `validate --check-backend`
- Python SDK entry points: `run_analysis`, `run_batch`, `load_result`, `compute_spectra`, `verify_run`, `verify_batch`
- Streamlit UI with run/benchmark/report controls and plot panels
- Streamlit UI now shows effective-stress metrics/plots (`ru`, `delta_u`, `sigma_v_eff`)
- Streamlit UI includes campaign controls and inline campaign summary rendering
- Streamlit UI includes config preset switch (`effective-stress`, `effective-stress-strict-plus`, `mkz-gqh-mock`)
- Streamlit UI includes `Render Tcl` flow with inline preview and downloadable `model.tcl` / `motion_processed.csv`
- Streamlit UI includes MKZ/GQH curve inspector plots (`G/Gmax`, damping proxy) for config-level sanity checks
- MKZ/GQH helper module (`python/dsra1d/materials/hysteretic.py`) with backbone/reduction utilities
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
