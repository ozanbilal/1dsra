# Benchmark Suite: opensees-parity

This suite is for real OpenSees parity checks.

- Backend: `opensees`
- Purpose: run calibration-ready u-p workflows against reference tolerance bands
- Cases:
  - `parity01`: PM4Sand + PM4Silt, elastic half-space
  - `parity02`: PM4Sand + elastic base, rigid boundary
  - `parity03`: PM4Silt profile, elastic half-space, alternative motion units
- Behavior:
  - If OpenSees executable is not resolvable, cases are marked as `skipped`
  - If executable exists, case metrics and constraints are evaluated

Before running:
- set valid `opensees.executable` in case config, or use an absolute path
- ensure OpenSees build supports commands used by generated Tcl
- optional executable override for all cases:
  - `DSRA1D_OPENSEES_EXE_OVERRIDE=/path/to/OpenSees`
