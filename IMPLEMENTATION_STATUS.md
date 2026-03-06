# StrataWave Implementation Status

Last updated: 2026-03-06

## 1. Summary

This file tracks implementation progress against the original v1.0 plan.
Current state is: **core scaffold complete, effective-stress OpenSees adapter functional, production hardening and scientific parity still pending**.

Recent updates (2026-03-05):
- Web convergence/profile health surfaces timeout recovery diagnostics (`timeout_s_configured`, `timeout_s_effective`, `timeout_recovered`, coverage).
- OpenSees backend probe hardened against double-timeout false negatives (`-version` + Tcl fallback timeout now defers final decision to runtime execution).
- Run resolution hardened for partial runs: directories with `run_meta.json` are discoverable even when artifacts are incomplete; data endpoints now report explicit `409 artifacts incomplete` instead of `404 run not found`.
- Web run endpoint now returns normalized `output_root`, and React run flow uses it to keep run-detail fetch root in sync.
- React run-detail fetch path now supports partial rendering: summary/convergence remain visible even if one or more result channels fail (soft warning instead of hard blank-state failure).
- Push CI no longer waits on dedicated OpenSees runner; dedicated parity/signoff gate remains mandatory in `release.yml` and manual parity workflow. `ci.yml` now also uses workflow `concurrency` to auto-cancel superseded queued runs on the same ref.
- Results `Profile` tab now includes a `Profile Atlas` block: stratigraphy bands plus depth-oriented `Vs`, `gamma_max`, and mesh-density plots above the layer table.
- Results `Profile` tab now also includes a `Layer Response Atlas`: depth-oriented `tau_peak`, mobilized-strength ratio, damping proxy, and static overburden proxy plots, plus expanded layer table fields.
- OpenSees Tcl now emits per-layer representative pore-pressure recorders (`layer_<tag>_pwp_raw.out`) in addition to stress/strain recorder channels.
- Web `profile-summary` now reads representative layer `pwp_raw` artifacts and returns per-layer `sigma_v0_mid_kpa`, `ru_max`, `delta_u_max`, and `sigma_v_eff_min`.
- React `Profile` tab now includes an `Effective Stress Atlas` and corresponding table columns for layer-wise effective-stress review.
- Results artifact/download panel now exposes `profile_summary.csv` for direct export of the layer response table.
- Web chart readability improved further: key results, compare, stress-strain, and profile charts now include explicit x/y axis titles.
- Profile gamma-depth rendering now falls back to layer hysteresis strain amplitude when backend-native `gamma_max` channels are unavailable.
- `Results Frame` mode is now a true two-panel studio: left rail for run/artifact/quality navigation and right canvas for the active result tab.

## 2. Phase-by-Phase Status

### Phase 0 - Bootstrap and Repository Skeleton
Status: **Completed**

Implemented:
- Standalone git repo structure under `StrataWave`
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
- Web motion-process path now supports explicit/fallback `dt` handling for one-column motions (prevents implicit `dt=1.0` PSA bias)
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
- OpenSees log diagnostics are now extracted per run (`opensees_diagnostics.json`) and persisted into `run_meta.json`
- OpenSees runtime now uses adaptive timeout budgeting (motion-duration/sample-aware) instead of fixed 180s-only behavior; run metadata includes configured/effective timeout fields
- Timeout-recovery path added: if OpenSees exceeds timeout but required outputs are already complete, pipeline preserves recovered outputs instead of forcing mock overwrite
- Boundary-condition aware TCL assembly:
  - `rigid` base fixity
  - `elastic_halfspace` base with Lysmer-style dashpot (`uniaxialMaterial Viscous` + `zeroLength`)
- Configurable u-p assembly constants in `opensees` config:
  - `column_width_m`, `thickness_m`, `fluid_bulk_modulus`, `fluid_mass_density`, `h_perm`, `v_perm`, `gravity_steps`
- OpenSees u-p stabilization updates applied in generated Tcl:
  - hydraulic conductivity (`h_perm/v_perm`) converted to quadUP permeability coefficients
  - gravity stage uses high temporary permeability and restores target permeability via `parameter/updateParameter`
  - PM4 dynamic-stage `FirstCall` initialization is applied per element/material tag
  - dynamic stage uses step-by-step fallback (`KrylovNewton` -> `ModifiedNewton` + substep retry)
