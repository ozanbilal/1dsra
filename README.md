# GeoWave

GeoWave is a CLI + Python SDK for 1D site response analysis workflows with an OpenSees adapter.
Current package version is `0.1.0`; the v1.0 roadmap focuses on effective-stress workflows, reproducible I/O, and benchmark-ready automation.

## Current Engineering Docs

For the current repo state and DeepSoil baseline-parity direction, use these first:

- [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) — current engineering truth and next technical iterations
- [DEEPSOIL_BASELINE_PARITY_RESEARCH.md](DEEPSOIL_BASELINE_PARITY_RESEARCH.md) — living parity dossier and hypothesis ordering
- [PARITY_MEMORY.md](PARITY_MEMORY.md) — human-readable experiment memory and do-not-repeat guidance
- [parity_experiment_index.json](parity_experiment_index.json) — machine-readable experiment-family manifest
- [PROJECT_MAP.md](PROJECT_MAP.md) — current repo architecture and workflow map
- [AGENTS.md](AGENTS.md) — operator/agent guidance for parity-focused work

Important:

- the status doc is more authoritative than older roadmap language elsewhere in this README
- the parity research + memory docs are more authoritative than dated one-off research reports
- current engineering focus is native `linear + eql + nonlinear` baseline parity, not broad feature expansion
- the active elastic-vs-rigid verification path is boundary-first and now uses the DeepSoil batch `deepsoilout.db3` pair as the primary truth surface

Canonical parity references:

- canonical case: `examples/native/deepsoil_gqh_5layer_baseline.yml`
- primary workbook: `tests/Results_profile_0_motion_Kocaeli.xlsx`

## Highlights
- JSON/YAML schema-validated project configs
- Motion preprocessing (baseline correction + scaling)
- OpenSees model generation and subprocess orchestration
- Native linear SH backend (lumped shear-beam, Newmark integration) for immediate baseline analysis
- Native equivalent-linear backend (`eql`) with iterative MKZ/GQH strain-compatible update loop
- Native nonlinear MKZ/GQH time-domain backend with stateful Masing/non-Masing branch updates
- Native `rigid` and `elastic_halfspace` boundary handling for linear/nonlinear shear-beam backends
- Darendeli-style calibration path for native MKZ/GQH backends (config-driven parameter derivation)
- Configurable native nonlinear accuracy control via `analysis.nonlinear_substeps`
- DEEPSOIL side-by-side comparison utility for surface acceleration + PSA parity checks
- HDF5 + SQLite result stores
- HTML/PDF reports including effective-stress summary metrics (`ru_max`, `delta_u_max`, `sigma_v_eff_min`)
- Benchmark and regression workflow (multi-case metrics, ru bounds, deterministic and dt-sensitivity checks)
- Benchmark constraints now support physics guards (ru monotonic, `delta_u`/`sigma_v_eff` lower bounds, PGA bounds)
- Benchmark checks include effective-stress metrics (`delta_u_max`, `sigma_v_eff_min`)
- Batch deduplication for identical motions (avoids duplicate run collisions)
- Deterministic reruns are idempotent in SQLite (run-id tables are refreshed, not duplicated)
- Windows + Linux CI matrix, Docker runtime

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
pip install -e .[dev]

