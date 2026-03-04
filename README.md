# StrataWave

StrataWave is a CLI + Python SDK for 1D site response analysis workflows with an OpenSees adapter.
Current package version is `0.1.0`; the v1.0 roadmap focuses on effective-stress workflows, reproducible I/O, and benchmark-ready automation.

## Highlights
- JSON/YAML schema-validated project configs
- Motion preprocessing (baseline correction + scaling)
- OpenSees model generation and subprocess orchestration
- Native linear SH backend (lumped shear-beam, Newmark integration) for immediate baseline analysis
- Native equivalent-linear backend (`eql`) with iterative MKZ/GQH strain-compatible update loop
- Native nonlinear MKZ/GQH time-domain backend with stateful Masing/non-Masing branch updates
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

StrataWave init --template effective-stress --out examples/configs/effective_stress.yml
StrataWave init --template effective-stress-strict-plus --out examples/configs/effective_stress_strict_plus.yml
StrataWave init --template pm4sand-calibration --out examples/configs/pm4sand_calibration.yml
StrataWave init --template pm4silt-calibration --out examples/configs/pm4silt_calibration.yml
StrataWave init --template mkz-gqh-mock --out examples/configs/mkz_gqh_mock.yml
StrataWave init --template mkz-gqh-eql --out examples/configs/mkz_gqh_eql.yml
StrataWave init --template mkz-gqh-nonlinear --out examples/configs/mkz_gqh_nonlinear.yml
StrataWave quickstart --out out/quickstart --template effective-stress-strict-plus --backend auto
StrataWave validate --config examples/configs/effective_stress.yml
StrataWave validate --config examples/configs/effective_stress.yml --check-backend
StrataWave validate --config examples/configs/effective_stress.yml --check-backend --require-backend-version-regex "OpenSees"
StrataWave render-tcl --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/tcl_preview
StrataWave run --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/run001
StrataWave run --config examples/configs/effective_stress_strict_plus.yml --motion examples/motions/sample_motion.csv --out out/run_opensees_auto --backend auto
StrataWave run --config examples/configs/effective_stress_strict_plus.yml --motion examples/motions/sample_motion.csv --out out/run_force_mock --backend mock
StrataWave run --config examples/configs/mkz_gqh_mock.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh_eql --backend eql
StrataWave run --config examples/configs/mkz_gqh_nonlinear.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh_nl --backend nonlinear
StrataWave run --config examples/configs/mkz_gqh_mock.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh
StrataWave dt-check --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/dt_check
StrataWave benchmark --suite core-es --out out/benchmarks
StrataWave benchmark --suite core-hyst --out out/benchmarks_hyst
StrataWave benchmark --suite core-linear --out out/benchmarks_linear
StrataWave benchmark --suite core-eql --out out/benchmarks_eql
StrataWave benchmark --suite opensees-parity --out out/benchmarks_parity
StrataWave benchmark --suite release-signoff --out out/benchmarks_release_signoff --require-opensees --fail-on-skip --require-runs 18 --require-explicit-checks
StrataWave benchmark --suite opensees-parity --out out/benchmarks_parity --opensees-executable "C:/path/to/OpenSees.exe"
StrataWave benchmark --suite opensees-parity --out out/benchmarks_parity --require-opensees
StrataWave benchmark --suite opensees-parity --out out/benchmarks_parity --min-execution-coverage 1.0
StrataWave benchmark --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --require-explicit-checks
StrataWave verify --in out/run001/run-xxxxxxxxxxxx
StrataWave verify-batch --in out/run001 --require-runs 1
StrataWave summarize --benchmark-report out/benchmarks_parity/benchmark_opensees-parity.json --verify-batch-report out/benchmarks_parity/verify_batch_report.json --out out/benchmarks_parity
StrataWave campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
StrataWave campaign --suite opensees-parity --out out/benchmarks_parity --require-opensees --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
StrataWave campaign --suite opensees-parity --out out/benchmarks_parity --require-opensees --min-execution-coverage 1.0 --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
StrataWave campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --verify-require-runs 6 --opensees-executable "C:/path/to/OpenSees.exe" --require-explicit-checks
StrataWave campaign --suite opensees-parity --out out/benchmarks_parity --require-explicit-checks --require-opensees --fail-on-skip --require-runs 6 --verify-require-runs 6
StrataWave campaign --suite release-signoff --out out/release_signoff --require-opensees --fail-on-skip --require-runs 18 --verify-require-runs 18 --require-explicit-checks
StrataWave summarize --input out/release_signoff --strict-signoff
StrataWave lock-golden --benchmark-report out/benchmarks_parity/benchmark_opensees-parity.json --suite opensees-parity --metrics pga,ru_max,delta_u_max,sigma_v_eff_min,transfer_abs_max,transfer_peak_freq_hz,solver_warning_count,solver_failed_converge_count,solver_analyze_failed_count,solver_divide_by_zero_count,solver_dynamic_fallback_failed --rel-tol 0.05
StrataWave campaign --suite core-hyst --out out/benchmarks_hyst --require-runs 3 --verify-require-runs 3
```

## Web UI (Streamlit)
```bash
pip install -e .[ui]
StrataWave ui --host 127.0.0.1 --port 8501
```
Open `http://127.0.0.1:8501` in your browser.
UI panels include effective-stress views for `ru`, `delta_u`, and `sigma_v_eff`.
UI also includes a campaign panel (`core-es`, `core-hyst`, `core-linear`, `core-eql`, `opensees-parity`) with inline benchmark+verify summaries.
UI sidebar includes config presets (`effective-stress`, `effective-stress-strict-plus`, `mkz-gqh-mock`, `mkz-gqh-eql`, `mkz-gqh-nonlinear`) for quick switching.
UI run panel includes backend mode selection (`config/auto/opensees/mock/linear/eql/nonlinear`) and optional run-level OpenSees executable override.
UI includes a `Render Tcl` action with inline `model.tcl` preview and direct download for `model.tcl` + `motion_processed.csv`.
UI includes MKZ/GQH curve inspector plots (`G/Gmax` and damping proxy vs strain) for quick parameter sanity checks.
UI export panel includes `surface_acc.csv` and `pwp_effective.csv`, both with `delta_t_s`.

