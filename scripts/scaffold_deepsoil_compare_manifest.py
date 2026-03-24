from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any

DEFAULTS: dict[str, float] = {
    "surface_corrcoef_min": 0.95,
    "surface_nrmse_max": 0.20,
    "psa_nrmse_max": 0.20,
    "pga_pct_diff_abs_max": 20.0,
}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = lowered.strip("-")
    return lowered or "case"


def _iter_run_dirs(root: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in root.rglob("run-*")
            if path.is_dir() and (path / "run_meta.json").exists()
        ]
    )


def _build_case_name(run_dir: Path, run_meta: dict[str, Any], used_names: set[str]) -> str:
    backend = str(run_meta.get("solver_backend", "")).strip().lower()
    parent = run_dir.parent.name
    raw_name = f"{parent}-{backend}" if backend else parent
    name = _slugify(raw_name)
    if name not in used_names:
        used_names.add(name)
        return name

    suffix = 2
    while f"{name}-{suffix}" in used_names:
        suffix += 1
    resolved = f"{name}-{suffix}"
    used_names.add(resolved)
    return resolved


def _is_complete_run(run_dir: Path, run_meta: dict[str, Any]) -> bool:
    if str(run_meta.get("status", "")).lower() != "ok":
        return False
    return (run_dir / "results.h5").exists()


def _relativize(path: Path, base: Path) -> str:
    return os.path.relpath(path, base).replace("\\", "/")


def scaffold_manifest(
    runs_root: Path,
    out_path: Path,
    deepsoil_reference_root: Path,
    *,
    include_profile: bool,
    include_hysteresis: bool,
    include_incomplete: bool,
) -> dict[str, object]:
    if not runs_root.exists():
        raise FileNotFoundError(f"Runs root does not exist: {runs_root}")

    used_names: set[str] = set()
    manifest_dir = out_path.parent
    cases: list[dict[str, object]] = []

    for run_dir in _iter_run_dirs(runs_root):
        run_meta = _read_json(run_dir / "run_meta.json")
        if not include_incomplete and not _is_complete_run(run_dir, run_meta):
            continue

        case_name = _build_case_name(run_dir, run_meta, used_names)
        run_value = _relativize(run_dir, manifest_dir)

        reference_base = deepsoil_reference_root / case_name
        ref_root = _relativize(reference_base, manifest_dir)

        case: dict[str, object] = {
            "name": case_name,
            "run": run_value,
            "surface_csv": f"{ref_root}/surface.csv",
            "psa_csv": f"{ref_root}/psa.csv",
        }
        if include_profile:
            case["profile_csv"] = f"{ref_root}/profile.csv"
        if include_hysteresis:
            case["hysteresis_csv"] = f"{ref_root}/hysteresis_layer1.csv"
            case["hysteresis_layer"] = 0
        cases.append(case)

    payload: dict[str, object] = {
        "defaults": DEFAULTS,
        "cases": cases,
        "_meta": {
            "generated_from_runs_root": str(runs_root),
            "generated_coverage": "complete_only" if not include_incomplete else "all_runs",
            "reference_root": str(deepsoil_reference_root),
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Scaffold a DEEPSOIL compare batch manifest from existing "
            "StrataWave run directories."
        )
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=Path("examples/output/deepsoil_equivalent/smoke"),
        help="Root directory to scan for run-* folders.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("examples/parity/deepsoil_compare_manifest.generated.json"),
        help="Output manifest path.",
    )
    parser.add_argument(
        "--deepsoil-reference-root",
        type=Path,
        default=Path("references/deepsoil"),
        help="Root directory where DEEPSOIL-exported CSV folders will live.",
    )
    parser.add_argument(
        "--no-profile",
        action="store_true",
        help="Do not include profile.csv placeholders.",
    )
    parser.add_argument(
        "--no-hysteresis",
        action="store_true",
        help="Do not include hysteresis placeholder fields.",
    )
    parser.add_argument(
        "--include-incomplete",
        action="store_true",
        help="Include runs even when run_meta status/results do not indicate a complete run.",
    )
    args = parser.parse_args(argv)

    payload = scaffold_manifest(
        runs_root=args.runs_root.resolve(),
        out_path=args.out.resolve(),
        deepsoil_reference_root=args.deepsoil_reference_root.resolve(),
        include_profile=not args.no_profile,
        include_hysteresis=not args.no_hysteresis,
        include_incomplete=args.include_incomplete,
    )
    print(
        json.dumps(
            {
                "manifest_path": str(args.out.resolve()),
                "case_count": len(payload["cases"]),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