GeoWave init --template effective-stress --out examples/configs/effective_stress.yml
GeoWave init --template effective-stress-strict-plus --out examples/configs/effective_stress_strict_plus.yml
GeoWave init --template pm4sand-calibration --out examples/configs/pm4sand_calibration.yml
GeoWave init --template pm4silt-calibration --out examples/configs/pm4silt_calibration.yml
GeoWave init --template mkz-gqh-mock --out examples/configs/mkz_gqh_mock.yml
GeoWave init --template mkz-gqh-eql --out examples/configs/mkz_gqh_eql.yml
GeoWave init --template mkz-gqh-nonlinear --out examples/configs/mkz_gqh_nonlinear.yml
GeoWave init --template mkz-gqh-darendeli --out examples/configs/mkz_gqh_darendeli.yml
GeoWave calibrate-darendeli --material gqh --out out/darendeli_gqh --plasticity-index 12 --ocr 1.2 --mean-effective-stress-kpa 120 --vs-m-s 220 --unit-weight-kN-m3 18.5
GeoWave quickstart --out out/quickstart --template effective-stress-strict-plus --backend auto
GeoWave validate --config examples/configs/effective_stress.yml
GeoWave validate --config examples/configs/effective_stress.yml --check-backend
GeoWave validate --config examples/configs/effective_stress.yml --check-backend --require-backend-version-regex "OpenSees"
GeoWave render-tcl --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/tcl_preview
GeoWave run --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/run001
GeoWave run --config examples/configs/effective_stress_strict_plus.yml --motion examples/motions/sample_motion.csv --out out/run_opensees_auto --backend auto
GeoWave run --config examples/configs/effective_stress_strict_plus.yml --motion examples/motions/sample_motion.csv --out out/run_force_mock --backend mock
GeoWave run --config examples/configs/mkz_gqh_mock.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh_eql --backend eql
GeoWave run --config examples/configs/mkz_gqh_nonlinear.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh_nl --backend nonlinear
GeoWave run --config examples/configs/mkz_gqh_darendeli.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh_darendeli --backend nonlinear
GeoWave run --config examples/configs/mkz_gqh_mock.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh
GeoWave compare-deepsoil --run out/mkz_gqh_darendeli/run-xxxxxxxxxxxx --surface-csv path/to/deepsoil_surface.csv --psa-csv path/to/deepsoil_psa.csv --profile-csv path/to/deepsoil_profile.csv --hysteresis-csv path/to/deepsoil_hysteresis.csv --hysteresis-layer 0 --out out/deepsoil_compare
GeoWave compare-deepsoil-batch --manifest path/to/deepsoil_manifest.json --out out/deepsoil_compare_batch
GeoWave summarize --benchmark-report out/benchmarks_hyst/benchmark_core-hyst.json --deepsoil-compare-report out/deepsoil_compare_batch/deepsoil_compare_batch.json --out out/hyst_summary
GeoWave dt-check --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/dt_check
GeoWave benchmark --suite core-es --out out/benchmarks
GeoWave benchmark --suite core-hyst --out out/benchmarks_hyst
GeoWave benchmark --suite core-linear --out out/benchmarks_linear
GeoWave benchmark --suite core-eql --out out/benchmarks_eql
GeoWave benchmark --suite opensees-parity --out out/benchmarks_parity
GeoWave benchmark --suite release-signoff --out out/benchmarks_release_signoff --require-opensees --fail-on-skip --require-runs 18 --require-explicit-checks
GeoWave benchmark --suite opensees-parity --out out/benchmarks_parity --opensees-executable "C:/path/to/OpenSees.exe"
GeoWave benchmark --suite opensees-parity --out out/benchmarks_parity --require-opensees
GeoWave benchmark --suite opensees-parity --out out/benchmarks_parity --min-execution-coverage 1.0
GeoWave benchmark --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --require-explicit-checks
GeoWave verify --in out/run001/run-xxxxxxxxxxxx
GeoWave verify-batch --in out/run001 --require-runs 1
GeoWave summarize --benchmark-report out/benchmarks_parity/benchmark_opensees-parity.json --verify-batch-report out/benchmarks_parity/verify_batch_report.json --out out/benchmarks_parity
GeoWave campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
GeoWave campaign --suite opensees-parity --out out/benchmarks_parity --require-opensees --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
GeoWave campaign --suite opensees-parity --out out/benchmarks_parity --require-opensees --min-execution-coverage 1.0 --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
GeoWave campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --verify-require-runs 6 --opensees-executable "C:/path/to/OpenSees.exe" --require-explicit-checks
GeoWave campaign --suite opensees-parity --out out/benchmarks_parity --require-explicit-checks --require-opensees --fail-on-skip --require-runs 6 --verify-require-runs 6
GeoWave campaign --suite release-signoff --out out/release_signoff --require-opensees --fail-on-skip --require-runs 18 --verify-require-runs 18 --require-explicit-checks
GeoWave summarize --input out/release_signoff --strict-signoff
GeoWave lock-golden --benchmark-report out/benchmarks_parity/benchmark_opensees-parity.json --suite opensees-parity --metrics pga,ru_max,delta_u_max,sigma_v_eff_min,transfer_abs_max,transfer_peak_freq_hz,solver_warning_count,solver_failed_converge_count,solver_analyze_failed_count,solver_divide_by_zero_count,solver_dynamic_fallback_failed --rel-tol 0.05
GeoWave campaign --suite core-hyst --out out/benchmarks_hyst --require-runs 3 --verify-require-runs 3
```

## Web UI (Streamlit)
```bash
pip install -e .[ui]
GeoWave ui --host 127.0.0.1 --port 8501
```
Open `http://127.0.0.1:8501` in your browser.
UI panels include effective-stress views for `ru`, `delta_u`, and `sigma_v_eff`.
UI also includes a campaign panel (`core-es`, `core-hyst`, `core-linear`, `core-eql`, `opensees-parity`) with inline benchmark+verify summaries.
UI sidebar includes config presets (`effective-stress`, `effective-stress-strict-plus`, `mkz-gqh-mock`, `mkz-gqh-eql`, `mkz-gqh-nonlinear`, `mkz-gqh-darendeli`) for quick switching.
UI run panel includes backend mode selection (`config/auto/opensees/mock/linear/eql/nonlinear`) and optional run-level OpenSees executable override.
UI includes a `Render Tcl` action with inline `model.tcl` preview and direct download for `model.tcl` + `motion_processed.csv`.
UI includes MKZ/GQH curve inspector plots (`G/Gmax` and damping proxy vs strain) for quick parameter sanity checks.
UI export panel includes `surface_acc.csv` and `pwp_effective.csv`, both with `delta_t_s`.

