# 1DSRA

1DSRA is a CLI + Python SDK for 1D site response analysis workflows with an OpenSees adapter.
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

1dsra init --template effective-stress --out examples/configs/effective_stress.yml
1dsra init --template effective-stress-strict-plus --out examples/configs/effective_stress_strict_plus.yml
1dsra init --template mkz-gqh-mock --out examples/configs/mkz_gqh_mock.yml
1dsra init --template mkz-gqh-eql --out examples/configs/mkz_gqh_eql.yml
1dsra init --template mkz-gqh-nonlinear --out examples/configs/mkz_gqh_nonlinear.yml
1dsra quickstart --out out/quickstart --template effective-stress-strict-plus --backend auto
1dsra validate --config examples/configs/effective_stress.yml
1dsra validate --config examples/configs/effective_stress.yml --check-backend
1dsra validate --config examples/configs/effective_stress.yml --check-backend --require-backend-version-regex "OpenSees"
1dsra render-tcl --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/tcl_preview
1dsra run --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/run001
1dsra run --config examples/configs/effective_stress_strict_plus.yml --motion examples/motions/sample_motion.csv --out out/run_opensees_auto --backend auto
1dsra run --config examples/configs/effective_stress_strict_plus.yml --motion examples/motions/sample_motion.csv --out out/run_force_mock --backend mock
1dsra run --config examples/configs/mkz_gqh_mock.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh_eql --backend eql
1dsra run --config examples/configs/mkz_gqh_nonlinear.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh_nl --backend nonlinear
1dsra run --config examples/configs/mkz_gqh_mock.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh
1dsra dt-check --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/dt_check
1dsra benchmark --suite core-es --out out/benchmarks
1dsra benchmark --suite core-hyst --out out/benchmarks_hyst
1dsra benchmark --suite core-linear --out out/benchmarks_linear
1dsra benchmark --suite core-eql --out out/benchmarks_eql
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --opensees-executable "C:/path/to/OpenSees.exe"
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --require-opensees
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --min-execution-coverage 1.0
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --require-explicit-checks
1dsra verify --in out/run001/run-xxxxxxxxxxxx
1dsra verify-batch --in out/run001 --require-runs 1
1dsra summarize --benchmark-report out/benchmarks_parity/benchmark_opensees-parity.json --verify-batch-report out/benchmarks_parity/verify_batch_report.json --out out/benchmarks_parity
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --require-opensees --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --require-opensees --min-execution-coverage 1.0 --fail-on-skip --require-runs 6 --verify-require-runs 6 --require-explicit-checks
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 6 --verify-require-runs 6 --opensees-executable "C:/path/to/OpenSees.exe" --require-explicit-checks
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --require-explicit-checks --require-opensees --fail-on-skip --require-runs 6 --verify-require-runs 6
1dsra lock-golden --benchmark-report out/benchmarks_parity/benchmark_opensees-parity.json --suite opensees-parity --metrics pga,ru_max,delta_u_max,sigma_v_eff_min --rel-tol 0.05
1dsra campaign --suite core-hyst --out out/benchmarks_hyst --require-runs 3 --verify-require-runs 3
```

## Web UI (Streamlit)
```bash
pip install -e .[ui]
1dsra ui --host 127.0.0.1 --port 8501
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
1dsra web --host 127.0.0.1 --port 8010
```
Open `http://127.0.0.1:8010`.
Primary UI path is now React + FastAPI; Streamlit remains as engineering/debug panel.

### Wizard Workflow (Wave-1)
DEEPSOIL-style 5-step wizard is available:
- `Analysis Type`
- `Soil Profile`
- `Input Motion`
- `Damping`
- `Analysis Control`

Run flow (no manual YAML editing required):
1. Fill 5 wizard steps.
2. Click `Generate Config`.
3. Click `Run Now`.
4. Inspect results tabs (`Time Histories`, `Spectral`, `Profile`, `Convergence`) and download artifacts.

### Motion Tools (Wave-1)
- Motion import: CSV + PEER AT2
- Baseline modes: `none`, `remove_mean`, `detrend_linear`, `deepsoil_bap_like`
- Scaling modes: `none`, `scale_by`, `scale_to_pga`
- Motion preview plots: processed acceleration, PSA, FAS ratio
- Motion outputs: processed CSV + metrics JSON

Included API endpoints:
- `GET /api/health`
- `GET /api/runs?output_root=<path>`
- `GET /api/runs/tree?output_root=<path>`
- `GET /api/runs/{run_id}/signals?output_root=<path>`
- `GET /api/runs/{run_id}/results/summary?output_root=<path>`
- `GET /api/runs/{run_id}/surface-acc.csv?output_root=<path>`
- `GET /api/runs/{run_id}/pwp-effective.csv?output_root=<path>`
- `GET /api/wizard/schema`
- `POST /api/config/from-wizard`
- `POST /api/motion/import/peer-at2`
- `POST /api/motion/process`
- `POST /api/run` (run analysis from config + motion paths)

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
- CI/release workflows enforce `core-es`, `core-hyst`, `core-linear`, and `core-eql` campaign gates (`benchmark + verify + summary`)
- CI/release campaign gates enforce full execution coverage (`--min-execution-coverage 1.0`)
- Release workflow includes mandatory dedicated OpenSees parity gate (`self-hosted, linux, x64, opensees`) before package publish.
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
CI can run parity automatically when repository variable `DSRA1D_CI_OPENSEES_EXE` is set
to a valid executable path/name on the runner.
Dedicated self-hosted parity job in CI is opt-in via:
- `DSRA1D_CI_DEDICATED_OPENSEES=1`
Optional OpenSeesPy parity gate can be enabled with repository variable:
- `DSRA1D_CI_OPENSEESPY=1`
and uses `scripts/opensees_pyshim.py`.
Use execution coverage policy for campaign/benchmark suites:
- `--min-execution-coverage <0..1>` (fails if executed case ratio is below target)
Use `campaign` to execute benchmark + verify-batch + summarize in one command.
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
