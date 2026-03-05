from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _load_json(path: Path) -> dict[str, object]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path for CI checks
        raise SystemExit(f"Failed to read JSON: {path} ({exc})") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Expected JSON object: {path}")
    return data


def _parse_matrix_rows(matrix_path: Path) -> list[dict[str, str]]:
    text = matrix_path.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines()]
    header_idx = -1
    for idx, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        lower = line.lower()
        if "suite" in lower and "reference_basis" in lower and "confidence_tier" in lower:
            header_idx = idx
            break
    if header_idx < 0 or header_idx + 1 >= len(lines):
        return []
    header_cells = [cell.strip() for cell in lines[header_idx].strip("|").split("|")]
    rows: list[dict[str, str]] = []
    for line in lines[header_idx + 2 :]:
        if not line.startswith("|"):
            if rows:
                break
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != len(header_cells):
            continue
        row = {header_cells[i]: cells[i] for i in range(len(header_cells))}
        if row:
            rows.append(row)
    return rows


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _normalize_sha256(value: str) -> str:
    text = value.strip().lower()
    if text.startswith("sha256:"):
        text = text.split(":", 1)[1].strip()
    return text


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Machine-check release signoff artifacts and scientific confidence matrix.",
    )
    parser.add_argument(
        "--campaign-dir",
        required=True,
        type=Path,
        help="Directory containing release-signoff outputs.",
    )
    parser.add_argument(
        "--matrix",
        default=Path("SCIENTIFIC_CONFIDENCE_MATRIX.md"),
        type=Path,
        help="Scientific confidence matrix markdown path.",
    )
    parser.add_argument(
        "--require-fingerprint",
        action="store_true",
        help="Require non-empty OpenSees fingerprint fields in summary + matrix.",
    )
    args = parser.parse_args()

    campaign_dir = args.campaign_dir
    _require(
        campaign_dir.exists() and campaign_dir.is_dir(),
        f"Invalid campaign dir: {campaign_dir}",
    )

    benchmark_path = campaign_dir / "benchmark_release-signoff.json"
    verify_path = campaign_dir / "verify_batch_report.json"
    summary_path = campaign_dir / "campaign_summary.json"
    summary_md_path = campaign_dir / "campaign_summary.md"
    required_files = [benchmark_path, verify_path, summary_path, summary_md_path]
    missing = [str(path) for path in required_files if not path.exists()]
    _require(not missing, f"Missing required release artifacts: {', '.join(missing)}")

    benchmark = _load_json(benchmark_path)
    verify = _load_json(verify_path)
    summary = _load_json(summary_path)

    _require(
        str(benchmark.get("suite", "")) == "release-signoff",
        "Benchmark suite must be release-signoff.",
    )
    _require(bool(benchmark.get("all_passed", False)), "Benchmark all_passed must be true.")
    _require(bool(verify.get("ok", False)), "verify_batch_report.ok must be true.")

    policy_obj = summary.get("policy")
    policy = policy_obj if isinstance(policy_obj, dict) else {}
    campaign_policy_obj = policy.get("campaign")
    campaign_policy = campaign_policy_obj if isinstance(campaign_policy_obj, dict) else {}
    _require(
        bool(campaign_policy.get("passed", False)),
        "campaign_summary policy.campaign.passed must be true.",
    )

    signoff_obj = summary.get("signoff")
    signoff = signoff_obj if isinstance(signoff_obj, dict) else {}
    _require(bool(signoff.get("strict_signoff", False)), "signoff.strict_signoff must be true.")
    _require(bool(signoff.get("passed", False)), "signoff.passed must be true.")
    conditions_obj = signoff.get("conditions")
    conditions = conditions_obj if isinstance(conditions_obj, dict) else {}
    _require(
        bool(conditions.get("backend_probe_not_assumed", False)),
        "signoff.conditions.backend_probe_not_assumed must be true.",
    )
    observed_obj = signoff.get("observed")
    observed = observed_obj if isinstance(observed_obj, dict) else {}
    _require(
        not bool(observed.get("backend_probe_assumed_available", False)),
        "signoff.observed.backend_probe_assumed_available must be false.",
    )

    if args.require_fingerprint:
        observed_sha = _normalize_sha256(str(observed.get("backend_probe_sha256", "")))
        _require(bool(observed_sha), "signoff.observed.backend_probe_sha256 must be non-empty.")
        _require(
            SHA256_RE.fullmatch(observed_sha) is not None,
            "signoff.observed.backend_probe_sha256 must be 64-hex sha256.",
        )

    matrix_path = args.matrix
    _require(matrix_path.exists(), f"Scientific confidence matrix not found: {matrix_path}")
    matrix_rows = _parse_matrix_rows(matrix_path)
    _require(bool(matrix_rows), "Scientific confidence matrix table could not be parsed.")

    parity_row = None
    for row in matrix_rows:
        suite_value = str(row.get("suite", "")).strip("` ").lower()
        if suite_value == "opensees-parity":
            parity_row = row
            break
    _require(parity_row is not None, "Matrix must include opensees-parity row.")

    for key in (
        "reference_basis",
        "tolerance_policy",
        "binary_fingerprint",
        "last_verified_utc",
        "confidence_tier",
    ):
        value = str(parity_row.get(key, "")).strip()
        _require(bool(value), f"Matrix opensees-parity row has empty field: {key}")

    if args.require_fingerprint:
        matrix_fingerprint = _normalize_sha256(
            str(parity_row.get("binary_fingerprint", "")).strip("` ")
        )
        _require(
            SHA256_RE.fullmatch(matrix_fingerprint) is not None,
            (
                "Matrix opensees-parity binary_fingerprint must be a "
                "64-hex sha256 for release signoff."
            ),
        )
        _require(
            matrix_fingerprint == observed_sha,
            "Matrix opensees-parity binary_fingerprint must match signoff observed backend sha256.",
        )

    print("Release signoff artifacts validated.")
    print(f"- Campaign dir: {campaign_dir}")
    print(f"- Summary: {summary_path}")
    print(f"- Matrix row: opensees-parity in {matrix_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
