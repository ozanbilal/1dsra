# 1DSRA

1DSRA is a CLI + Python SDK for 1D site response analysis workflows with an OpenSees adapter.
Version 1.0 focuses on effective-stress workflows, reproducible I/O, and benchmark-ready automation.

## Highlights
- JSON/YAML schema-validated project configs
- Motion preprocessing (baseline correction + scaling)
- OpenSees model generation and subprocess orchestration
- HDF5 + SQLite result stores
- Benchmark and regression workflow (multi-case metrics, ru bounds, deterministic and dt-sensitivity checks)
- Windows + Linux CI matrix, Docker runtime

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate
pip install -e .[dev]

1dsra init --template effective-stress --out examples/configs/effective_stress.yml
1dsra validate --config examples/configs/effective_stress.yml
1dsra validate --config examples/configs/effective_stress.yml --check-backend
1dsra run --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/run001
1dsra dt-check --config examples/configs/effective_stress.yml --motion examples/motions/sample_motion.csv --out out/dt_check
1dsra benchmark --suite core-es --out out/benchmarks
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity
1dsra benchmark --suite opensees-parity --out out/benchmarks_parity --fail-on-skip --require-runs 3
1dsra verify --in out/run001/run-xxxxxxxxxxxx
1dsra verify-batch --in out/run001 --require-runs 1
```

## Web UI (Streamlit)
```bash
pip install -e .[ui]
1dsra ui --host 127.0.0.1 --port 8501
```
Open `http://127.0.0.1:8501` in your browser.

## OpenSees Integration
Set the OpenSees executable in config:
```yaml
opensees:
  executable: OpenSees
```
You can also use an absolute path for deterministic environments.
When `analysis.solver_backend: opensees` is selected, PM4 layers must include
their required `material_params` keys (PM4Sand: `Dr/G0/hpo`, PM4Silt: `Su/Su_Rat/G_o/h_po`).
PM4 validation profile can be configured via:
- `analysis.pm4_validation_profile: basic` (presence + positivity checks)
- `analysis.pm4_validation_profile: strict` (adds conservative range checks)
Motion units are validated and converted to SI internally (`m/s2`).
Supported input units: `m/s2`, `m/s^2`, `mps2`, `g`, `gal`, `cm/s2`, `cm/s^2`.

`render_tcl` now generates a calibration-ready u-p column scaffold with:
- `model BasicBuilder -ndm 2 -ndf 3`
- PM4Sand / PM4Silt material command blocks
- `quadUP` element assembly
- boundary conditions (`rigid` or `elastic_halfspace` with Lysmer-style dashpot), gravity+dynamic stages
- surface acceleration and pore-pressure ratio recorder outputs

Each run writes structured metadata/artifacts:
- `run_meta.json` with backend, status, command metadata
- `opensees_stdout.log` / `opensees_stderr.log` (if available)
- SQLite `artifacts` table entries for generated files

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
Use benchmark strict policy flags to enforce non-skipped runs in CI:
- `--fail-on-skip`
- `--require-runs <N>`

A dedicated manual parity workflow is included:
- `.github/workflows/opensees-parity.yml`
  - default strict target: `require_runs=3`

## Run Verification
Use `verify` to validate post-run integrity:
- run-id consistency between directory, `run_meta.json`, and SQLite `runs`
- metric consistency between HDF5 and SQLite (`pga`, `ru_max`)
- checksum consistency for `results.h5` and `results.sqlite`

Use `verify-batch` for folder-level checks over multiple run directories.
