# AGENTS.md

## Current Objective

The project is currently optimizing for one thing:

- close DeepSoil baseline parity before adding new features

Do not treat this repo as a broad feature-expansion project right now.

## Read These First

Before starting a new parity iteration, read in this order:

1. `IMPLEMENTATION_STATUS.md`
2. `DEEPSOIL_BASELINE_PARITY_RESEARCH.md`
3. `PARITY_MEMORY.md`
4. `parity_experiment_index.json`
5. `AGENTS.md`

## Canonical Baseline Case

Primary engineering case:

- `examples/native/deepsoil_gqh_5layer_baseline.yml`

Primary DeepSoil workbook:

- `tests/Results_profile_0_motion_Kocaeli.xlsx`

Secondary cross-check workbook:

- `tests/Results_profile_0_motion_Kocaeli-EL.xlsx`

## What Counts as a Valid Parity Iteration

A valid parity iteration should:

1. preserve baseline semantics
   - `nonlinear`
   - `rigid`
   - `outcrop`
   - `frequency_independent`
   - `newmark`
   - `viscous_damping_update = false`

2. rerun the canonical case

3. regenerate compare output against the workbook

4. judge the iteration on response metrics, not parameter similarity

Primary compare signals:

- `surface_nrmse`
- `psa_nrmse`
- `surface_psa_peak_period_diff_pct`
- `gamma_max_nrmse`
- `secant_g_over_gmax_nrmse`
- `stress_path_nrmse`
- `loop_energy_pct_diff`

## Current Mismatch Interpretation

The canonical rigid/outcrop baseline gap should currently be interpreted as:

- not primarily an input `dt` problem
- not primarily a rigid/outcrop semantic problem
- not primarily a plotting or displacement-animation problem
- not primarily a monotonic `theta` / backbone problem
- not primarily a simple tangent-floor or local tangent-restore deficiency

The likely remaining cause there is now:

- F_mrdf evolution semantics
- translated-branch curvature semantics only insofar as they improve the multi-layer response path
- branch-progress / reversal-state dependent translated-branch behavior only when coupled to a better multi-layer target
- multi-layer constitutive evolution across the full column
- previous-cycle memory only if supported by new evidence
- active tangent evolution and how that tangent reaches the global solver

The active boundary-first verification gap should currently be interpreted separately:

- acceptance pair is `elastic_halfspace + outcrop` vs `rigid + within`
- DeepSoil `deepsoilout.db3` from the supplied batch output is the primary truth surface
- peak RS ratio, peak-period shift, surface PGA, and surface PGD direction now match DeepSoil
- the directional gate is passed
- the remaining work is first-order boundary magnitude closure
- do not reopen new constitutive families before this boundary-first mismatch is cleaner

## Repo Truth From Recent Iterations

Treat these as already learned:

- `mode3` did not reduce peak-period drift and regressed general parity
- `mode4` gave a small non-accepting improvement but did not reduce peak-period drift
- deep-layer tangent restore alone does not move the `+11.732%` peak-period signature
- standalone `mode5` F_mrdf progression improved local Layer 1 replay but regressed full compare and did not reduce peak-period drift
- `mode6` and `mode7` translated-curvature families improved local Layer 1 replay but regressed full compare and did not reduce peak-period drift
- DeepSoil v7.1 notes bedrock damping ratio has no effect in time-domain analyses; elastic-halfspace parity should focus on impedance semantics, not standalone bedrock `% damping`
- `rigid+outcrop` and `elastic_halfspace+outcrop` are expected to differ strongly in GeoWave because rigid-base outcrop input is halved before application; do not confuse that with a pure boundary-only effect
- on the canonical Kocaeli motion, `elastic_halfspace+outcrop` is about `1.308x` of `rigid+outcrop` in max surface PSA but only about `0.981x` of `rigid+within`; the cleaner residual boundary signature is a surface peak-period increase of about `+5.704%`
- on the canonical Kocaeli motion, elastic-halfspace incident force and dashpot reaction nearly cancel (`dashpot_to_incident_rms_ratio ≈ 0.989`, correlation `≈ 0.994`); the residual net boundary traction RMS is only about `10.85%` of incident-force RMS
- on the canonical Kocaeli motion, the residual net boundary traction and elastic-halfspace surface response share the same dominant frequency (`≈ 5.3667 Hz`, `T ≈ 0.1863 s`); treat the remaining halfspace effect as a frequency-selective residual traction problem
- after semantic locking and relative-displacement alignment, GeoWave now matches DeepSoil direction for `elastic_halfspace+outcrop` vs `rigid+within` in peak RS ratio, peak-period shift, surface PGA, and surface PGD
- the boundary-first pair has passed the directional gate; the next task is first-order magnitude closure
- current magnitude audit says the remaining boundary-first gap is driven mainly by under-amplified `rigid+within`; the elastic case is closer to DeepSoil
- direct rigid/elastic case-truth profile audit now shows the rigid case is not simply under-excited:
  - rigid-within `gamma_max` is already close to DeepSoil while `max_stress_ratio` and profile PGA stay low
  - the reusable rigid-within all-layer truth+tangent audit now shows Layer 5 as the dominant mean-compliance carrier (`~0.2097`) and keeps Layers 2-5 in the same soft compliance band
  - the derived stress/secant proxy audit shows the stress deficit is full-column (`~0.75x`) and the secant deficit is strongest in the upper-to-mid column, so do not reduce the remaining mismatch to deepest-layer compliance alone
  - after the corrected layer alignment, `mean kt / ref secant` is already high on average while `min kt / ref secant` and `tau peak proxy` remain low; treat the next rigid-case closure step as cyclic stress mobilization / low-end tangent evolution, not average stiffness alone
  - use that as the handoff point back into rigid-case constitutive stress/tangent auditing