## Web API + React Dashboard (Migration Starter)
```bash
pip install -e .[web]
GeoWave web --host 127.0.0.1 --port 8010
```
Open `http://127.0.0.1:8010`.
Primary UI path is now React + FastAPI; Streamlit remains as engineering/debug panel.
If `--port` is already occupied, CLI auto-scans next ports (`+20` by default).
You can tune it with `--port-scan <N>`.

### Wizard Workflow (Wave-1)
DEEPSOIL-style 5-step wizard is available:
- `Analysis Type`
- `Soil Profile`
- `Input Motion`
- `Damping`
- `Analysis Control`
- `Analysis Type` step includes `Wizard Template` loader (`effective-stress`, `effective-stress-strict-plus`, `pm4sand-calibration`, `pm4silt-calibration`, `mkz-gqh-*`) to bootstrap model state without YAML.
- Wizard tabs show step readiness badges and inline issues; `Generate Config`/`Run Now` are gated until required fields are valid.

`Soil Profile` step now supports DEEPSOIL-style bulk editing:
- `Table` mode for fast multi-layer entry and model-aware parameter editing (`pm4sand`, `pm4silt`, `mkz`, `gqh`, `elastic`)
- `Cards` mode for per-layer detailed edits
- `Layer Properties` studio: focused layer selector, curve-mode status, Darendeli calibration inputs for MKZ/GQH, fitted-vs-target `G/Gmax` and damping plots, plus single-element loop preview
- Layer utilities: `duplicate`, `up/down reorder`, `CSV import/export`
- Starter builders: `5-Layer Starter` quick button + preset loader (`five-main-layers`, `soft-over-stiff`)
- `Automatic Profile Builder`: define main layers, then auto-slice with:
  - `f_max` (or use Analysis Control `f_max`)
  - points-per-wavelength
  - minimum slice thickness
  - max sublayers per main layer

