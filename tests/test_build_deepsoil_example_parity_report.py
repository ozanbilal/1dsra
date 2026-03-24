from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "build_deepsoil_example_parity_report.py"
)
SPEC = importlib.util.spec_from_file_location("build_deepsoil_example_parity_report", SCRIPT_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_classify_case_partial_for_psa_only_match() -> None:
    verdict, note = MODULE._classify_case(
        {
            "psa_nrmse": 0.21,
            "pga_pct_diff": -57.0,
            "surface_corrcoef": 0.002,
            "warnings": ["Time-step mismatch detected (StrataWave=0.005s, DEEPSOIL=0.02s)."],
        }
    )
    assert verdict == "partial"
    assert "PSA" in note


def test_classify_case_poor_for_large_mismatch() -> None:
    verdict, note = MODULE._classify_case(
        {
            "psa_nrmse": 3.7,
            "pga_pct_diff": 524.0,
            "surface_corrcoef": 0.01,
            "warnings": [],
        }
    )
    assert verdict == "poor"
    assert "parity" in note.lower()


def test_best_case_prefers_lower_psa_nrmse() -> None:
    poor = MODULE.CaseSummary(
        key="poor",
        label="Poor",
        boundary="rigid",
        run_id="run-poor",
        compare_json="poor.json",
        run_dir="poor",
        deepsoil_surface_csv="surface.csv",
        deepsoil_psa_csv="psa.csv",
        stratawave_dt_s=0.02,
        deepsoil_dt_s=0.02,
        surface_nrmse=0.45,
        surface_corrcoef=0.01,
        pga_ratio=0.8,
        pga_pct_diff=-20.0,
        psa_nrmse=0.24,
        psa_pct_diff_at_peak=-20.0,
        psa_peak_period_s=0.18,
        warnings=[],
        verdict="partial",
        note="note",
    )
    better = MODULE.CaseSummary(
        key="better",
        label="Better",
        boundary="rigid",
        run_id="run-better",
        compare_json="better.json",
        run_dir="better",
        deepsoil_surface_csv="surface.csv",
        deepsoil_psa_csv="psa.csv",
        stratawave_dt_s=0.005,
        deepsoil_dt_s=0.02,
        surface_nrmse=0.44,
        surface_corrcoef=0.002,
        pga_ratio=0.43,
        pga_pct_diff=-57.0,
        psa_nrmse=0.20,
        psa_pct_diff_at_peak=-78.0,
        psa_peak_period_s=0.05,
        warnings=["Time-step mismatch"],
        verdict="partial",
        note="note",
    )
    assert MODULE._best_case([poor, better]).key == "better"
