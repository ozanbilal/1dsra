from __future__ import annotations

import argparse
import re
from pathlib import Path

TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")
VERSION_HEADING_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]", flags=re.MULTILINE)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate changelog structure and release section for a tag."
    )
    parser.add_argument("--tag", required=True, help="Git tag, e.g. v1.0.0")
    args = parser.parse_args()

    tag = args.tag.strip()
    match = TAG_RE.fullmatch(tag)
    if match is None:
        raise SystemExit("Tag must be in form vX.Y.Z")
    version = match.group(1)

    repo_root = Path(__file__).resolve().parents[1]
    changelog = repo_root / "CHANGELOG.md"
    text = changelog.read_text(encoding="utf-8")

    if "## [Unreleased]" not in text:
        raise SystemExit("CHANGELOG.md must contain an [Unreleased] section.")

    versions = VERSION_HEADING_RE.findall(text)
    if version not in versions:
        raise SystemExit(f"CHANGELOG.md does not contain a section for version [{version}].")

    print(f"Changelog validated for release v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