- OpenSees Tcl now emits per-layer representative stress/strain element recorders (`layer_<tag>_stress.out`, `layer_<tag>_strain.out`) for UI hysteresis channels
- OpenSees Tcl now emits per-layer representative pore-pressure recorders (`layer_<tag>_pwp_raw.out`) for depth-wise effective-stress review
- CLI backend preflight check (`validate --check-backend`) for deterministic OpenSees path validation
- OpenSees backend probe hardening: if both `-version` and Tcl fallback probes timeout, probe now reports "assumed available" to avoid false blockers (final authority is runtime execution)
- Optional real-binary integration test harness (`DSRA1D_RUN_OPENSEES_INTEGRATION=1`)

Current level:
- `render_tcl` now emits u-p-style assembly with materials, nodes, `quadUP` elements, BCs, gravity+dynamic stages, and recorders.
- It is calibration-ready scaffold, not yet full benchmark-validated engineering template set.

### Phase 3 - Effective Stress (PM4Sand/PM4Silt)
Status: **Partial (runtime-stable baseline)**

Implemented:
- PM4Sand/PM4Silt command blocks in generated TCL
- Layer-level material parameter plumbing via `material_params`
- Layer-level PM4 positional tail arguments via `material_optional_args` for calibration runs
- Calibration-ready starter templates for PM4 tuning workflows:
  - `pm4sand-calibration`
  - `pm4silt-calibration`
- Example config includes PM4 placeholder calibration parameters
- Effective-stress normalization outputs in result stores:
  - HDF5 `/pwp`: `ru`, `delta_u`, `sigma_v_ref`, `sigma_v_eff`
  - SQLite `metrics`: `delta_u_max`, `sigma_v_ref`, `sigma_v_eff_min`
- PM4 runtime stability hardening in OpenSees assembly:
  - stage-transition `FirstCall` hook for PM4 elements
  - gravity-to-dynamic permeability staging path
  - robust dynamic fallback path without immediate hard abort

Not completed:
- Full parameter coverage and robust validation of PM4 inputs
- Verified physics-level parity against reference OpenSees/DEEPSOIL datasets
- Dissipation model tuning and advanced pore-pressure workflows
- Published-reference calibration for MKZ/GQH nonlinear hysteresis (current native coupling exists)

### Phase 4 - Result Store and Reporting
Status: **Completed (v1 base)**

Implemented:
- HDF5 output (`/time`, `/depth`, `/signals`, `/pwp`, `/spectra`, `/mesh`)
- SQLite output tables (runs, layers, motions, metrics, spectra, transfer_function, pwp_stats, mesh_slices, artifacts)
- EQL output persistence (`/eql` group in HDF5; `eql_summary` + `eql_layers` tables in SQLite)
- Transfer-function outputs now persisted (`/spectra/freq_hz`, `/spectra/transfer_abs`, SQLite `transfer_function`)
- Time-step metadata is persisted (`run_meta.json: dt_s/delta_t_s`, HDF5 `/meta/delta_t_s`)
- Run-level CSV artifacts are now written by pipeline (`surface_acc.csv`, `pwp_effective.csv` with `delta_t_s`)
- Run-level config snapshot is now persisted (`config_snapshot.json`) for deterministic post-processing and UI reconstruction
- SQLite write path is idempotent for deterministic reruns (run-id scoped rows are replaced)
- Checksum table + run verification commands (`verify`, `verify-batch`) for HDF5/SQLite/meta consistency checks
- `verify` checks extended to effective-stress metrics (`delta_u_max`, `sigma_v_ref`, `sigma_v_eff_min`)
- `verify` now also checks `pwp_effective_stats` table-level consistency vs HDF5
- `verify` now checks successful OpenSees runs for command metadata + stdout/stderr artifact/log presence
- `verify-batch` now emits machine-readable policy verdicts (`require_runs`, condition flags, `passed`) including path/directory guards
- HTML/PDF report generation (includes effective-stress KPI summary and additional time-history plots)
- Report/UI PSA path now recomputes spectra from run `surface_acc` + run `dt` instead of relying on stale stored arrays

### Phase 5 - Benchmark and Regression
Status: **Completed (basic) / Partial (scientific depth)**