Run flow (no manual YAML editing required):
1. Fill 5 wizard steps.
2. Click `Generate Config`.
3. Click `Run Now`.
4. Inspect results tabs (`Time Histories`, `Spectral`, `Profile`, `Convergence`) and download artifacts.
5. Use `Open Results Frame` in Results header to switch into a full-width output workspace.
6. Review `Parity Health`, `Scientific Confidence`, and `Release Blockers` cards for quick go/no-go diagnostics.
   `Release Blockers` uses backend signoff endpoint fields (`release_ready`, fingerprint match, blocker categories, severity score/label).
7. Use the `Layer Ledger` + `Profile Atlas` inside the `Profile` tab for a fast depth read of stratigraphy, `Vs`, `gamma_max`, mesh density, `tau_peak`, mobilized strength, damping proxy, static overburden proxy, and layer-level effective-stress metrics (`ru_max`, `delta_u_max`, `sigma'_v,min`) before dropping to the detailed table.
8. In `Results Frame` mode, the UI now switches to a two-panel studio: left rail for run/artifact/quality navigation, right canvas for the active result tab.

Damping routing:
- Wizard `Damping` step writes directly into config analysis fields:
  - `damping_mode`
  - `rayleigh_mode_1_hz`
  - `rayleigh_mode_2_hz`
  - `rayleigh_update_matrix`
- Native `linear`, `eql`, and `nonlinear` backends now consume these fields at runtime.

### Motion Tools (Wave-1)
- Motion import: CSV + PEER AT2
- Motion upload (no local path typing): upload CSV or AT2 directly from browser, then auto-bind to wizard motion path
- Baseline modes: `none`, `remove_mean`, `detrend_linear`, `deepsoil_bap_like`
- Scaling modes: `none`, `scale_by`, `scale_to_pga`
- Optional `dt override` in wizard for one-column motions
- One-column CSV fallback `dt` now follows Analysis Control (`dt` or `1/(20*f_max)`) to avoid distorted PSA previews
- Imported/processed motions are tracked in SI (`m/s2`) in wizard state to prevent double unit conversion
- Motion preview plots: processed acceleration, PSA, FAS ratio
- Results and compare plots now include explicit x/y axis titles for direct engineering reading inside the web UI
- Motion outputs: processed CSV + metrics JSON

### Results Compare
- Results panel includes `Multi-Motion Compare` selector (up to 6 runs overlay).
- Overlay charts: surface acceleration, PSA (5%), and transfer `|H(f)|`.
- Reference-based diagnostics: PSA ratio to reference, transfer `Δ`, surface-acc `Δ`, and per-run `ΔPGA` / PGA ratio.

Included API endpoints:
- `GET /api/health`
- `GET /api/backend/opensees/probe?executable=<path-or-name>`
- backend probe response includes `requested_input`, `requested`, `assumed_available`, `env_override`, `env_override_used` for executable source diagnostics
- `GET /api/runs?output_root=<path>`
- `GET /api/runs/tree?output_root=<path>`
- `GET /api/runs/{run_id}/signals?output_root=<path>`
  - returns `409` with clear message when run exists but required artifacts are incomplete
- `GET /api/runs/{run_id}/results/summary?output_root=<path>`
- `GET /api/runs/{run_id}/profile-summary.csv?output_root=<path>`
- `GET /api/runs/{run_id}/surface-acc.csv?output_root=<path>`
- `GET /api/runs/{run_id}/pwp-effective.csv?output_root=<path>`
- `GET /api/wizard/schema`
- `POST /api/config/from-wizard`
- `POST /api/motion/import/peer-at2`
- `POST /api/motion/upload/csv`
- `POST /api/motion/upload/peer-at2`
- `POST /api/motion/process`
- `POST /api/run` (run analysis from config + motion paths; response includes normalized `output_root`)
- `GET /api/parity/latest?output_root=<path>`
- `GET /api/parity/deepsoil/latest?output_root=<path>`
- `GET /api/parity/deepsoil/release-manifest`
- `GET /api/science/confidence`
- `GET /api/release/signoff/latest?output_root=<path>`

