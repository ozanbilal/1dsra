"""Railway entry point — adds python/ to sys.path before importing the app."""
import sys
from pathlib import Path

# Add python/ subdirectory to Python path so dsra1d package is importable
_python_dir = str(Path(__file__).resolve().parent / "python")
if _python_dir not in sys.path:
    sys.path.insert(0, _python_dir)

from dsra1d.web.app import app  # noqa: E402, F401
