# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project follows Semantic Versioning.

## [Unreleased]

### Added
- Initial 1DSRA v1 scaffold with:
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
  - `1dsra web` command (uvicorn-backed)
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

### Fixed
- PSA computation path now consistently uses run time-axis `dt` in pipeline/reporting flows.
- Web/Streamlit spectra views now recompute PSA from `surface_acc` to avoid stale-curve artifacts after deterministic reruns.

## [0.1.0] - 2026-03-01

### Added
- First tagged baseline for repository bootstrap.
