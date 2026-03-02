# Benchmark Suite: opensees-parity

This suite is for real OpenSees parity checks.

- Backend: `opensees`
- Purpose: run calibration-ready u-p workflows against reference tolerance bands
- Cases:
  - `parity01`: PM4Sand + PM4Silt, elastic half-space
  - `parity02`: PM4Sand + PM4Silt, strict-plus validation profile
  - `parity03`: PM4Silt profile, strict-plus validation profile, alternative motion units
  - `parity04`: mixed PM4 profile with scale-by motion
  - `parity05`: PM4Sand-dominant profile with scale-to-PGA motion
  - `parity06`: PM4Silt-PM4Sand profile with alternate discretization settings
- Behavior:
  - If OpenSees executable is not resolvable, cases are marked as `skipped`
  - If executable exists, case metrics and constraints are evaluated

Before running:
- set valid `opensees.executable` in case config, or use an absolute path
- ensure OpenSees build supports commands used by generated Tcl
- optional executable override for all cases:
  - `DSRA1D_OPENSEES_EXE_OVERRIDE=/path/to/OpenSees`
- optional executable fingerprint requirements:
  - `--require-backend-version-regex <regex>`
  - `--require-backend-sha256 <hex>`