## OpenSees Integration
Set the OpenSees executable in config:
```yaml
opensees:
  executable: OpenSees
  require_version_regex: null
  require_binary_sha256: null
```
You can also use an absolute path for deterministic environments.
u-p assembly constants are configurable per project via:
- `column_width_m`
- `thickness_m`
- `fluid_bulk_modulus`
- `fluid_mass_density`
- `h_perm`
- `v_perm`
- `gravity_steps`
When `analysis.solver_backend: opensees` is selected, PM4 layers must include
their required `material_params` keys (PM4Sand: `Dr/G0/hpo`, PM4Silt: `Su/Su_Rat/G_o/h_po`).
MKZ/GQH are intentionally rejected for `opensees` backend in v1 pipeline.
Use native `eql` / `nonlinear` backends for MKZ/GQH runs.
Darendeli calibration can now be declared directly on MKZ/GQH layers; the loader derives
native `material_params` automatically for `eql` / `nonlinear` runs.
Native nonlinear runs also accept `analysis.nonlinear_substeps` for tighter constitutive integration
when running parity studies or difficult strong-motion cases.
For DEEPSOIL side-by-side review, `compare-deepsoil` consumes a GeoWave run folder plus
DEEPSOIL-exported surface acceleration CSV and optional PSA/profile/hysteresis CSVs, then writes
`deepsoil_compare.json` + `deepsoil_compare.md` with PGA, correlation, RMSE, PSA mismatch,
layer-profile mismatch, and hysteresis-loop mismatch metrics.
For campaign-level review, `compare-deepsoil-batch` consumes a JSON manifest of cases and
writes `deepsoil_compare_batch.json` + `deepsoil_compare_batch.md` with pass/fail parity checks.
You can start from `examples/parity/deepsoil_compare_manifest.sample.json`
and replace the placeholder run/reference paths with your own exported cases.
If you already have many `run-*` folders, use the external helper
`scripts/scaffold_deepsoil_compare_manifest.py` to generate a starter manifest automatically.
The helper is documented in `examples/parity/README.md` and is intended for evidence/parity
prep work rather than product runtime.
`summarize` also accepts `--deepsoil-compare-report` so benchmark/verify/deepsoil parity can be merged into one campaign summary.
For a shareable external handoff focused only on the local DEEPSOIL example campaign,
run `python scripts/build_deepsoil_example_parity_report.py`.
It writes a standalone `JSON + Markdown + PDF` bundle under
`output/pdf/validation/deepsoil_examples/report/`.
That report now includes both rigid-base and native elastic-halfspace native parity iterations
for the DEEPSOIL `Example_5A` family.
Current best local parity case is still the rigid-base reduced-`dt` nonlinear run; the native
elastic-halfspace iterations improved substantially after incident-wave forcing was added, but do
not yet outperform the best rigid reduced-`dt` case at PSA level.
For release signoff, keep the real manifest at
`benchmarks/policies/release_signoff_deepsoil_manifest.json`; a starter template lives at
`benchmarks/policies/release_signoff_deepsoil_manifest.sample.json`.
Strict signoff policy can now optionally require:
- a DEEPSOIL batch parity report to be present
- profile parity coverage for every case
- hysteresis parity coverage for every case
These switches live in `benchmarks/policies/release_signoff.yml` as
`require_deepsoil_compare`, `require_deepsoil_profile`, and `require_deepsoil_hysteresis`.

