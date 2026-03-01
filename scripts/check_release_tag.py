from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

TAG_RE = re.compile(r"^v(\d+\.\d+\.\d+)$")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate that release tag matches project version."
    )
    parser.add_argument("--tag", required=True, help="Git tag name (e.g. v1.0.0)")
    args = parser.parse_args()

    match = TAG_RE.fullmatch(args.tag.strip())
    if match is None:
        raise SystemExit("Tag must be in form vX.Y.Z")
    tag_version = match.group(1)

    repo_root = Path(__file__).resolve().parents[1]
    pyproject = repo_root / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    project_version = str(data["project"]["version"])

    if project_version != tag_version:
        raise SystemExit(
            f"Release tag/version mismatch: tag={tag_version}, pyproject={project_version}"
        )

    print(f"Release tag validated: v{project_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