Implemented:
- `benchmark` command
- Core benchmark suite with multi-case pass/fail output and metric-level tolerance checks
- Added `core-hyst` benchmark suite for MKZ/GQH native nonlinear regression coverage (3-case matrix)
- Added `core-linear` benchmark suite for native linear SH backend coverage (3-case matrix)
- Added `core-eql` benchmark suite for native equivalent-linear backend coverage (3-case matrix)
- `core-linear` golden checks now include transfer-function metrics (`transfer_abs_max`, `transfer_peak_freq_hz`) with deterministic and dt-sensitivity gates
- OpenSees parity suite scaffold (`opensees-parity`) with auto-skip when executable is unavailable
- OpenSees parity suite expanded to 6-case matrix (`parity01`..`parity06`) with explicit-check golden envelopes
- OpenSees parity golden envelopes were re-locked from real-binary local runs (6/6 execution coverage) including transfer metrics (`transfer_abs_max`, `transfer_peak_freq_hz`)
- OpenSees parity constraints now include solver-quality gates from diagnostics (`solver_warning_max`, `solver_failed_converge_max`, `solver_analyze_failed_max`, `solver_divide_by_zero_max`, `solver_dynamic_fallback_failed_max`)
- Strict benchmark policy options (`--fail-on-skip`, `--require-runs`) for CI gating
- Backend fingerprint policy options (`--require-backend-version-regex`, `--require-backend-sha256`) for `validate`, `benchmark`, and `campaign`
- Manual parity workflow (`.github/workflows/opensees-parity.yml`) with executable override input
- Manual parity workflow now also accepts executable extra-args override (`opensees_extra_args`)
- Manual parity workflow now supports backend fingerprint requirements and defaults to 6-run parity target
- New aggregated benchmark suite: `release-signoff` (`core-es` + `core-hyst` + `core-linear` + `core-eql` + `opensees-parity`)
- Release/manual dedicated runner parity gate is non-optional (`self-hosted, linux, x64, opensees`) and executes `release-signoff`
- CI dedicated runner now enforces `summarize --strict-signoff` for machine-readable signoff verdicts
- Parity suite expanded to multi-case set (3 baseline scenarios) for stronger coverage
- Parity suite now distinguishes missing executable vs failed backend probe (`missing_opensees` / `probe_failed`)
- Parity reports now persist backend fingerprint diagnostics (`binary_sha256`, requirements verdict/errors)
- Campaign summary aggregation (`summarize`) for benchmark + verify outputs (`campaign_summary.json/.md`)
- Campaign orchestration command (`campaign`) for benchmark + verify + summarize pipeline
- Golden envelope locking command (`lock-golden`) to generate explicit check matrices from benchmark reports
- Parity workflow now publishes campaign summary into GitHub Step Summary
- Parity suite now treats failed backend probes as backend-unavailable (`skip_kind=probe_failed`) for deterministic gating
- Automated test coverage including TCL generation, parser robustness, fallback behavior
- Added constitutive path-regression tests for native nonlinear MKZ/GQH hysteresis (`reload_factor` sensitivity + loop dissipation)
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
Status: **In progress (mid)**

Missing:
- Final dedicated runner provisioning + operational reliability monitoring (self-hosted agent health/SLA)
- Organization-level sign-off for release gates (release path enforces `release-signoff` + `strict-signoff`)
- Production fingerprint lifecycle process (rotate/update `DSRA1D_CI_OPENSEES_SHA256` and matrix evidence)
- Artifact publishing policy finalization (GitHub release workflow + release tag/version + changelog guards are now added)
- Dedicated OpenSees parity release gate runner provisioning (`self-hosted, linux, x64, opensees`) and secret/variable bootstrap
- User manual completeness and migration notes

## 3. What Is Working Today

