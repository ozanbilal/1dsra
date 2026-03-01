from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _script() -> Path:
    return Path(__file__).resolve().parents[1] / "scripts" / "check_release_tag.py"


def test_release_tag_script_accepts_current_version() -> None:
    proc = subprocess.run(
        [sys.executable, str(_script()), "--tag", "v0.1.0"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Release tag validated" in proc.stdout


def test_release_tag_script_rejects_mismatch() -> None:
    proc = subprocess.run(
        [sys.executable, str(_script()), "--tag", "v9.9.9"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    assert "mismatch" in proc.stderr.lower()