Example:
```yaml
profile:
  layers:
    - name: Clay-1
      thickness_m: 6.0
      unit_weight_kN_m3: 18.2
      vs_m_s: 190.0
      material: mkz
      calibration:
        source: darendeli
        plasticity_index: 20.0
        ocr: 1.5
        mean_effective_stress_kpa: 80.0
        frequency_hz: 1.0
        num_cycles: 10.0
```
If `gmax` is not supplied explicitly, GeoWave seeds it from `Vs` and unit weight.
For calibration-ready experiments, you can pass extra positional PM4 arguments with:
- `layer.material_optional_args: [ ... ]`
These values are appended to the generated `nDMaterial PM4Sand/PM4Silt ...` line in order.
PM4 validation profile can be configured via:
- `analysis.pm4_validation_profile: basic` (presence + positivity checks)
- `analysis.pm4_validation_profile: strict` (adds conservative range checks)
- `analysis.pm4_validation_profile: strict_plus` (adds strict checks + u-p setup sanity guards:
  elastic-halfspace boundary, permeability/fluid/gravity bounds, and PM4 layer envelope checks)
Motion units are validated and converted to SI internally (`m/s2`).
Supported input units: `m/s2`, `m/s^2`, `mps2`, `g`, `gal`, `cm/s2`, `cm/s^2`.

`render_tcl` now generates a calibration-ready u-p column scaffold with:
- `model BasicBuilder -ndm 2 -ndf 3`
- PM4Sand / PM4Silt material command blocks
- `quadUP` element assembly
- boundary conditions (`rigid` or `elastic_halfspace` with Lysmer-style dashpot), gravity+dynamic stages
- surface acceleration and pore-pressure ratio recorder outputs
- representative layer pore-pressure recorder outputs (`layer_<tag>_pwp_raw.out`) for depth-wise effective-stress review
- PM4 stage-transition hardening:
  - `FirstCall` initialization per PM4 element/material after `updateMaterialStage ... -stage 1`
  - gravity stage with temporary high permeability, then restore user `h_perm/v_perm`
  - user `h_perm/v_perm` are treated as hydraulic conductivity (m/s) and converted to quadUP coefficients in Tcl

Use CLI `render-tcl` when you want to inspect/export OpenSees Tcl and processed motion
without running the solver backend.
Runtime backend mode can be overridden at execution time:
- `--backend config` (default: use config as-is)
- `--backend auto` (if config requests OpenSees but executable is missing, fallback to mock)
- `--backend opensees` (force OpenSees, fail fast if executable missing)
- `--backend mock` (force mock backend)
- `--backend linear` (force native linear SH response backend)
- `--backend eql` (force native equivalent-linear backend with strain-compatible updates)
- `--backend nonlinear` (force native nonlinear MKZ/GQH backbone-coupled time-domain backend)
These options are available on `run`, `batch`, `dt-check`, and `quickstart`.
`quickstart` creates a self-contained sample run directory, executes analysis, runs verification,
and writes `quickstart_summary.json`.

Each run writes structured metadata/artifacts:
- `run_meta.json` with backend, status, command metadata
- `opensees_stdout.log` / `opensees_stderr.log` (if available)
- `opensees_diagnostics.json` with extracted solver diagnostics (`warning_count`, `failed_converge_count`, `analyze_failed_count`, `divide_by_zero_count`)
- SQLite `artifacts` table entries for generated files
- `surface_acc.csv` with `time_s,acc_m_s2,delta_t_s`
- `pwp_effective.csv` with `time_s,ru,delta_u,sigma_v_eff,delta_t_s`
- Effective-stress outputs in HDF5 `/pwp`: `ru`, `delta_u`, `sigma_v_ref`, `sigma_v_eff`
- Time-step metadata in HDF5 `/meta/delta_t_s`
- Spectral outputs in HDF5 `/spectra`: `periods`, `psa`, `freq_hz`, `transfer_abs` (`|H(f)|`)
- EQL runs persist convergence outputs in HDF5 `/eql` and SQLite (`eql_summary`, `eql_layers`)

