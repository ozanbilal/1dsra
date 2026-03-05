from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _normalize_sha256(value: str) -> str:
    text = value.strip().strip("`").lower()
    if text.startswith("sha256:"):
        text = text.split(":", 1)[1].strip()
    return text


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _load_policy_fingerprint(policy_path: Path) -> str:
    try:
        payload = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive path for CI checks
        raise SystemExit(f"Failed to read policy YAML: {policy_path} ({exc})") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"Expected mapping in policy YAML: {policy_path}")
    return _normalize_sha256(str(payload.get("opensees_fingerprint", "")))


def _parse_matrix_rows(matrix_path: Path) -> list[dict[str, str]]:
    text = matrix_path.read_text(encoding="utf-8")
    lines = [ln.strip() for ln in text.splitlines()]
    header_idx = -1
    for idx, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        lower = line.lower()
        if "suite" in lower and "binary_fingerprint" in lower:
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
        rows.append({header_cells[i]: cells[i] for i in range(len(header_cells))})
    return rows


def _load_matrix_fingerprint(matrix_path: Path) -> str:
    rows = _parse_matrix_rows(matrix_path)
    if not rows:
        raise SystemExit(f"Scientific confidence matrix table could not be parsed: {matrix_path}")
    for row in rows:
        suite_value = str(row.get("suite", "")).strip("` ").lower()
        if suite_value == "opensees-parity":
            return _normalize_sha256(str(row.get("binary_fingerprint", "")))
    raise SystemExit("Scientific confidence matrix missing `opensees-parity` row.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Check OpenSees fingerprint alignment across CI expected SHA, "
            "release_signoff policy, and scientific confidence matrix."
        )
    )
    parser.add_argument(
        "--expected-sha",
        required=True,
        help="Expected OpenSees sha256 (typically DSRA1D_CI_OPENSEES_SHA256).",
    )
    parser.add_argument(
        "--policy",
        default=Path("benchmarks/policies/release_signoff.yml"),
        type=Path,
        help="Path to release signoff policy YAML.",
    )
    parser.add_argument(
        "--matrix",
        default=Path("SCIENTIFIC_CONFIDENCE_MATRIX.md"),
        type=Path,
        help="Path to scientific confidence matrix markdown.",
    )
    args = parser.parse_args()

    expected_sha = _normalize_sha256(args.expected_sha)
    _require(bool(expected_sha), "expected sha256 is empty")
    _require(
        SHA256_RE.fullmatch(expected_sha) is not None,
        "expected sha256 must be 64-hex",
    )

    policy_path = args.policy
    _require(policy_path.exists(), f"policy path does not exist: {policy_path}")
    policy_sha = _load_policy_fingerprint(policy_path)
    _require(bool(policy_sha), "policy opensees_fingerprint is empty")
    _require(
        SHA256_RE.fullmatch(policy_sha) is not None,
        "policy opensees_fingerprint must be 64-hex",
    )

    matrix_path = args.matrix
    _require(matrix_path.exists(), f"matrix path does not exist: {matrix_path}")
    matrix_sha = _load_matrix_fingerprint(matrix_path)
    _require(bool(matrix_sha), "matrix opensees-parity binary_fingerprint is empty")
    _require(
        SHA256_RE.fullmatch(matrix_sha) is not None,
        "matrix opensees-parity binary_fingerprint must be 64-hex",
    )

    _require(
        expected_sha == policy_sha,
        "expected sha256 must match benchmarks/policies/release_signoff.yml opensees_fingerprint",
    )
    _require(
        expected_sha == matrix_sha,
        (
            "expected sha256 must match SCIENTIFIC_CONFIDENCE_MATRIX.md "
            "opensees-parity binary_fingerprint"
        ),
    )

    print("Fingerprint alignment validated.")
    print(f"- expected : {expected_sha}")
    print(f"- policy   : {policy_sha} ({policy_path})")
    print(f"- matrix   : {matrix_sha} ({matrix_path})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
