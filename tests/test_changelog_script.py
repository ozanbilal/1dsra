from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _script() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "check_changelog.py"


def test_changelog_script_accepts_current_version() -> None:
    proc = subprocess.run(
        [sys.executable, str(_script()), "--tag", "v0.1.0"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Changelog validated" in proc.stdout


def test_changelog_script_rejects_missing_version() -> None:
    proc = subprocess.run(
        [sys.executable, str(_script()), "--tag", "v9.9.9"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "does not contain a section" in proc.stderr
