# 1DSRA

1DSRA is a CLI + Python SDK for 1D site response analysis workflows with an OpenSees adapter.
Version 1.0 focuses on effective-stress workflows, reproducible I/O, and benchmark-ready automation.

## Highlights
- JSON/YAML schema-validated project configs
- Motion preprocessing (baseline correction + scaling)
- OpenSees model generation and subprocess orchestration
- MKZ/GQH hysteretic backbone helpers for native/mock-track prototyping
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
1dsra validate --config examples/configs/effective_stress.yml
1dsra validate --config examples/configs/effective_stress.yml --check-backend
1dsra render-tcl --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/tcl_preview
1dsra run --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/run001
1dsra run --config examples/configs/mkz_gqh_mock.yml --motion examples/motions/sample_motion.csv --out out/mkz_gqh
1dsra dt-check --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/dt_check
1dsra benchmark --suite core-es --out out/benchmarks
1dsra benchmark --suite core-hyst --out out/benchmarks_hyst
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --opensees-executable "C:/path/to/OpenSees.exe"
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --require-opensees
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 3
1dsra verify --in out/run001/run-xxxxxxxxxxxx
1dsra verify-batch --in out/run001 --require-runs 1
1dsra summarize --benchmark-report out/benchmarks_parity/benchmark_opensees-parity.json --verify-batch-report out/benchmarks_parity/verify_batch_report.json --out out/benchmarks_parity
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 3 --verify-require-runs 3
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --require-opensees --fail-on-skip --require-runs 3 --verify-require-runs 3
1dsra campaign --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 3 --verify-require-runs 3 --opensees-executable "C:/path/to/OpenSees.exe"
1dsra campaign --suite core-hyst --out out/benchmarks_hyst --require-runs 3 --verify-require-runs 3
```

## Web UI (Streamlit)
```bash
pip install -e .[ui]
1dsra ui --host 127.0.0.1 --port 8501
```
Open `http://127.0.0.1:8501` in your browser.
UI panels include effective-stress views for `ru`, `delta_u`, and `sigma_v_eff`.
UI also includes a campaign panel (`core-es`, `core-hyst`, `opensees-parity`) with inline benchmark+verify summaries.
UI sidebar includes config presets (`effective-stress`, `effective-stress-strict-plus`, `mkz-gqh-mock`) for quick switching.
UI includes a `Render Tcl` action with inline `model.tcl` preview and direct download for `model.tcl` + `motion_processed.csv`.
UI includes MKZ/GQH curve inspector plots (`G/Gmax` and damping proxy vs strain) for quick parameter sanity checks.

## OpenSees Integration
Set the OpenSees executable in config:
```yaml
opensees:
  executable: OpenSees
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
MKZ/GQH are currently enabled for `mock` backend prototyping and are intentionally rejected
for `opensees` backend in v1 pipeline.
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

Each run writes structured metadata/artifacts:
- `run_meta.json` with backend, status, command metadata
- `opensees_stdout.log` / `opensees_stderr.log` (if available)
- SQLite `artifacts` table entries for generated files
- Effective-stress outputs in HDF5 `/pwp`: `ru`, `delta_u`, `sigma_v_ref`, `sigma_v_eff`

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
- Tag-based release workflow: `.github/workflows/release.yml` (push `v*` tags)
- CI/release workflows enforce a `core-es` campaign gate (`benchmark + verify + summary`)
- CI/release workflows enforce `core-es` and `core-hyst` campaign gates (`benchmark + verify + summary`)
- Version bump helper: `python scripts/release_bump.py --version 1.0.0`
- Release tag guard: `python scripts/check_release_tag.py --tag v1.0.0`
- Changelog guard: `python scripts/check_changelog.py --tag v1.0.0`

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
You can also pass override directly via CLI:
- `--opensees-executable /path/to/OpenSees`
Use benchmark strict policy flags to enforce non-skipped runs in CI:
- `--fail-on-skip`
- `--require-runs <N>`
Use OpenSees readiness policy for parity suites:
- `--require-opensees` (fails if parity cases are skipped due to missing OpenSees backend)
Use `campaign` to execute benchmark + verify-batch + summarize in one command.
Campaign summary now includes backend coverage indicators:
- `backend_ready`
- `skipped_backend`
- `execution_coverage`
- `backend_missing_cases`

A dedicated manual parity workflow is included:
- `.github/workflows/opensees-parity.yml`
  - default strict target: `require_runs=3`
  - writes `campaign_summary.json` + `campaign_summary.md` and appends markdown to GitHub job summary

## Run Verification
Use `verify` to validate post-run integrity:
- run-id consistency between directory, `run_meta.json`, and SQLite `runs`
- metric consistency between HDF5 and SQLite (`pga`, `ru_max`, `delta_u_max`, `sigma_v_ref`, `sigma_v_eff_min`)
- `pwp_effective_stats` table consistency against HDF5 (`row count`, `time bounds`, `delta_u_max`, `sigma_v_eff_min`)
- checksum consistency for `results.h5` and `results.sqlite`

Use `verify-batch` for folder-level checks over multiple run directories.
Use `summarize` to aggregate benchmark + verify outputs into campaign-level JSON/Markdown artifacts.