## Recommended Debug Order

Use this order unless there is strong evidence to do otherwise:

1. read the living dossier and memory first
2. check whether the same experiment family was already falsified
3. if boundary verification is the active problem, use the DeepSoil semantics pair `elastic_halfspace + outcrop` vs `rigid + within`
4. keep `rigid+outcrop` vs `elastic_halfspace+outcrop` only as a secondary UI report
5. close boundary-first first-order magnitude differences before opening another constitutive family
6. only after boundary-first closure, define the multi-layer target before shaping another local branch family
7. run single-element replay if constitutive behavior changed
8. run branch/tangent or layer-sweep logging
9. rerun workbook compare
10. only then consider UI/result follow-up

## Do Not Waste Time On

Avoid these as the main parity strategy:

- endless scalar `reload_factor` sweeps
- rerunning unchanged `mode3` reversal-tangent-preserving experiments
- rerunning unchanged selective deep-layer `mode4_bottom*` experiments
- rerunning unchanged standalone `mode5` branch-progress F_mrdf experiments
- rerunning unchanged standalone `mode6` or `mode7` translated-curvature experiments
- re-debugging rigid/outcrop semantics as the primary cause
- trying to fix `+11.7%` peak-period drift with damping-matrix tweaks alone
- trying to fix time-domain elastic-halfspace parity by tuning bedrock `% damping` alone
- retuning monotonic theta sets before unload/reload behavior is closed
- treating `rigid+outcrop` vs `elastic_halfspace+outcrop` as the acceptance pair for boundary parity after the semantic-locking work
- reopening new mode3/4/5/6/7 constitutive families while the boundary-first magnitude gap is still open

## Key Working Paths

Important source files:

- `python/dsra1d/nonlinear.py`
- `python/dsra1d/newmark_nonlinear.py`
- `python/dsra1d/motion/excitation.py`
- `python/dsra1d/materials/hysteretic.py`
- `python/dsra1d/materials/mrdf.py`
- `python/dsra1d/deepsoil_excel.py`
- `python/dsra1d/deepsoil_compare.py`
- `python/dsra1d/constitutive_debug.py`

Important runtime/generated paths:

- generated motion cache:
  - `out/ui/motions/`
- runtime outputs:
  - `out/`
- parity iteration outputs:
  - `output/baseline_iter/`

Important note:

- `out/ui/motions/` is for uploaded/converted/generated motion files
- it is not part of the motion-library scan
- the motion library scans only user-provided folders and does not recurse into subfolders

## Outputs That Should Not Be Committed

Do not intentionally commit generated debug artifacts unless explicitly curating them:

- `out/`
- `output/`
- `tmp/`
- `tmp_excel_inspect/`
- ad-hoc rendered images
- workbook-derived intermediate bundles
- motion cache files under `out/ui/motions/`

## Decision Guidance For Future Agents

If you are deciding where to spend effort:

- prefer boundary-first delta closure over new constitutive family work while the elastic-vs-rigid magnitude gap is still open
- after boundary-first closure, prefer constitutive parity work over UI polish
- prefer compare-driven iteration over parameter-table matching
- prefer status/doc truth in `IMPLEMENTATION_STATUS.md` over older roadmap language elsewhere
- prefer a new hypothesis family over repeating a family already marked `falsified` in `parity_experiment_index.json`