## Project Layout
- `python/dsra1d/`: SDK + CLI + adapters
- `core/`: C++ core scaffold for future native solver
- `benchmarks/`: benchmark suites and golden values
- `tests/`: unit and integration tests
- `docker/`: reproducible runtime image

## License
Apache-2.0

## Tracking
- Implementation status: [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md)
- Scientific confidence matrix: [SCIENTIFIC_CONFIDENCE_MATRIX.md](SCIENTIFIC_CONFIDENCE_MATRIX.md)
- Tag-based release workflow: `.github/workflows/release.yml` (push `v*` tags)
- CI workflow enforces matrix quality gates (`ruff`, `mypy`, `pytest`) and native suite campaign gates (`core-es`, `core-hyst`, `core-linear`, `core-eql`).
- Dedicated OpenSees runner gate is mandatory in `release.yml` and manual parity workflow, not on every `push` CI run.
- Release workflow now runs `scripts/run_release_deepsoil_compare.py` before strict summary; it skips cleanly when no release manifest is configured and policy does not require DEEPSOIL parity.
- Release workflow enforces strict signoff (`1dsra summarize --strict-signoff`) and machine checks (`scripts/check_release_signoff.py`).
- Strict signoff can now elevate DEEPSOIL parity to a release blocker through `benchmarks/policies/release_signoff.yml`.
- React Web Studio now exposes latest DEEPSOIL batch parity as a case-level `Deepsoil Parity` panel under the results quality rail.
- That panel now also surfaces release-manifest configuration state, starter template path, and policy gate flags.
- The same panel now includes an editable `Release Manifest Studio` table for release DEEPSOIL parity cases and tolerance defaults.
- Before tagging a release, set `opensees-parity` fingerprint in `SCIENTIFIC_CONFIDENCE_MATRIX.md` to the exact 64-hex sha256 observed on dedicated signoff run.
- Version bump helper: `python scripts/release_bump.py --version 0.1.0`
- Release tag guard: `python scripts/check_release_tag.py --tag v0.1.0`
- Changelog guard: `python scripts/check_changelog.py --tag v0.1.0`

## Optional Real OpenSees Integration Test
By default, test suite runs fully in mock mode. To run the real binary integration test:
```bash
set DSRA1D_RUN_OPENSEES_INTEGRATION=1
set OPENSEES_EXE=OpenSees
pytest tests/test_opensees_integration_optional.py
```
On Linux/macOS, use `export` instead of `set`.
`opensees-parity` benchmark suite also supports real-binary verification and auto-skips
cases when `opensees.executable` is not found.
You can override executable path without editing benchmark configs:
- `DSRA1D_OPENSEES_EXE_OVERRIDE=/path/to/OpenSees`
You can also override executable extra args (JSON list or shell string):
- `DSRA1D_OPENSEES_EXTRA_ARGS_OVERRIDE='["scripts/opensees_pyshim.py"]'`
You can also pass override directly via CLI:
- `--opensees-executable /path/to/OpenSees`
You can enforce backend fingerprint requirements from CLI:
- `--require-backend-version-regex "<regex>"`
- `--require-backend-sha256 "<hex>"`
Use benchmark strict policy flags to enforce non-skipped runs in CI:
- `--fail-on-skip`
- `--require-runs <N>`
Use explicit-checks policy to enforce locked parity envelopes:
- `--require-explicit-checks` (fails if executed cases do not have explicit `checks` in golden metrics)
Use OpenSees readiness policy for parity suites:
- `--require-opensees` (fails if parity cases are skipped due to missing OpenSees backend)
Dedicated parity gate runs on `self-hosted, linux, x64, opensees` runners and is
non-optional in release/manual parity paths.
Set repository variable `DSRA1D_CI_OPENSEES_EXE` (or ensure `OpenSees` is on PATH)
for deterministic executable resolution on the dedicated runner.
Release path also requires fingerprint variable:
- `DSRA1D_CI_OPENSEES_SHA256`
It must match `benchmarks/policies/release_signoff.yml:opensees_fingerprint`
(currently `5aa4e9c80c410c510ca62ac3b2f1d64a8e50679f0238e140b5bebcd6d5ddbe6d`).
Use execution coverage policy for campaign/benchmark suites:
- `--min-execution-coverage <0..1>` (fails if executed case ratio is below target)
Use `campaign` to execute benchmark + verify-batch + summarize in one command.
Use `release-signoff` suite to execute all critical suites in one parity-first gate:
- `core-es`, `core-hyst`, `core-linear`, `core-eql`, `opensees-parity`
Use strict signoff for release verdict generation:
- `1dsra summarize --input <campaign_dir> --strict-signoff`
Use `lock-golden` to freeze benchmark actual metrics into explicit golden `checks` envelopes.
Campaign summary now includes backend coverage indicators:
- `backend_ready`
- `skipped_backend`
- `execution_coverage`
- `backend_missing_cases`
Parity benchmark JSON also includes `backend_probe`:
- `requested`
- `resolved`
- `available`
- `version`
- `binary_sha256`
- `requirements` (`ok`, `errors`, requested regex/sha)
When backend probe fails (resolved executable exists but probe is not runnable),
parity cases are marked with `skip_kind=probe_failed`; `--require-opensees` will fail.
Campaign summary JSON also includes policy evaluation blocks:
- `policy.benchmark`
- `policy.verify_batch`
- `policy.campaign`

