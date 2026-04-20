# GeoWave Project Map

## Summary

This file is the architecture and ownership-level map for the current repo.

The repo is currently running a parity campaign, not a broad feature campaign.

Current engineering focus:

- native `linear + eql + nonlinear`
- DeepSoil rigid/outcrop baseline parity
- boundary-first elastic-vs-rigid verification against DeepSoil DB output
- compare-driven iteration against workbook exports

## Current Source Of Truth

Read these first:

- `IMPLEMENTATION_STATUS.md`
- `DEEPSOIL_BASELINE_PARITY_RESEARCH.md`
- `PARITY_MEMORY.md`
- `parity_experiment_index.json`
- `AGENTS.md`

Canonical case:

- `examples/native/deepsoil_gqh_5layer_baseline.yml`

Primary workbook:

- `tests/Results_profile_0_motion_Kocaeli.xlsx`

Primary DeepSoil DB boundary surface:

- `C:/DEEPSOIL/Batch Output/Batch_run_22/.../deepsoilout.db3`
- `C:/DEEPSOIL/Batch Output/Batch_run_23/.../deepsoilout.db3`

Primary acceptance outputs:

- compare JSON under `output/baseline_iter/*/compare/`
- constitutive replay summaries under `output/baseline_iter/single_element_*`
- tangent audit summaries under `output/baseline_iter/tangent_audit_*`

## Core Source Layout

### `python/dsra1d/config`

Purpose:

- schema
- runtime defaults
- example/template loading
- legacy config normalization

Key files:

- `python/dsra1d/config/models.py`
- `python/dsra1d/config/io.py`

Current importance:

- parity-critical defaults live here
- current expected baseline defaults are `rigid + nonlinear + outcrop + frequency_independent + newmark`

### `python/dsra1d/motion`

Purpose:

- motion import
- unit normalization
- preprocessing
- applied base-motion semantics

Current importance:

- input time-step and outcrop application are parity-critical
- boundary-input semantic locking lives here
- generated uploaded/converted motions are written under `out/ui/motions/`

Important note:

- `out/ui/motions/` is generated cache, not source
- motion-library scanning is based on user-provided folders
- motion-library scanning does not recurse into subfolders

### `python/dsra1d/materials` and nonlinear solver path

Purpose:

- backbone evaluation
- MRDF bridge behavior
- unload/reload/reversal logic
- active tangent evolution

Key files:

- `python/dsra1d/materials/hysteretic.py`
- `python/dsra1d/materials/mrdf.py`
- `python/dsra1d/nonlinear.py`
- `python/dsra1d/newmark_nonlinear.py`

Current hotspot:

- `F_mrdf` evolution
- translated-branch curvature
- active tangent actually assembled by the solver

### `python/dsra1d/deepsoil_excel.py` and `python/dsra1d/deepsoil_compare.py`

Purpose:

- import DeepSoil workbook data into canonical compare artifacts
- compute response-level parity metrics

Why these matter now:

- parity is being judged on response outputs, not parameter similarity
- the workbook compare report is the main acceptance gate

### `python/dsra1d/constitutive_debug.py`

Purpose:

- single-element replay against workbook-derived hysteresis
- solver tangent audit
- all-layer compliance/tangent sweep
- boundary sensitivity compare and DeepSoil DB delta ingestion

Current usage:

- first-stop parity diagnostics before rerunning full compare
- boundary-first delta comparison also runs through this file

Important output families:

- `single_element_*`
- `tangent_audit_*`
- `layer_sweep_*`
- `boundary_first_*`
- `boundary_delta_*`

### `python/dsra1d/web`

Purpose:

- wizard
- motion library
- results viewer

Current status:

- not the primary engineering frontier right now
- UI work should follow parity closure, not lead it

### `examples/native`

Purpose:

- canonical parity cases
- literal diagnostic examples

Current key files:

- `examples/native/deepsoil_gqh_5layer_baseline.yml`
- `examples/native/deepsoil_gqh_5layer_literal.yml`

### `tests`

Purpose:

- workbook importer coverage
- compare coverage
- constitutive-path regression
- web/API regression

Current parity-critical tests:

- workbook importer tests
- hysteresis path tests
- Newmark tangent/assembly tests
- parity docs/memory consistency tests

## Generated Outputs

These are runtime outputs, not source:

- `out/`
- `output/`
- `tmp/`
- `tmp_excel_inspect/`
- `out/ui/motions/`

Parity campaign artifact families currently expected under `output/baseline_iter/`:

- `single_element_*`
- `tangent_audit_*`
- `layer_sweep_*`
- `mode3_*`
- `mode4_*`
- selective `mode4_bottom*`
- `boundary_first_*`
- `boundary_delta_*`

Do not treat generated artifacts as the durable source of truth. The durable truth belongs in:

- `IMPLEMENTATION_STATUS.md`
- `DEEPSOIL_BASELINE_PARITY_RESEARCH.md`
- `PARITY_MEMORY.md`
- `parity_experiment_index.json`

## Legacy / De-emphasized

Older docs may still mention:

- OpenSees-centric workflows
- PM4 material families
- broad roadmap items outside parity closure

Do not use those as the current execution map unless the status docs explicitly reactivate them.