- CLI commands: `init`, `validate`, `render-tcl`, `run`, `quickstart`, `batch`, `benchmark`, `campaign`, `summarize`, `lock-golden`, `report`, `dt-check`, `verify`, `verify-batch`, `ui`
- `init` now supports both `effective-stress` and `mkz-gqh-mock` templates
- `init` now supports `effective-stress`, `effective-stress-strict-plus`, `pm4sand-calibration`, `pm4silt-calibration`, `mkz-gqh-mock`, `mkz-gqh-eql`, and `mkz-gqh-nonlinear` templates
- `benchmark`/`campaign` support direct OpenSees override option: `--opensees-executable`
- `run`/`batch`/`dt-check` now support runtime backend override: `--backend config|auto|opensees|mock|linear|eql|nonlinear`
- `--backend auto` now enables OpenSees->mock fallback for immediate analyzable runs when executable is unavailable
- `--backend linear` now enables native linear SH baseline analysis without OpenSees dependency
- `--backend eql` now enables native equivalent-linear (strain-compatible MKZ/GQH iteration) analysis without OpenSees dependency
- `--backend nonlinear` now enables native MKZ/GQH stateful hysteretic time-domain analysis without OpenSees dependency
- EQL convergence diagnostics are now stored and verifiable across HDF5/SQLite/report outputs
- `quickstart` command now creates a self-contained sample case, runs analysis, and writes `quickstart_summary.json`
- `benchmark`/`campaign` support OpenSees readiness enforcement: `--require-opensees` (parity suites fail fast when backend is missing)
- `benchmark`/`campaign` support execution coverage enforcement: `--min-execution-coverage` (ratio gate for executed/non-skipped cases)
- `benchmark`/`campaign` support explicit-checks enforcement: `--require-explicit-checks` (parity envelopes must be explicitly locked)
- Campaign summaries now carry backend coverage telemetry (`backend_ready`, `skipped_backend`, `execution_coverage`)
- Benchmark reports now include explicit backend skip diagnostics (`backend_missing_cases`, `skip_kind`)
- Release/manual parity workflow gates enforce full coverage (`--min-execution-coverage 1.0`)
- `release-signoff` suite now aggregates all critical suites into one parity-first gate
- Dedicated OpenSees parity gate is mandatory in release/manual parity workflows (`self-hosted, linux, x64, opensees`)
- Release workflow now enforces strict signoff + machine-check checklist (`check_release_signoff.py`)
- Release machine-check now enforces exact SHA-256 parity: matrix `opensees-parity.binary_fingerprint` must match signoff observed backend fingerprint
- Strict signoff now also enforces `backend_probe_not_assumed` (probe timeout-assumption is treated as release blocker)
- Release/manual dedicated runner gates now run `scripts/check_fingerprint_alignment.py` so CI variable, policy fingerprint, and matrix fingerprint must match before parity execution
- CI/release workflows now run `scripts/check_release_policy_consistency.py` to prevent `release_signoff.yml` drift from benchmark suite/case matrix
- Campaign summary now includes machine-readable policy verdicts (`policy.benchmark`, `policy.verify_batch`, `policy.campaign`)
- Verify policy metadata is now preserved/merged across CLI/UI campaign outputs and propagated in summary conditions
- CLI backend preflight: `validate --check-backend` (path + lightweight `-version` probe output)
- Parity benchmark reports now include `backend_probe` diagnostics (`requested`, `resolved`, `available`, `version`)
- OpenSees override env now supports executable extra args (`DSRA1D_OPENSEES_EXTRA_ARGS_OVERRIDE`)
- Python SDK entry points: `run_analysis`, `run_batch`, `load_result`, `compute_spectra`, `verify_run`, `verify_batch`
- Streamlit UI with run/benchmark/report controls and plot panels
- Streamlit UI now shows effective-stress metrics/plots (`ru`, `delta_u`, `sigma_v_eff`)
- Streamlit UI now shows transfer-function visualization (`|H(f)|`) when available
- Streamlit UI includes campaign controls and inline campaign summary rendering
- Streamlit UI includes config preset switch (`effective-stress`, `effective-stress-strict-plus`, `mkz-gqh-mock`, `mkz-gqh-eql`, `mkz-gqh-nonlinear`)
- Streamlit UI run panel includes backend mode selector (`config/auto/opensees/mock/linear/eql/nonlinear`) and run-level OpenSees executable override
- Streamlit UI now visualizes transfer function (`|H(f)|`) for runs with stored spectral ratio outputs
- Streamlit UI includes `Render Tcl` flow with inline preview and downloadable `model.tcl` / `motion_processed.csv`
- Streamlit UI includes MKZ/GQH curve inspector plots (`G/Gmax`, damping proxy) for config-level sanity checks
- Streamlit UI MKZ/GQH inspector now includes Masing-style hysteresis loop preview and per-layer loop energy proxy
- FastAPI + React migration starter is now available (`StrataWave web`) with API-backed run listing, signal fetch, `surface_acc.csv` and `pwp-effective.csv` downloads
- FastAPI dashboard upgraded with run-detail cards and multi-chart views (surface acc, PSA, transfer, ru, `delta_u`, `sigma_v_eff`) plus artifact downloads (`surface_acc.csv`, `pwp_effective.csv`, `surface_acc.out`, `results.h5`, `results.sqlite`, `run_meta.json`)
- React dashboard now includes a dedicated `Results Frame` focus mode so outputs can be reviewed in a full-width workspace (without Wizard/Runs crowding)
- `Results Frame` focus mode now uses a split studio layout instead of stacking all diagnostic cards above the plots
- Wizard `Damping` step is now solver-routed:
  - `rayleigh` mode writes `analysis.damping_mode`, `rayleigh_mode_1_hz`, `rayleigh_mode_2_hz`, `rayleigh_update_matrix`
  - native linear/eql/nonlinear backends now consume Rayleigh damping in runtime
