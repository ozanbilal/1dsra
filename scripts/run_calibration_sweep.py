"""Run a calibration sweep: execute each candidate config and compare against DEEPSOIL reference.

Reads sweep_manifest.json, runs GeoWave nonlinear analysis for each candidate,
then compares against DEEPSOIL Example 5A reference data and ranks results.

Usage:
    python scripts/run_calibration_sweep.py [--sweep-dir <dir>] [--motion <path>] [--top-n 10]

Outputs:
    <sweep_dir>/sweep_results.json   (ranked results by PSA NRMSE)
    <sweep_dir>/sweep_results.md     (human-readable summary)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from dsra1d.config import load_project_config  # noqa: E402
from dsra1d.deepsoil_compare import compare_deepsoil_run  # noqa: E402
from dsra1d.pipeline import RunResult, load_motion, run_analysis  # noqa: E402

# Default paths for Example 5A reference data
DEFAULT_MOTION = (
    REPO_ROOT
    / "output"
    / "pdf"
    / "validation"
    / "deepsoil_examples"
    / "kobe_motion_dt0025.csv"
)
DEFAULT_DEEPSOIL_SURFACE = (
    REPO_ROOT
    / "output"
    / "pdf"
    / "validation"
    / "deepsoil_examples"
    / "nonlinear_5a_rigid"
    / "deepsoil_ref"
    / "surface.csv"
)
DEFAULT_DEEPSOIL_PSA = (
    REPO_ROOT
    / "output"
    / "pdf"
    / "validation"
    / "deepsoil_examples"
    / "nonlinear_5a_rigid"
    / "deepsoil_ref"
    / "psa.csv"
)


def _find_motion() -> Path:
    """Find the Example 5A motion file."""
    if DEFAULT_MOTION.exists():
        return DEFAULT_MOTION
    candidates = [
        REPO_ROOT / "examples" / "deepsoil_equivalent" / "motions" / "example_5a.csv",
        REPO_ROOT / "examples" / "motions" / "sample_motion.csv",
    ]
    for c in candidates:
        if c.exists():
            return c
    raise FileNotFoundError(
        "Cannot find Example 5A motion CSV. "
        f"Provide --motion argument or place motion at {DEFAULT_MOTION}"
    )


def run_single_case(
    config_path: Path,
    motion_path: Path,
    output_root: Path,
) -> Path | None:
    """Run a single GeoWave analysis. Returns run directory or None on failure."""
    try:
        config = load_project_config(config_path)
        dt = config.analysis.dt
        motion = load_motion(motion_path, dt=dt, unit=config.motion.units)
        result: RunResult = run_analysis(
            config=config,
            motion=motion,
            output_dir=str(output_root),
        )
        run_dir = Path(result.output_dir)
        if run_dir.exists():
            return run_dir
        # Fallback: find run-* directory under output_root
        run_dirs = sorted(output_root.glob("run-*"))
        return run_dirs[-1] if run_dirs else None
    except Exception as exc:
        print(f"  FAILED: {exc}")
        return None


def compare_case(
    run_dir: Path,
    deepsoil_surface: Path,
    deepsoil_psa: Path,
) -> dict | None:
    """Compare a run against DEEPSOIL reference. Returns flat metrics dict or None."""
    try:
        result = compare_deepsoil_run(
            run_dir=run_dir,
            surface_csv=deepsoil_surface,
            psa_csv=deepsoil_psa,
        )
        return {
            "psa_nrmse": result.psa_nrmse,
            "surface_nrmse": result.surface_nrmse,
            "surface_corrcoef": result.surface_corrcoef,
            "pga_ratio": result.pga_ratio,
            "pga_pct_diff": result.pga_pct_diff,
            "surface_rmse": result.surface_rmse_m_s2,
            "psa_rmse": result.psa_rmse_m_s2,
            "warnings": result.warnings,
        }
    except Exception as exc:
        print(f"  COMPARE FAILED: {exc}")
        return None


def run_sweep(
    sweep_dir: Path,
    motion_path: Path | None = None,
    deepsoil_surface: Path | None = None,
    deepsoil_psa: Path | None = None,
    top_n: int = 10,
) -> None:
    """Execute full sweep and rank results."""
    manifest_path = sweep_dir / "sweep_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"No sweep_manifest.json at {sweep_dir}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    motion = Path(motion_path) if motion_path else _find_motion()
    ds_surface = Path(deepsoil_surface) if deepsoil_surface else DEFAULT_DEEPSOIL_SURFACE
    ds_psa = Path(deepsoil_psa) if deepsoil_psa else DEFAULT_DEEPSOIL_PSA

    if not ds_surface.exists():
        raise FileNotFoundError(f"DEEPSOIL surface reference not found: {ds_surface}")
    if not ds_psa.exists():
        raise FileNotFoundError(f"DEEPSOIL PSA reference not found: {ds_psa}")

    print(f"Motion: {motion}")
    print(f"DEEPSOIL surface: {ds_surface}")
    print(f"DEEPSOIL PSA: {ds_psa}")

    cases = manifest["cases"]
    results: list[dict] = []

    for i, case in enumerate(cases):
        sid = case["sweep_id"]
        config_path = Path(case["config_path"])
        case_dir = config_path.parent
        output_root = case_dir / "output"

        print(f"\n[{i + 1}/{len(cases)}] {sid} ...")

        run_dir = run_single_case(config_path, motion, output_root)
        if run_dir is None:
            results.append({**case, "status": "run_failed", "psa_nrmse": None, "surface_nrmse": None})
            continue

        metrics = compare_case(run_dir, ds_surface, ds_psa)
        if metrics is None:
            results.append({
                **case,
                "status": "compare_failed",
                "run_dir": str(run_dir),
                "psa_nrmse": None,
                "surface_nrmse": None,
            })
            continue

        psa_nrmse = metrics.get("psa_nrmse")
        surface_nrmse = metrics.get("surface_nrmse")
        surface_corr = metrics.get("surface_corrcoef")
        pga_ratio = metrics.get("pga_ratio")

        results.append({
            **case,
            "status": "ok",
            "run_dir": str(run_dir),
            "psa_nrmse": psa_nrmse,
            "surface_nrmse": surface_nrmse,
            "surface_corrcoef": surface_corr,
            "pga_ratio": pga_ratio,
        })
        if psa_nrmse is not None and surface_nrmse is not None:
            corr_str = f"{surface_corr:.4f}" if surface_corr is not None else "n/a"
            print(f"  PSA NRMSE={psa_nrmse:.4f}  Surface NRMSE={surface_nrmse:.4f}  Corr={corr_str}")

    # Rank by PSA NRMSE (lower is better)
    ranked = sorted(
        [r for r in results if r.get("psa_nrmse") is not None],
        key=lambda r: r["psa_nrmse"],
    )
    failed = [r for r in results if r.get("psa_nrmse") is None]

    # Write JSON results
    output = {
        "total_candidates": len(cases),
        "completed": len(ranked),
        "failed": len(failed),
        "top_n": min(top_n, len(ranked)),
        "best_case": ranked[0] if ranked else None,
        "ranked": ranked[:top_n],
        "all_results": results,
    }
    results_json = sweep_dir / "sweep_results.json"
    with open(results_json, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)

    # Write Markdown summary
    results_md = sweep_dir / "sweep_results.md"
    with open(results_md, "w", encoding="utf-8") as f:
        f.write("# MKZ Calibration Sweep Results\n\n")
        f.write(f"Total candidates: {len(cases)}\n")
        f.write(f"Completed: {len(ranked)}\n")
        f.write(f"Failed: {len(failed)}\n\n")

        if ranked:
            f.write("## Top Results (by PSA NRMSE)\n\n")
            f.write("| Rank | Sweep ID | RF | GRS | Dmax | Subs | PSA NRMSE | Surf NRMSE | Corr | PGA Ratio |\n")
            f.write("|------|----------|-----|------|------|------|-----------|------------|------|-----------|\n")
            for idx, r in enumerate(ranked[:top_n]):
                corr = r.get("surface_corrcoef")
                pga = r.get("pga_ratio")
                corr_s = f"{corr:.4f}" if corr is not None else "n/a"
                pga_s = f"{pga:.3f}" if pga is not None else "n/a"
                f.write(
                    f"| {idx + 1} | `{r['sweep_id']}` "
                    f"| {r['reload_factor']:.2f} "
                    f"| {r['gamma_ref_scale']:.2f} "
                    f"| {r['damping_max']:.2f} "
                    f"| {r['nonlinear_substeps']} "
                    f"| {r['psa_nrmse']:.4f} "
                    f"| {r['surface_nrmse']:.4f} "
                    f"| {corr_s} "
                    f"| {pga_s} |\n"
                )
            f.write(f"\n**Best case:** `{ranked[0]['sweep_id']}`\n")
            f.write(f"- PSA NRMSE: {ranked[0]['psa_nrmse']:.4f}\n")
            f.write(f"- Surface NRMSE: {ranked[0]['surface_nrmse']:.4f}\n")

        if failed:
            f.write(f"\n## Failed Cases ({len(failed)})\n\n")
            for r in failed:
                f.write(f"- `{r['sweep_id']}`: {r['status']}\n")

    print(f"\nResults: {results_json}")
    print(f"Summary: {results_md}")
    if ranked:
        print(f"\nBest: {ranked[0]['sweep_id']} (PSA NRMSE={ranked[0]['psa_nrmse']:.4f})")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run calibration sweep and compare against DEEPSOIL reference."
    )
    parser.add_argument(
        "--sweep-dir",
        type=Path,
        default=REPO_ROOT / "output" / "pdf" / "validation" / "deepsoil_examples" / "calibration_sweep_pilot",
        help="Directory containing sweep_manifest.json.",
    )
    parser.add_argument("--motion", type=Path, default=None, help="Motion CSV path.")
    parser.add_argument("--deepsoil-surface", type=Path, default=None, help="DEEPSOIL surface CSV.")
    parser.add_argument("--deepsoil-psa", type=Path, default=None, help="DEEPSOIL PSA CSV.")
    parser.add_argument("--top-n", type=int, default=10, help="Number of top results to show.")
    args = parser.parse_args()

    run_sweep(
        sweep_dir=args.sweep_dir,
        motion_path=args.motion,
        deepsoil_surface=args.deepsoil_surface,
        deepsoil_psa=args.deepsoil_psa,
        top_n=args.top_n,
    )


if __name__ == "__main__":
    main()
