from __future__ import annotations

import shutil
import subprocess
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


def resolve_opensees_executable(executable: str) -> Path | None:
    candidate = Path(executable)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    resolved = shutil.which(executable)
    return Path(resolved) if resolved is not None else None


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
        raise OpenSeesExecutionError(
            f"OpenSees timed out after {timeout_s}s for script {tcl_file.name}.",
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