- Results `Convergence` tab now includes OpenSees log-derived diagnostics for non-EQL runs (warning/divergence counters and severity)
- Results `Convergence` tab upgraded from raw JSON view to structured diagnostics cards + severity badge (EQL and OpenSees modes)
- Results `Convergence` and profile health cards now surface OpenSees timeout diagnostics/recovery metadata (`timeout_s_configured`, `timeout_s_effective`, `timeout_recovered`, coverage) even when log-level diagnostics are absent
- Results `Profile` tab now surfaces a compact solver-health snapshot (severity + key diagnostics) for faster run triage
- Results `Profile` tab now includes visual depth summaries (`Profile Atlas`) in addition to the layer table for faster engineering review
- Results `Profile` tab now includes a second visual `Layer Response Atlas` for depth-based stress/strength diagnostics (`tau_peak`, mobilized ratio, damping proxy, static overburden proxy)
- Results `Profile` tab now includes an `Effective Stress Atlas` for depth-based `ru_max`, `delta_u_max`, and `sigma'_v,min` review from representative layer pore-pressure recorders
- Runs list and run-tree now surface health severity at-a-glance (`convergence_mode` / `convergence_severity`) via API-backed chips
- Results workspace now includes `Parity Health` and `Scientific Confidence` cards for release-readiness visibility
- Results workspace now includes API-backed `Release Blockers` panel (go/no-go + blocker/warning list from parity/science/signoff/runtime diagnostics)
- `/api/runs` now includes solver diagnostic counters (`warning`, `failed_converge`, `analyze_failed`, `divide_by_zero`, `dynamic_fallback_failed`) for pre-detail triage
- Run-detail fetch path now retries with run-specific output-root parent to reduce cross-root `Run not found` failures in UI
- Run discovery/resolution is now recursive under `output_root` (nested campaign folders supported), and run detail endpoints now resolve run-id from parent roots instead of requiring direct run-folder root
- New wizard readiness API (`POST /api/wizard/sanity-check`) provides blocker/warning diagnostics before run (motion path, dt/f_max, backend probe, config/material compatibility)
- Wizard sanity-check now includes OpenSees timeout budget diagnostics (`timeout_budget`) with recommended timeout warning for long motions
- Step-5 now includes a `Run Sanity Check` action and structured readiness result cards
- Step-5 `Run Now` now supports single-click execution by auto-generating config (if missing) and enforcing sanity-check blockers before launch
- New profile summary API (`GET /api/runs/{run_id}/results/profile-summary`) and Profile tab layer table (depth bounds, sublayer count, `gamma_max` when available)
- Runtime backend resolver now handles `backend=config|auto` with `config.solver_backend=auto` deterministically (OpenSees if available, else mock fallback)
- CI reliability: fixed Python 3.12 mypy strict-typing break in web profile-summary model field aliasing
- Web chart UX: chart cards now render numeric axes/ticks + gridlines for direct value reading in UI
- Web API `signals` payload now includes `dt_s` / `delta_t_s` (and alias `delta_t`) for frontend consumers
- Web UI now includes DEEPSOIL-style 5-step wizard (`Analysis Type -> Soil Profile -> Input Motion -> Damping -> Analysis Control`)
- Wizard schema now exposes template catalog + per-template defaults, and React UI supports one-click template apply in Analysis step (including PM4 calibration templates)
- React wizard now includes step-level readiness indicators (`ready`/`issue` badges), inline step issue list, and gated `Generate Config` / `Run Now` actions based on required inputs
- React Motion step now supports direct file uploads (CSV and AT2) without manual filesystem path entry
- Results panel now supports multi-run overlay comparison (surface acceleration, PSA, transfer `|H(f)|`)
- Multi-run compare now includes reference-based diagnostics (`PSA ratio`, transfer/surface `Δ`, `ΔPGA`/PGA ratio)
- Web API now includes backend readiness probe endpoint (`/api/backend/opensees/probe`) used by wizard run diagnostics
- Backend probe payload now includes `assumed_available`; UI/CLI render this as warning when probe timed out and availability was inferred
- Backend probe payload now includes executable-source diagnostics (`requested_input`, env override value/used) to debug path override issues
- Web API now includes wizard/motion orchestration endpoints (`/api/wizard/schema`, `/api/config/from-wizard`, `/api/motion/import/peer-at2`, `/api/motion/process`, `/api/runs/tree`, `/api/runs/{run_id}/results/summary`)
- Web API now includes parity/science visibility endpoints (`/api/parity/latest`, `/api/science/confidence`)
- Web API now includes release signoff visibility endpoint (`/api/release/signoff/latest`) with normalized go/no-go fields (`release_ready`, coverage/runs, fingerprint match, blocker categories, severity score/label)
- React motion tools now support CSV + PEER AT2 import, baseline processing (`deepsoil_bap_like` included), scaling, and preview plots (acc/PSA/FAS ratio)
- Motion wizard now keeps imported/processed motion units in `m/s2` and exposes optional `dt override` input to reduce PSA preprocessing errors
- Web API now exposes layer-wise hysteresis/mobilized payload (`/api/runs/{run_id}/results/hysteresis`) using stored config snapshots with sqlite fallback
- React Results tabs `Stress-Strain` and `Mobilized Strength` now render backend data (layer selector, loop plot, mobilized ratio/energy charts) instead of static placeholders
- React Soil Profile step now includes per-layer `material_params` and `material_optional_args` editors with material-aware default parameter sets (PM4Sand/PM4Silt/MKZ/GQH/elastic)
- React Soil Profile step now includes layer utility actions: `duplicate`, `up/down reorder`, and `CSV import/export` for full layer-stack editing without YAML
- React Soil Profile step now supports DEEPSOIL-style table editing mode (Table/Cards switch) plus `Auto Profile Build` (f_max, points-per-wavelength, minimum slice thickness, max sublayers per main layer)
- React Soil Profile step now includes starter profile builders (`5-Layer Starter` quick action and preset loader)
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
- Dedicated runner parity gate configured in release/manual parity workflows; runner availability and secret/var provisioning remain environment-dependent
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

