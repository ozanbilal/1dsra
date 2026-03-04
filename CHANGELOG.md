# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- Initial StrataWave v1 scaffold with:
  - CLI + Python SDK workflows
  - OpenSees adapter for effective-stress runs
  - HDF5 + SQLite result stores
  - Benchmark/regression framework and release scaffolding
- Visual config editor in Streamlit UI:
  - Layer/material parameter form editing
  - In-place config validation and file save
  - Starter-case bootstrap helpers for faster first analysis
- Backend fingerprint policy support:
  - version-regex and sha256 requirements in validate/benchmark/campaign
  - parity reporting includes backend fingerprint diagnostics
- Dedicated release/CI parity gates hardened for 6-case OpenSees parity workflow.
- FastAPI + React migration starter:
  - `StrataWave web` command (uvicorn-backed)
  - API endpoints for run listing, signal fetch, run execution, and `surface_acc.csv` download
  - first production-path dashboard under `python/dsra1d/web/static`
  - expanded run-detail dashboard cards: surface/PSA/transfer/ru/`delta_u`/`sigma_v_eff` charts + artifact downloads
- Streamlit run output export buttons:
  - `surface_acc.csv`, `surface_acc.out`, and `results.h5`
- Run artifact enrichment for time-step traceability:
  - `surface_acc.csv` now includes `delta_t_s`
  - `pwp_effective.csv` artifact added with `time_s,ru,delta_u,sigma_v_eff,delta_t_s`
  - `run_meta.json` now includes `delta_t_s`
  - HDF5 now includes `/meta/delta_t_s`
- Web API enhancements:
  - `GET /api/runs/{run_id}/pwp-effective.csv`
  - `signals` payload includes `dt_s`, `delta_t_s`, and `delta_t`
  - config-template endpoints: `GET /api/config/templates`, `POST /api/config/template`
- React Web Studio model-builder panel:
  - create template-based YAML config files from UI
  - auto-fill generated config path into run form
- Web results parity for constitutive views:
  - new endpoint `GET /api/runs/{run_id}/results/hysteresis`
  - layer-wise stress-strain loop and mobilized-strength payload
  - `Stress-Strain` / `Mobilized Strength` tabs now render backend data
- Wizard Soil Profile UX upgrades:
  - per-layer `material_params` and `material_optional_args` editors
  - layer utility controls: duplicate, reorder (up/down), CSV import/export
  - DEEPSOIL-style table editor mode for layers (Table/Cards switch)
  - starter profile builders (`5-Layer Starter`, preset loader)
  - Auto Profile Creator in UI (`f_max`, points-per-wavelength, min slice thickness, max sublayers)
  - Runs panel accordion toggle (right-top triangle collapse/expand) to free workspace while editing layers
- PM4 calibration-ready template set added:
  - `pm4sand-calibration`
  - `pm4silt-calibration`
  - wired in CLI `init`/`quickstart` and web template endpoints
- React Wizard template bootstrap:
  - `Analysis Type` now includes one-click template apply
  - backend `wizard/schema` now returns `config_templates` and `template_defaults`
  - PM4 calibration and MKZ/GQH templates can populate full wizard state without manual YAML
- React Wizard flow hardening:
  - step-level readiness badges and inline issue reporting
  - `Generate Config` and `Run Now` buttons now enforce required step validity before execution
  - template selector now shows short preset descriptions in Analysis step
- Web motion upload flow:
  - new API endpoints: `POST /api/motion/upload/csv`, `POST /api/motion/upload/peer-at2`
  - browser-side file upload now fills wizard motion path directly (no manual file path typing)
- Results multi-motion compare:
  - run selector with up to 6 overlays
  - overlay charts for surface acceleration, PSA (5%), and transfer `|H(f)|`
  - reference-based diagnostics added (`PSA ratio`, transfer/surface `Δ`, `ΔPGA` and PGA ratio metrics)
- Run diagnostics:
  - new backend readiness endpoint `GET /api/backend/opensees/probe`
  - wizard now surfaces OpenSees availability and explicit run blockers when backend is set to `opensees`
- Pipeline artifact enrichment:
  - deterministic `config_snapshot.json` written per run
  - `run_meta.json` now includes `config_snapshot`

### Fixed
- PSA computation path now consistently uses run time-axis `dt` in pipeline/reporting flows.
- Web/Streamlit spectra views now recompute PSA from `surface_acc` to avoid stale-curve artifacts after deterministic reruns.
- React Wizard `Soil Profile` step no longer falls into blank-screen hook-order crash when switching steps (stabilized Step-2 render path).
- Web motion processing now uses robust `dt` fallback (`control.dt` or `1/(20*f_max)`) for one-column motions, preventing PSA distortion from accidental `dt=1.0`.
- AT2 import / processed-motion chaining now normalizes motion units to `m/s2` in wizard state to prevent double unit-scaling in PSA preview.
- OpenSees PM4 runtime stability improved:
  - added PM4 `FirstCall` initialization during stage transition in generated Tcl
  - added gravity permeability staging (high temporary permeability -> target `h_perm/v_perm`)
  - converted configured hydraulic conductivity (`m/s`) to quadUP permeability coefficients in Tcl
  - strengthened gravity/dynamic fallback solve sequence (`KrylovNewton` + substep retry)
- OpenSees quality diagnostics:
  - run-level log diagnostics are now extracted (`warning`, `failed_converge`, `analyze_failed`, `divide_by_zero`)
  - diagnostics are persisted in `run_meta.json` and `opensees_diagnostics.json`
  - run summary/convergence views now show OpenSees log diagnostics for non-EQL runs

## [0.1.0] - 2026-03-01

### Added
- First tagged baseline for repository bootstrap.

