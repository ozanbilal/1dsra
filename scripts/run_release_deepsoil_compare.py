from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from dsra1d.deepsoil_compare import compare_deepsoil_manifest


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _load_yaml_mapping(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive for CI/runtime
        raise SystemExit(f"Failed to read YAML: {path} ({exc})") from exc
    return payload if isinstance(payload, dict) else {}


def _policy_requires_deepsoil_compare(policy: dict[str, object]) -> bool:
    return any(
        bool(policy.get(key, False))
        for key in (
            "require_deepsoil_compare",
            "require_deepsoil_profile",
            "require_deepsoil_hysteresis",
        )
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run release DEEPSOIL parity batch if configured. "
            "If policy requires DEEPSOIL parity, missing manifest is treated as a hard error."
        )
    )
    parser.add_argument(
        "--campaign-dir",
        required=True,
        type=Path,
        help="Release-signoff campaign output directory.",
    )
    parser.add_argument(
        "--manifest",
        default=Path("benchmarks/policies/release_signoff_deepsoil_manifest.json"),
        type=Path,
        help="Release DEEPSOIL parity manifest path.",
    )
    parser.add_argument(
        "--policy",
        default=Path("benchmarks/policies/release_signoff.yml"),
        type=Path,
        help="Release signoff policy YAML path.",
    )
    args = parser.parse_args(argv)

    campaign_dir = args.campaign_dir
    campaign_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = args.manifest
    policy_path = args.policy

    policy = _load_yaml_mapping(policy_path)
    deepsoil_required = _policy_requires_deepsoil_compare(policy)

    if not manifest_path.exists():
        _require(
            not deepsoil_required,
            (
                "DEEPSOIL release compare manifest required by policy but not found: "
                f"{manifest_path}"
            ),
        )
        print(f"DEEPSOIL release compare not configured; skipping ({manifest_path}).")
        return 0

    result = compare_deepsoil_manifest(manifest_path, out_dir=campaign_dir)
    print("DEEPSOIL release compare completed.")
    print(f"- Manifest: {manifest_path}")
    print(f"- Cases: {result.total_cases}")
    print(f"- Passed: {result.passed_cases}")
    print(f"- Failed: {result.failed_cases}")
    if result.artifacts is not None:
        print(f"- JSON: {result.artifacts.json_path}")
        print(f"- Markdown: {result.artifacts.markdown_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
