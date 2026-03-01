from __future__ import annotations

import argparse
import re
from pathlib import Path

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _replace_single(pattern: re.Pattern[str], text: str, repl: str, label: str) -> str:
    new_text, count = pattern.subn(repl, text, count=1)
    if count != 1:
        raise RuntimeError(f"Could not update version in {label}")
    return new_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Bump 1DSRA version in synchronized files.")
    parser.add_argument("--version", required=True, help="SemVer version (e.g. 1.0.0)")
    parser.add_argument("--dry-run", action="store_true", help="Only validate files; do not write.")
    args = parser.parse_args()

    version = args.version.strip()
    if not SEMVER_RE.fullmatch(version):
        raise SystemExit("Version must match SemVer core format: X.Y.Z")

    repo_root = Path(__file__).resolve().parents[1]
    pyproject = repo_root / "pyproject.toml"
    py_init = repo_root / "python" / "dsra1d" / "__init__.py"
    core_cpp = repo_root / "core" / "src" / "version.cpp"

    pyproject_text = pyproject.read_text(encoding="utf-8")
    py_init_text = py_init.read_text(encoding="utf-8")
    core_cpp_text = core_cpp.read_text(encoding="utf-8")

    pyproject_new = _replace_single(
        re.compile(r'^version = "[^"]+"$', flags=re.MULTILINE),
        pyproject_text,
        f'version = "{version}"',
        "pyproject.toml",
    )
    py_init_new = _replace_single(
        re.compile(r'^__version__ = "[^"]+"$', flags=re.MULTILINE),
        py_init_text,
        f'__version__ = "{version}"',
        "python/dsra1d/__init__.py",
    )
    core_cpp_new = _replace_single(
        re.compile(r'return "[^"]+";'),
        core_cpp_text,
        f'return "{version}";',
        "core/src/version.cpp",
    )

    if not args.dry_run:
        pyproject.write_text(pyproject_new, encoding="utf-8")
        py_init.write_text(py_init_new, encoding="utf-8")
        core_cpp.write_text(core_cpp_new, encoding="utf-8")

    print(
        "Updated versions:\n"
        f"- {pyproject}\n"
        f"- {py_init}\n"
        f"- {core_cpp}\n"
        f"Target version: {version}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
