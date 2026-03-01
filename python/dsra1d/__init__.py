"""1DSRA SDK package."""

from dsra1d.pipeline import load_result, run_analysis, run_batch
from dsra1d.post.spectra import Spectra, compute_spectra
from dsra1d.types import BatchResult, Motion, RunResult

__version__ = "0.1.0"

__all__ = [
    "BatchResult",
    "Motion",
    "RunResult",
    "Spectra",
    "__version__",
    "compute_spectra",
    "load_result",
    "run_analysis",
    "run_batch",
]