## Web API + React Dashboard (Migration Starter)
```bash
pip install -e .[web]
StrataWave web --host 127.0.0.1 --port 8010
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
- Motion outputs: processed CSV + metrics JSON

### Results Compare
- Results panel includes `Multi-Motion Compare` selector (up to 6 runs overlay).
- Overlay charts: surface acceleration, PSA (5%), and transfer `|H(f)|`.
- Reference-based diagnostics: PSA ratio to reference, transfer `Δ`, surface-acc `Δ`, and per-run `ΔPGA` / PGA ratio.

Included API endpoints:
- `GET /api/health`
- `GET /api/backend/opensees/probe?executable=<path-or-name>`
- `GET /api/runs?output_root=<path>`
- `GET /api/runs/tree?output_root=<path>`
- `GET /api/runs/{run_id}/signals?output_root=<path>`
- `GET /api/runs/{run_id}/results/summary?output_root=<path>`
- `GET /api/runs/{run_id}/surface-acc.csv?output_root=<path>`
- `GET /api/runs/{run_id}/pwp-effective.csv?output_root=<path>`
- `GET /api/wizard/schema`
- `POST /api/config/from-wizard`
- `POST /api/motion/import/peer-at2`
- `POST /api/motion/upload/csv`
- `POST /api/motion/upload/peer-at2`
- `POST /api/motion/process`
- `POST /api/run` (run analysis from config + motion paths)
- `GET /api/parity/latest?output_root=<path>`
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
- Dedicated OpenSees runner gate is mandatory in CI/release (`self-hosted, linux, x64, opensees`) and uses `release-signoff`.
- Release workflow enforces strict signoff (`1dsra summarize --strict-signoff`) and machine checks (`scripts/check_release_signoff.py`).
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
non-optional in CI/release paths.
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

