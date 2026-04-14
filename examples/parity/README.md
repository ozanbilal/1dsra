# DEEPSOIL Parity Manifest Workflow

This directory holds starter artifacts for GeoWave-vs-DEEPSOIL parity work.

## Files
- `deepsoil_compare_manifest.sample.json`: hand-edited starter example
- `deepsoil_compare_manifest.generated.json`: optional scaffold output created from existing `run-*` folders

## Recommended Flow
1. Run a GeoWave case first and confirm the target `run-*` directory is complete.
2. Export the matching DEEPSOIL reference CSV files:
   - `surface.csv`
   - `psa.csv`
   - optional `profile.csv`
   - optional `hysteresis_layer1.csv`
3. Scaffold a manifest from the available GeoWave runs:

```bash
python scripts/scaffold_deepsoil_compare_manifest.py ^
  --runs-root "examples/output/deepsoil_equivalent/smoke" ^
  --out "examples/parity/deepsoil_compare_manifest.generated.json" ^
  --deepsoil-reference-root "references/deepsoil"
```

4. Replace the placeholder DEEPSOIL CSV paths with the real exported files.
5. Run batch parity:

```bash
GeoWave compare-deepsoil-batch ^
  --manifest "examples/parity/deepsoil_compare_manifest.generated.json" ^
  --out "out/deepsoil_compare_batch"
```

## Notes
- The scaffold script is an external repo utility, not part of the product runtime.
- By default, only completed runs (`status=ok` and `results.h5` present) are included.
- Add `--include-incomplete` only when intentionally preparing a parity backlog.
