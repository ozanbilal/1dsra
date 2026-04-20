# StrataWave Validation Pack

- Generated: `2026-03-23T13:32:39.461950+00:00`
- Repo root: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA`
- Output dir: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation`

## Verdict

- Core verdict: `Calisiyor`
- Parity verdict: `Kismi`
- Release verdict: `Kismi`
- Overall verdict: `Kismi`

## Claims this pack supports

- Native `linear`, `eql`, and `nonlinear` analysis paths execute end-to-end.
- The OpenSees effective-stress adapter executes and captures diagnostics.
- Darendeli-based MKZ/GQH calibration is wired into the repository.
- DEEPSOIL parity tooling exists, but parity remains partial.
- The web UI exposes wizard, results, parity, and confidence surfaces.

## Validation snapshots

- Smoke pack: `4/4` passed
- OpenSees parity benchmark: `ran=0`, `skipped=1`
- Confidence rows: `5`

## Status matrix

| Bucket | Scope | Horizon | Note |
|---|---|---|---|
| Done | Native linear/EQL/nonlinear; OpenSees adapter; Darendeli calibration; DEEPSOIL-like UI; benchmark harness | Current | Core workflows execute and produce reproducible outputs. |
| Partial | DEEPSOIL parity, release-signoff runner in local environment, visual appendix coverage | Near-term | Parity tooling exists, but reference coverage is not yet publication-locked. |
| Pending | Broader published-reference matrix and native full effective-stress solver | Next | Current engineering gaps, not blockers for validation reporting. |
| Out-of-v1 | Full native u-p solver and complete DEEPSOIL project import/export | Later | Explicitly outside the current delivery boundary. |

## Evidence inventory

- **Native linear/EQL/nonlinear example pack**
  - Artifact: `Smoke summary`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\examples\output\deepsoil_equivalent\smoke\smoke_summary.json`
  - Note: 4/4 cases passed in the example bundle.
  - Status: `ok`
- **OpenSees effective-stress path executes**
  - Artifact: `OpenSees stdout log`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\examples\output\deepsoil_equivalent\smoke\effective_stress\run-485b214d64ad\opensees_stdout.log`
  - Note: Representative effective-stress smoke artifact.
  - Status: `ok`
- **OpenSees diagnostics are captured**
  - Artifact: `OpenSees diagnostics`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\examples\output\deepsoil_equivalent\smoke\effective_stress\run-485b214d64ad\opensees_diagnostics.json`
  - Note: Shows the adapter is not a stub.
  - Status: `ok`
- **Darendeli calibration is wired**
  - Artifact: `PM4 validation guide`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\docs\PM4_CALIBRATION_VALIDATION.md`
  - Note: Declares valid ranges and strict-plus constraints.
  - Status: `ok`
- **DEEPSOIL parity tooling exists**
  - Artifact: `Compare engine`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\python\dsra1d\deepsoil_compare.py`
  - Note: Surface, profile, and hysteresis compare support.
  - Status: `ok`
- **Release parity wiring exists**
  - Artifact: `Release parity helper`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\scripts\run_release_deepsoil_compare.py`
  - Note: Policy-aware compare orchestration.
  - Status: `ok`
- **Scientific confidence is tracked**
  - Artifact: `Confidence matrix`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\SCIENTIFIC_CONFIDENCE_MATRIX.md`
  - Note: Canonical release-scientific signoff table.
  - Status: `ok`
- **UI exposes wizard/results/parity/confidence**
  - Artifact: `React + FastAPI web layer`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\python\dsra1d\web\app.py`
  - Note: React + FastAPI orchestration layer.
  - Status: `ok`
- **Examples show the target workflow**
  - Artifact: `DEEPSOIL-equivalent examples`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\examples\deepsoil_equivalent\README.md`
  - Note: Linear, EQL, nonlinear, and effective-stress references.
  - Status: `ok`
- **Parity manifests are defined**
  - Artifact: `Parity manifest sample`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\examples\parity\deepsoil_compare_manifest.sample.json`
  - Note: Batch compare manifest format for side-by-side checks.
  - Status: `ok`
- **Release parity manifest is defined**
  - Artifact: `Release manifest sample`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\benchmarks\policies\release_signoff_deepsoil_manifest.sample.json`
  - Note: Used by release workflow when parity is available.
  - Status: `ok`
- **Release gate is codified**
  - Artifact: `Release signoff checklist`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\docs\RELEASE_SIGNOFF_CHECKLIST.md`
  - Note: Operational gate for v* tags.
  - Status: `ok`
- **OpenSees parity benchmark exists**
  - Artifact: `Benchmark JSON`
  - Path: `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\out\benchmarks_parity\benchmark_opensees-parity.json`
  - Note: Gate evidence; local environment may skip when OpenSees is absent.
  - Status: `ok`

## Scientific confidence summary

- `core-es` | Medium | Internal-only reference lock; external publication lock pending
- `core-hyst` | Medium | Published loop/reference lock pending
- `core-linear` | Medium-High | Physics-grounded but not yet publication-locked
- `core-eql` | Medium | SHAKE/DEEPSOIL external lock pending
- `opensees-parity` | Medium | Fingerprint locked from local OpenSees binary; dedicated runner must match exactly at release signoff

## Appendix evidence

- `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\out\ui\run-2c32ae6cc181\report.pdf`
- `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\out\ui\run-ddd5bbb22b69\report.pdf`
- `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\out\ui\run-9b578ad94620\report.pdf`

## Appendix preview images

- `run-2c32ae6cc181` -> `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\assets\ui_appendix_preview_01.png`
- `run-ddd5bbb22b69` -> `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\assets\ui_appendix_preview_02.png`
- `run-9b578ad94620` -> `H:\Drive'ım\GitHub_Repo\Deepsoil\1DSRA\output\pdf\validation\assets\ui_appendix_preview_03.png`

## Honest limitations

- This pack does not claim full DEEPSOIL parity.
- The native full effective-stress solver is still pending.
- Dedicated OpenSees runner coverage is environment-dependent and policy-gated.

## Rebuild

```bash
python scripts/build_validation_pack.py
```
