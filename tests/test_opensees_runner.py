import sys
from pathlib import Path

from dsra1d.interop.opensees.runner import (
    probe_opensees_executable,
    resolve_opensees_executable,
)


def test_resolve_opensees_executable_absolute_exists() -> None:
    exe = Path(sys.executable)
    resolved = resolve_opensees_executable(str(exe))
    assert resolved == exe


def test_resolve_opensees_executable_absolute_missing() -> None:
    missing = Path(sys.executable).parent / "definitely_missing_opensees_binary.exe"
    resolved = resolve_opensees_executable(str(missing))
    assert resolved is None


def test_probe_opensees_executable_missing() -> None:
    missing = "OPEN_SEES_DEF_MISSING_EXE"
    probe = probe_opensees_executable(missing, timeout_s=1)
    assert probe.available is False
    assert probe.resolved is None
    assert probe.version == "unknown"


def test_probe_opensees_executable_with_python_binary() -> None:
    probe = probe_opensees_executable(sys.executable, timeout_s=2)
    assert probe.resolved is not None
    assert probe.command
    assert probe.command[-1] == "-version"