## 5A. Immediate Critical Path (Next Phase Execution Order)

1. **Real OpenSees parity closure:** Run full `opensees-parity` (6/6 executed, no skip) on dedicated runner and lock final explicit envelopes.
2. **Scientific envelope hardening:** Expand `SCIENTIFIC_CONFIDENCE_MATRIX.md` with published/reference-mapped tolerances per scenario class.
3. **PM4 calibration templates:** Publish and freeze calibration-ready PM4Sand/PM4Silt template set with documented parameter defaults/ranges.
4. **UI production transition:** Continue React/FastAPI path (keep Streamlit as engineering panel), and complete artifact + diagnostics UX parity.
5. **Release gate finalization:** Enforce parity policy in release path as non-bypassable and finalize release checklist/sign-off flow.

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
| Nonlinear total-stress MKZ/GQH native coupling | Partial | Native time-domain solver now includes stateful branch tracking and runs MKZ/GQH profiles without mock dependency | Add published-reference calibration and stronger constitutive verification envelopes |
| Masing/non-Masing production hysteresis rules | Partial | Time-stepping constitutive update now supports generalized reload factor (`reload_factor`, Masing/non-Masing approximation) | Extend with advanced path-dependence checks and reference loop matching |
| Small-strain damping package (freq-independent + Rayleigh) | Pending | Not yet implemented as solver damping module | Design/implement damping module with tests |
| Linear native solver (time/frequency domain) | Partial | Python native linear SH backend (lumped shear-beam + Newmark) is now available via `--backend linear` | Add frequency-domain transfer-function mode and broader validation tests |
| EQL solver (SHAKE-like + deconv/conv) | Partial | Native time-domain strain-compatible EQL backend (`solver_backend: eql`) is implemented with iterative MKZ/GQH modulus+damping updates and convergence tracking | Add frequency-domain deconvolution/convolution mode and published-reference validation |
| f_max-driven auto sublayering / mesh controls | Partial | Element slicing logic exists in OpenSees TCL path; Web UI now has `Auto Profile Build` for interactive profile slicing from main layers | Expose shared mesh service/API across all backends and add randomization options |
| Result store (HDF5 + SQLite) | Done | Implemented with deterministic run-id consistency checks | Add optional DuckDB/Parquet query utilities |
| CLI coverage (`run/batch/benchmark/campaign/verify/report/ui`) | Done | End-to-end command set available | Maintain backward compatibility and docs |
| Python SDK stable entry points | Done | `run_analysis`, `run_batch`, `load_result`, `compute_spectra` | Add examples for calibration and campaign automation |
| GUI capability (engineering monitoring UI) | Partial | Streamlit UI available with run/campaign/plots/TCL preview | Decide whether to keep Streamlit or move to full product UI |
| Benchmark + regression framework | Partial | `core-es`, `core-hyst`, `core-linear`, `core-eql`, `opensees-parity`, policy gates | Expand with published reference sets and stricter tolerances |
| Scientific parity against DEEPSOIL/OpenSees references | Pending | Scaffold and policy telemetry exist; no full parity qualification | Build full parity matrix and acceptance envelopes |
| Real-binary OpenSees integration validation | Partial | Optional integration harness + dedicated release/manual parity gates with backend fingerprint policy hooks | Run and lock final parity envelopes on dedicated runner with production OpenSees binary |
| Deterministic reproducibility (hash/checksum/policy) | Done | Checksums, verify commands, campaign policies, stable run-id | Add release-level reproducibility checklist |
| Release hardening and governance | Partial | Release/tag/changelog guards added | Finalize org sign-off, manuals, and artifact policy |
| Native effective-stress solver beyond OpenSees interop | Out-of-v1 | Explicitly deferred | Start after linear/EQL native milestones |

