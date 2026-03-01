#!/usr/bin/env python
from __future__ import annotations

import sys
from pathlib import Path


def _import_ops():
    try:
        from openseespy import opensees as ops
    except Exception as exc:  # pragma: no cover - import failure path
        print(f"OpenSeesPy import failed: {exc}", file=sys.stderr)
        return None
    return ops


def _print_version() -> int:
    ops = _import_ops()
    if ops is None:
        return 2
    try:
        version = ops.version()
    except Exception as exc:  # pragma: no cover - backend-specific
        print(f"OpenSeesPy version probe failed: {exc}", file=sys.stderr)
        return 2
    print(f"OpenSeesPy {version}")
    return 0


def _run_tcl(tcl_file: Path) -> int:
    if not tcl_file.exists():
        print(f"Tcl file not found: {tcl_file}", file=sys.stderr)
        return 2
    ops = _import_ops()
    if ops is None:
        return 2
    try:
        ops.wipe()
        ops.source(str(tcl_file))
    except SystemExit as exc:  # pragma: no cover - passthrough for exit codes
        code = exc.code
        if isinstance(code, int):
            return code
        if code is None:
            return 0
        return 1
    except Exception as exc:  # pragma: no cover - backend-specific
        print(f"OpenSeesPy source failed for {tcl_file}: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str]) -> int:
    if len(argv) <= 1:
        print("Usage: opensees_pyshim.py [-version|--version] <model.tcl>", file=sys.stderr)
        return 2

    if argv[-1] in {"-version", "--version"}:
        return _print_version()
    if "-version" in argv or "--version" in argv:
        return _print_version()

    tcl_path = Path(argv[-1]).resolve()
    return _run_tcl(tcl_path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
