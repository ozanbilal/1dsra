# PM4 Calibration Minimum Validation Guide

This guide defines the minimum parameter sets and strict validation ranges used by GeoWave templates.

## PM4Sand minimum valid parameter set
Required keys:
- `Dr`
- `G0`
- `hpo`

Strict range checks (`strict` / `strict_plus`):
- `Dr` in `(0.0, 1.0]`
- `G0` in `(50.0, 3000.0]`
- `hpo` in `(0.01, 5.0]`

## PM4Silt minimum valid parameter set
Required keys:
- `Su`
- `Su_Rat`
- `G_o`
- `h_po`

Strict range checks (`strict` / `strict_plus`):
- `Su` in `(0.0, 1000.0]`
- `Su_Rat` in `(0.0, 1.0]`
- `G_o` in `(50.0, 3000.0]`
- `h_po` in `(0.01, 5.0]`

## strict_plus environment constraints
- `boundary_condition=elastic_halfspace`
- PM4-only layer stack (`pm4sand` / `pm4silt`)
- profile depth in `[5, 200]` m
- `h_perm/v_perm` in `[1e-2, 1e2]`
- `gravity_steps` in `[10, 2000]`

## Templates
- `examples/configs/pm4sand_calibration.yml`
- `examples/configs/pm4silt_calibration.yml`

Use `1dsra validate --config <path> --check-backend` to print checklist + backend diagnostics.