Tracking rule for continuation:
- When a `Partial`/`Pending` item advances, update both this matrix and the corresponding phase section above in the same commit.

## 7A. DEEPSOIL UI Parity Backlog

| Wave-1 (zorunlu) | Durum | Wave-2 (sonraki) | Durum |
|---|---|---|---|
| 5-step wizard state + config üretimi | Done | Auto-profile advanced heuristics (Vs gradient + curve-aware slicing) | Pending |
| Motion import (`CSV`, `PEER AT2`) | Done | Thickness/Vs/dynamic curve randomization UI | Pending |
| Baseline pipeline opsiyonları (`deepsoil_bap_like` dahil) | Done | Genişletilmiş database browser parity | Pending |
| Scale by / scale to PGA | Done | Multi-profile random batch scenario editor | Pending |
| Soil Profile tablo/kart editörü + katman yardımcıları (duplicate/reorder/CSV) | Done | Bulk layer templates library (regional presets) | Pending |
| Auto Profile Builder (`f_max`, points/wavelength, min slice, max sublayers) | Done | Stochastic/randomized auto-profile realizations | Pending |
| Results tab yapısı (`Time Histories`, `Spectral`, `Profile`, `Convergence`) | Partial | Advanced mobilized strength and convergence diagnostics parity | Pending |
| Run tree (`project -> motion -> run`) | Done | DEEPSOIL-style batch navigator parity (full) | Pending |

Notes:
- Wave-1 UI parity is orchestration-focused; numerik çekirdek değişiklikleri bu dalgada hedeflenmez.
- `Stress-Strain` ve `Mobilized Strength` tabları mevcut, fakat detay veri kanalı için ek recorder/çıktı şeması gereklidir.

## 8. Scientific Confidence Matrix

- Single source of truth: [SCIENTIFIC_CONFIDENCE_MATRIX.md](SCIENTIFIC_CONFIDENCE_MATRIX.md)
- Update rule: when benchmark tolerances/reference-basis change, update confidence matrix in the same commit.
- Release rule: `opensees-parity.binary_fingerprint` must match both policy fingerprint (`benchmarks/policies/release_signoff.yml`) and strict-signoff observed backend SHA256.

