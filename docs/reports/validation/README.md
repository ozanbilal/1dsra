# Validation Pack

This directory defines the external technical validation bundle for GeoWave.

Purpose:
- collect existing evidence from the repository in one place,
- generate a shareable `Markdown + JSON + PDF` report,
- keep validation packaging outside product runtime flows.

Generator:

```bash
python scripts/build_validation_pack.py
python scripts/build_deepsoil_example_parity_report.py
```

Default output:
- `output/pdf/validation/validation_pack.json`
- `output/pdf/validation/validation_pack.md`
- `output/pdf/validation/validation_pack.pdf`
- `output/pdf/validation/assets/*.png`
- `output/pdf/validation/deepsoil_examples/report/deepsoil_example_parity_report.json`
- `output/pdf/validation/deepsoil_examples/report/deepsoil_example_parity_report.md`
- `output/pdf/validation/deepsoil_examples/report/deepsoil_example_parity_report.pdf`
- `output/pdf/validation/deepsoil_examples/report/assets/*.png`

Evidence sources:
- `examples/output/deepsoil_equivalent/smoke/`
- `out/benchmarks_parity/benchmark_opensees-parity.json`
- `SCIENTIFIC_CONFIDENCE_MATRIX.md`
- `docs/PM4_CALIBRATION_VALIDATION.md`
- `docs/RELEASE_SIGNOFF_CHECKLIST.md`
- `out/ui/run-*/report.pdf` appendix artifacts

Optional screenshot source:
- `docs/reports/validation/assets/screenshots/*.png`

Notes:
- Missing evidence is reported explicitly as `partial` or `missing`; it is not hidden.
- Existing `out/ui/run-*/report.pdf` files are used as appendix evidence when present.
- If PyMuPDF (`fitz`) is available, preview images are rendered automatically into `output/pdf/validation/assets/`.
- The DEEPSOIL example parity report is separate from the broader validation pack and is intended for side-by-side native-vs-DEEPSOIL evidence only.
- Current best native DEEPSOIL Example 5A case is the tuned rigid-base run
  (`reload_factor=1.45`, `analysis.nonlinear_substeps=16`) with `PSA NRMSE ~= 0.1939`;
  this remains a partial-parity result, not a full equivalence claim.
- This directory is not part of the product runtime.
