import sys
from pathlib import Path

from dsra1d.interop.opensees.runner import resolve_opensees_executable


def test_resolve_opensees_executable_absolute_exists() -> None:
    exe = Path(sys.executable)
    resolved = resolve_opensees_executable(str(exe))
    assert resolved == exe


def test_resolve_opensees_executable_absolute_missing() -> None:
    missing = Path(sys.executable).parent / "definitely_missing_opensees_binary.exe"
    resolved = resolve_opensees_executable(str(missing))
    assert resolved is None
