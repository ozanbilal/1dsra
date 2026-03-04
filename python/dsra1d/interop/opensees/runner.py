from __future__ import annotations

import hashlib
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class OpenSeesExecutionError(RuntimeError):
    """Raised when OpenSees execution fails."""

    def __init__(
        self,
        message: str,
        *,
        returncode: int | None = None,
        stdout: str = "",
        stderr: str = "",
        command: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.command = command or []


@dataclass(slots=True)
class OpenSeesRunOutput:
    returncode: int
    stdout: str
    stderr: str
    command: list[str]


@dataclass(slots=True)
class OpenSeesProbeResult:
    available: bool
    resolved: Path | None
    version: str
    stdout: str
    stderr: str
    command: list[str]
    binary_sha256: str


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def resolve_opensees_executable(executable: str) -> Path | None:
    candidate = Path(executable)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    resolved = shutil.which(executable)
    return Path(resolved) if resolved is not None else None


def _decode_timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")
    return value


def _first_non_empty_line(*values: str) -> str:
    for value in values:
        if not value:
            continue
        for line in value.splitlines():
            text = line.strip()
            if text:
                return text
    return "unknown"


def _run_probe_command(
    cmd: list[str],
    *,
    timeout_s: int,
) -> tuple[bool, str, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            check=False,
            timeout=timeout_s,
            capture_output=True,
            text=True,
            stdin=subprocess.DEVNULL,
        )
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        version_line = _first_non_empty_line(stdout, stderr)
        return proc.returncode == 0, version_line, stdout, stderr
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_timeout_stream(exc.stdout)
        stderr = _decode_timeout_stream(exc.stderr)
        version_line = _first_non_empty_line(stdout, stderr)
        timeout_msg = (
            f"Command timed out after {timeout_s} seconds: {' '.join(str(x) for x in cmd)}"
        )
        if stderr:
            stderr = f"{stderr}\n{timeout_msg}".strip()
        else:
            stderr = timeout_msg
        # If a recognizable banner/version line appears before timeout, treat as available.
        banner = f"{stdout}\n{stderr}".lower()
        available = "opensees" in banner and version_line != "unknown"
        return available, version_line, stdout, stderr


def _probe_with_tcl_script(
    resolved: Path,
    *,
    extra_args: list[str] | None,
    timeout_s: int,
) -> tuple[bool, str, str, str, list[str]]:
    with tempfile.TemporaryDirectory(prefix="dsra1d_probe_") as tmpdir:
        script = Path(tmpdir) / "probe_version.tcl"
        script.write_text("puts [version]\nexit\n", encoding="utf-8")
        cmd = [str(resolved)]
        if extra_args:
            cmd.extend(extra_args)
        cmd.append(str(script))
        available, version_line, stdout, stderr = _run_probe_command(cmd, timeout_s=timeout_s)
        return available, version_line, stdout, stderr, cmd


def probe_opensees_executable(
    executable: str,
    extra_args: list[str] | None = None,
    timeout_s: int = 5,
) -> OpenSeesProbeResult:
    resolved = resolve_opensees_executable(executable)
    if resolved is None:
        return OpenSeesProbeResult(
            available=False,
            resolved=None,
            version="unknown",
            stdout="",
            stderr=f"OpenSees executable not found: {executable}",
            command=[],
            binary_sha256="",
        )

    version_cmd = [str(resolved)]
    if extra_args:
        version_cmd.extend(extra_args)
    version_cmd.append("-version")
    try:
        available, version_line, stdout, stderr = _run_probe_command(
            version_cmd,
            timeout_s=timeout_s,
        )
    except FileNotFoundError as exc:
        return OpenSeesProbeResult(
            available=False,
            resolved=resolved,
            version="unknown",
            stdout="",
            stderr=str(exc),
            command=version_cmd,
            binary_sha256="",
        )

    command = version_cmd
    if not available:
        try:
            fb_available, fb_version, fb_stdout, fb_stderr, fb_cmd = _probe_with_tcl_script(
                resolved,
                extra_args=extra_args,
                timeout_s=max(timeout_s, 8),
            )
        except FileNotFoundError as exc:
            fb_available = False
            fb_version = "unknown"
            fb_stdout = ""
            fb_stderr = str(exc)
            fb_cmd = version_cmd
        if fb_available:
            available = True
            version_line = fb_version
            stdout = fb_stdout
            stderr = fb_stderr
            command = fb_cmd
        elif version_line == "unknown":
            version_line = fb_version if fb_version != "unknown" else version_line
            if fb_stdout and not stdout:
                stdout = fb_stdout
            if fb_stderr:
                stderr = f"{stderr}\n{fb_stderr}".strip() if stderr else fb_stderr

    return OpenSeesProbeResult(
        available=bool(available),
        resolved=resolved,
        version=version_line,
        stdout=stdout,
        stderr=stderr,
        command=command,
        binary_sha256=_sha256_file(resolved),
    )


def validate_backend_probe_requirements(
    probe: OpenSeesProbeResult,
    *,
    require_version_regex: str | None = None,
    require_binary_sha256: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if not probe.available:
        errors.append("backend probe is not available")
        return errors

    version_regex = (require_version_regex or "").strip()
    if version_regex:
        try:
            matches = re.search(version_regex, probe.version) is not None
        except re.error as exc:
            errors.append(f"invalid version regex '{version_regex}': {exc}")
            matches = False
        if not matches:
            errors.append(
                f"version '{probe.version}' does not match regex '{version_regex}'"
            )

    required_sha = (require_binary_sha256 or "").strip().lower()
    if required_sha:
        actual_sha = probe.binary_sha256.strip().lower()
        if not actual_sha:
            errors.append("binary sha256 could not be computed")
        elif actual_sha != required_sha:
            errors.append(
                f"binary sha256 mismatch: expected {required_sha}, got {actual_sha}"
            )

    return errors


def run_opensees(
    executable: str,
    tcl_file: Path,
    cwd: Path,
    timeout_s: int,
    extra_args: list[str] | None = None,
) -> OpenSeesRunOutput:
    cmd = [executable]
    if extra_args:
        cmd.extend(extra_args)
    cmd.append(str(tcl_file))

    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            timeout=timeout_s,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise OpenSeesExecutionError(
            f"OpenSees executable not found: {executable}. Set opensees.executable in config.",
            command=cmd,
        ) from exc
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_timeout_stream(exc.stdout)
        stderr = _decode_timeout_stream(exc.stderr)
        raise OpenSeesExecutionError(
            f"OpenSees timed out after {timeout_s}s for script {tcl_file.name}.",
            stdout=stdout,
            stderr=stderr,
            command=cmd,
        ) from exc

    if proc.returncode != 0:
        raise OpenSeesExecutionError(
            f"OpenSees failed with code {proc.returncode}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}",
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            command=cmd,
        )

    return OpenSeesRunOutput(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        command=cmd,
    )