A dedicated manual parity workflow is included:
- `.github/workflows/opensees-parity.yml`
  - default strict target: `require_runs=6`
  - default coverage target: `min_execution_coverage=1.0`
  - writes `campaign_summary.json` + `campaign_summary.md` and appends markdown to GitHub job summary

## Run Verification
Use `verify` to validate post-run integrity:
- run-id consistency between directory, `run_meta.json`, and SQLite `runs`
- metric consistency between HDF5 and SQLite (`pga`, `ru_max`, `delta_u_max`, `sigma_v_ref`, `sigma_v_eff_min`)
- `pwp_effective_stats` table consistency against HDF5 (`row count`, `time bounds`, `delta_u_max`, `sigma_v_eff_min`)
- for successful OpenSees runs: command metadata + stdout/stderr artifact/log presence checks
- checksum consistency for `results.h5` and `results.sqlite`

Use `verify-batch` for folder-level checks over multiple run directories.
Use `summarize` to aggregate benchmark + verify outputs into campaign-level JSON/Markdown artifacts.

## Example Packs

The repository now includes a ready-to-run DEEPSOIL-equivalent example pack:
- `examples/deepsoil_equivalent/linear_reference.yml`
- `examples/deepsoil_equivalent/eql_reference.yml`
- `examples/deepsoil_equivalent/nonlinear_reference.yml`
- `examples/deepsoil_equivalent/effective_stress_reference.yml`

The pack was smoke-tested on 2026-03-19 with the following commands:
```bash
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/linear_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/linear_smoke
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/eql_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/eql_smoke
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/nonlinear_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/nonlinear_smoke
python -m dsra1d.cli.main run --config examples/deepsoil_equivalent/effective_stress_reference.yml --motion examples/motions/sample_motion.csv --out examples/output/deepsoil_equivalent/effective_smoke
```
This pack is intended for validation and demonstration runs, not as a product feature.
## Validation Pack
External technical validation artifacts are generated under `output/pdf/validation/`.
The focused DEEPSOIL example parity report currently identifies
`nonlinear_5a_rigid_dt0025_tuned` as the best native Example 5A case with
`PSA NRMSE ~= 0.1939`, which is still classified as partial parity rather than full equivalence.
The pack includes a Markdown manifest, a JSON manifest, and a PDF report built from
existing smoke, benchmark, parity, and confidence evidence in the repository.
