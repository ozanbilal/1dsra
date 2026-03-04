import subprocess
import sys
from pathlib import Path

import dsra1d.interop.opensees.runner as runner_mod
from dsra1d.interop.opensees.runner import (
    OpenSeesProbeResult,
    probe_opensees_executable,
    resolve_opensees_executable,
    validate_backend_probe_requirements,
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
    assert probe.binary_sha256 == ""


def test_probe_opensees_executable_with_python_binary() -> None:
    probe = probe_opensees_executable(sys.executable, timeout_s=2)
    assert probe.resolved is not None
    assert probe.command
    assert probe.command[-1] == "-version"


def test_probe_opensees_executable_with_extra_args(tmp_path: Path) -> None:
    shim = tmp_path / "probe_shim.py"
    shim.write_text(
        "import sys\n"
        "if '-version' in sys.argv:\n"
        "    print('shim-version')\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    probe = probe_opensees_executable(
        sys.executable,
        extra_args=[str(shim)],
        timeout_s=2,
    )
    assert probe.available is True
    assert probe.command[-2] == str(shim)
    assert probe.command[-1] == "-version"
    assert len(probe.binary_sha256) == 64


def test_probe_opensees_executable_timeout_falls_back_to_tcl(monkeypatch) -> None:
    calls: list[list[str]] = []

    def _fake_run(cmd, **kwargs):
        calls.append([str(x) for x in cmd])
        if cmd[-1] == "-version":
            raise subprocess.TimeoutExpired(cmd=cmd, timeout=1)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="OpenSees 3.8.0\n", stderr="")

    monkeypatch.setattr(runner_mod.subprocess, "run", _fake_run)
    probe = probe_opensees_executable(sys.executable, timeout_s=1)
    assert probe.available is True
    assert probe.version.startswith("OpenSees")
    assert len(calls) >= 2
    assert calls[0][-1] == "-version"
    assert calls[1][-1].endswith(".tcl")


def test_validate_backend_probe_requirements_ok() -> None:
    probe = OpenSeesProbeResult(
        available=True,
        resolved=Path(sys.executable),
        version="OpenSees 3.7.0",
        stdout="",
        stderr="",
        command=[sys.executable, "-version"],
        binary_sha256="a" * 64,
    )
    errors = validate_backend_probe_requirements(
        probe,
        require_version_regex=r"OpenSees\s+3\.7",
        require_binary_sha256="a" * 64,
    )
    assert errors == []


def test_validate_backend_probe_requirements_failures() -> None:
    probe = OpenSeesProbeResult(
        available=True,
        resolved=Path(sys.executable),
        version="OpenSees 3.6.0",
        stdout="",
        stderr="",
        command=[sys.executable, "-version"],
        binary_sha256="a" * 64,
    )
    errors = validate_backend_probe_requirements(
        probe,
        require_version_regex=r"OpenSees\s+3\.7",
        require_binary_sha256="b" * 64,
    )
    assert len(errors) == 2
