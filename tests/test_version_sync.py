from __future__ import annotations

import re
import tomllib
from pathlib import Path

from dsra1d import __version__


def test_version_is_synchronized() -> None:
    root = Path(__file__).resolve().parents[1]

    pyproject_data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    pyproject_version = str(pyproject_data["project"]["version"])

    core_text = (root / "core" / "src" / "version.cpp").read_text(encoding="utf-8")
    match = re.search(r'return "([^"]+)";', core_text)
    assert match is not None
    core_version = match.group(1)

    assert pyproject_version == __version__ == core_version
