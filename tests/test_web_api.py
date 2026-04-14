from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")


def test_web_health_endpoint() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload.get("status") == "ok"


def test_web_runs_endpoint_returns_list() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)


def test_web_runs_endpoint_includes_health_summary(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    client = TestClient(create_app())
    resp = client.get("/api/runs", params={"output_root": str(tmp_path / "web-runs")})
    assert resp.status_code == 200
    payload = resp.json()
    row = next((r for r in payload if r.get("run_id") == result.run_id), None)
    assert row is not None
    assert "convergence_mode" in row
    assert "convergence_severity" in row
    assert "converged" in row
    assert "solver_warning_count" in row
    assert "solver_failed_converge_count" in row
    assert "solver_analyze_failed_count" in row
    assert "solver_divide_by_zero_count" in row
    assert "solver_dynamic_fallback_failed_count" in row


def test_web_static_assets_served() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    root = client.get("/")
    assert root.status_code == 200
    assert "/assets/app.v2.js" in root.text

    app_js = client.get("/assets/app.v2.js")
    assert app_js.status_code == 200
    assert "GeoWave" in app_js.text


def test_web_list_config_templates_endpoint() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/config/templates")
    assert resp.status_code == 200
    payload = resp.json()
    assert "templates" in payload
    assert "linear-3layer-sand" in payload["templates"]
    assert "mkz-gqh-eql" in payload["templates"]
    assert "mkz-gqh-nonlinear" in payload["templates"]
    assert "mkz-gqh-darendeli" in payload["templates"]
    assert "pm4sand-calibration" not in payload["templates"]
    assert "pm4silt-calibration" not in payload["templates"]
    assert "mkz-gqh-mock" not in payload["templates"]


def test_web_create_config_template_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/config/template",
        json={
            "template": "mkz-gqh-eql",
            "output_dir": str(tmp_path),
            "file_name": "ui_generated_case.yml",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    cfg_path = payload["config_path"]
    assert cfg_path.endswith(".yml")

    from pathlib import Path

    cfg = Path(cfg_path)
    assert cfg.exists()


def _make_core_run(tmp_path):
    from pathlib import Path

    from dsra1d.config import load_project_config
    from dsra1d.motion import load_motion
    from dsra1d.pipeline import run_analysis

    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    return run_analysis(cfg, motion, output_dir=tmp_path / "web-runs")


def _make_core_run_with_time_column_motion(tmp_path):
    from pathlib import Path

    from dsra1d.config import load_project_config
    from dsra1d.motion import load_motion
    from dsra1d.pipeline import run_analysis

    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    cfg.analysis.dt = 0.002
    motion_file = tmp_path / "motion_time_acc.csv"
    motion_file.write_text(
        "time_s,acc_m_s2\n"
        "0.000,0.10\n"
        "0.005,-0.20\n"
        "0.010,0.00\n"
        "0.015,0.15\n"
        "0.020,-0.05\n",
        encoding="utf-8",
    )
    motion = load_motion(motion_file, dt=cfg.analysis.dt, unit=cfg.motion.units)
    return run_analysis(cfg, motion, output_dir=tmp_path / "web-runs")


def test_web_signals_endpoint_includes_extended_fields(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    client = TestClient(create_app())
    resp = client.get(
        f"/api/runs/{result.run_id}/signals",
        params={"output_root": str(tmp_path / "web-runs")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    required_keys = {
        "run_id",
        "time_s",
        "surface_acc_m_s2",
        "input_time_s",
        "applied_input_time_s",
        "period_s",
        "psa_m_s2",
        "dt_s",
        "input_dt_s",
        "delta_t_s",
        "spectra_source",
        "freq_hz",
        "transfer_abs",
        "ru_time_s",
        "ru_t",
        "ru",
        "delta_u_t",
        "delta_u",
        "sigma_v_eff_t",
        "sigma_v_eff",
        "sigma_v_ref",
    }
    assert required_keys.issubset(payload.keys())
    assert len(payload["time_s"]) > 1
    assert len(payload["period_s"]) > 1


def test_web_signals_endpoint_uses_input_motion_dt_for_input_series_and_psa(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run_with_time_column_motion(tmp_path)
    client = TestClient(create_app())
    resp = client.get(
        f"/api/runs/{result.run_id}/signals",
        params={"output_root": str(tmp_path / "web-runs")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["input_dt_s"] == pytest.approx(0.005)
    assert len(payload["input_time_s"]) == len(payload["input_acc_m_s2"])
    assert len(payload["applied_input_time_s"]) == len(payload["applied_input_acc_m_s2"])
    if len(payload["input_time_s"]) > 1:
        assert (payload["input_time_s"][1] - payload["input_time_s"][0]) == pytest.approx(0.005)
    if len(payload["applied_input_time_s"]) > 1:
        assert (payload["applied_input_time_s"][1] - payload["applied_input_time_s"][0]) == pytest.approx(0.005)


def test_web_download_surface_csv_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    client = TestClient(create_app())
    resp = client.get(
        f"/api/runs/{result.run_id}/surface-acc.csv",
        params={"output_root": str(tmp_path / "web-runs")},
    )
    assert resp.status_code == 200
    text = resp.text
    assert "time_s,acc_m_s2,delta_t_s" in text
    assert len(text.splitlines()) > 5


def test_web_download_pwp_effective_csv_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    client = TestClient(create_app())
    resp = client.get(
        f"/api/runs/{result.run_id}/pwp-effective.csv",
        params={"output_root": str(tmp_path / "web-runs")},
    )
    assert resp.status_code == 200
    text = resp.text
    assert "time_s,ru,delta_u,sigma_v_eff,delta_t_s" in text
    assert len(text.splitlines()) > 5


def test_web_wizard_schema_endpoint() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/wizard/schema")
    assert resp.status_code == 200
    payload = resp.json()
    assert "steps" in payload
    assert "defaults" in payload
    assert "config_templates" in payload
    assert "template_defaults" in payload
    assert payload["steps"][0]["id"] == "analysis_step"
    assert "mkz-gqh-eql" in payload["config_templates"]
    assert "mkz-gqh-nonlinear" in payload["config_templates"]
    assert "mkz-gqh-darendeli" in payload["config_templates"]
    assert payload["default_template"] == "mkz-gqh-nonlinear"
    assert payload["enum_options"]["solver_backend"] == ["linear", "eql", "nonlinear"]
    assert payload["enum_options"]["material"] == ["mkz", "gqh", "elastic"]
    assert payload["defaults"]["analysis_step"]["boundary_condition"] == "rigid"
    assert payload["defaults"]["motion_step"]["input_type"] == "outcrop"
    assert "mkz-gqh-darendeli" in payload["template_defaults"]
    assert payload["template_defaults"]["mkz-gqh-nonlinear"]["analysis_step"]["boundary_condition"] == "rigid"
    assert payload["template_defaults"]["mkz-gqh-nonlinear"]["motion_step"]["input_type"] == "outcrop"
    darendeli_defaults = payload["template_defaults"]["mkz-gqh-darendeli"]["profile_step"]["layers"]
    assert darendeli_defaults[0]["calibration"]["source"] == "darendeli"
    assert darendeli_defaults[0]["material"] == "mkz"
    assert "water_table_depth_m" in payload["fields"]["profile_step"]


def test_web_config_from_wizard_endpoint(tmp_path) -> None:
    from dsra1d.config import load_project_config
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/config/from-wizard",
        json={
            "analysis_step": {
                "project_name": "wizard-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "nonlinear",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "mkz",
                        "material_params": {"gmax": 60000.0, "gamma_ref": 0.001, "damping_min": 0.02, "damping_max": 0.12},
                        "material_optional_args": [],
                    }
                ]
            },
            "motion_step": {
                "motion_path": "examples/motions/sample_motion.csv",
                "units": "m/s2",
                "baseline": "remove_mean",
                "scale_mode": "none",
            },
            "damping_step": {"mode": "frequency_independent", "update_matrix": False},
            "control_step": {
                "f_max": 25.0,
                "timeout_s": 120,
                "retries": 1,
                "write_hdf5": True,
                "write_sqlite": True,
                "parquet_export": False,
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_case.yml",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    cfg_path = Path(payload["config_path"])
    assert cfg_path.exists()
    _ = load_project_config(cfg_path)


def test_web_config_from_wizard_wires_explicit_bedrock(tmp_path) -> None:
    from dsra1d.config import load_project_config
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/config/from-wizard",
        json={
            "analysis_step": {
                "project_name": "wizard-bedrock-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "nonlinear",
            },
            "profile_step": {
                "water_table_depth_m": 0.0,
                "bedrock": {
                    "name": "Rock",
                    "vs_m_s": 760.0,
                    "unit_weight_kN_m3": 25.0,
                },
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 20.0,
                        "unit_weight_kN_m3": 20.0,
                        "vs_m_s": 500.0,
                        "material": "elastic",
                        "material_params": {},
                        "material_optional_args": [],
                    }
                ],
            },
            "motion_step": {
                "motion_path": "examples/motions/sample_motion.csv",
                "units": "m/s2",
                "baseline": "remove_mean",
                "scale_mode": "none",
            },
            "damping_step": {"mode": "frequency_independent", "update_matrix": False},
            "control_step": {
                "f_max": 25.0,
                "timeout_s": 120,
                "retries": 1,
                "write_hdf5": True,
                "write_sqlite": True,
                "parquet_export": False,
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_bedrock.yml",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    cfg = load_project_config(Path(payload["config_path"]))
    assert cfg.profile.bedrock is not None
    assert cfg.profile.bedrock.vs_m_s == pytest.approx(760.0)
    assert cfg.profile.bedrock.unit_weight_kn_m3 == pytest.approx(25.0)


def test_web_config_from_wizard_preserves_darendeli_calibration(tmp_path) -> None:
    from dsra1d.config import load_project_config
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/config/from-wizard",
        json={
            "analysis_step": {
                "project_name": "wizard-darendeli-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "nonlinear",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "Clay-1",
                        "thickness_m": 6.0,
                        "unit_weight_kN_m3": 18.2,
                        "vs_m_s": 190.0,
                        "material": "mkz",
                        "material_params": {"tau_max": 82.0},
                        "material_optional_args": [],
                        "calibration": {
                            "source": "darendeli",
                            "plasticity_index": 20.0,
                            "ocr": 1.5,
                            "mean_effective_stress_kpa": 80.0,
                            "frequency_hz": 1.0,
                            "num_cycles": 10.0,
                            "reload_factor": 2.0,
                        },
                    }
                ]
            },
            "motion_step": {
                "motion_path": "examples/motions/sample_motion.csv",
                "units": "m/s2",
                "baseline": "remove_mean",
                "scale_mode": "none",
            },
            "damping_step": {"mode": "frequency_independent", "update_matrix": False},
            "control_step": {
                "f_max": 25.0,
                "timeout_s": 120,
                "retries": 1,
                "write_hdf5": True,
                "write_sqlite": True,
                "parquet_export": False,
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_darendeli.yml",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    cfg_path = Path(payload["config_path"])
    cfg = load_project_config(cfg_path)
    layer = cfg.profile.layers[0]
    assert layer.calibration is not None
    assert layer.calibration.source == "darendeli"
    assert layer.calibration.mean_effective_stress_kpa == pytest.approx(80.0)


def test_web_layer_calibration_preview_endpoint_with_darendeli_target() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/layer-calibration-preview",
        json={
            "layer": {
                "name": "Clay-1",
                "thickness_m": 6.0,
                "unit_weight_kN_m3": 18.2,
                "vs_m_s": 190.0,
                "material": "mkz",
                "material_params": {"tau_max": 82.0},
                "material_optional_args": [],
                "calibration": {
                    "source": "darendeli",
                    "plasticity_index": 20.0,
                    "ocr": 1.5,
                    "mean_effective_stress_kpa": 80.0,
                    "frequency_hz": 1.0,
                    "num_cycles": 10.0,
                    "reload_factor": 2.0,
                },
            }
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["available"] is True
    assert payload["target_available"] is True
    assert payload["source"] == "darendeli"
    assert len(payload["strain"]) >= 12
    assert len(payload["fitted_modulus_reduction"]) == len(payload["strain"])
    assert len(payload["target_damping_ratio"]) == len(payload["strain"])


def test_web_layer_calibration_preview_endpoint_manual_gqh() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/layer-calibration-preview",
        json={
            "layer": {
                "name": "GQH-1",
                "thickness_m": 8.0,
                "unit_weight_kN_m3": 19.0,
                "vs_m_s": 240.0,
                "material": "gqh",
                "material_params": {
                    "gmax": 95000.0,
                    "gamma_ref": 0.001,
                    "a1": 1.0,
                    "a2": 0.45,
                    "m": 2.0,
                    "damping_min": 0.01,
                    "damping_max": 0.12,
                    "reload_factor": 1.6,
                },
                "material_optional_args": [],
                "calibration": None,
            }
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["available"] is True
    assert payload["target_available"] is False
    assert payload["source"] == "manual"
    assert len(payload["fitted_modulus_reduction"]) == len(payload["strain"])


def test_web_layer_calibration_preview_strength_controlled_gqh() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/layer-calibration-preview",
        json={
            "layer": {
                "name": "GQH-Strength",
                "thickness_m": 4.0,
                "unit_weight_kN_m3": 20.0,
                "vs_m_s": 500.0,
                "material": "gqh",
                "material_params": {"gmax": 509684.0, "tau_max": 420.0},
                "calibration": {
                    "source": "darendeli",
                    "plasticity_index": 15.0,
                    "ocr": 1.0,
                    "k0": 0.5,
                    "frequency_hz": 1.0,
                    "num_cycles": 10.0,
                    "fit_strain_min": 1e-6,
                    "fit_strain_max": 5e-4,
                    "target_strength_kpa": 420.0,
                    "target_strength_ratio": 0.95,
                    "target_strength_strain": 0.1,
                },
            },
            "layers": [
                {
                    "name": "GQH-Strength",
                    "thickness_m": 4.0,
                    "unit_weight_kN_m3": 20.0,
                    "vs_m_s": 500.0,
                    "material": "gqh",
                    "material_params": {"gmax": 509684.0, "tau_max": 420.0},
                    "calibration": {
                        "source": "darendeli",
                        "plasticity_index": 15.0,
                        "ocr": 1.0,
                        "k0": 0.5,
                        "target_strength_kpa": 420.0,
                    },
                }
            ],
            "layer_index": 0,
            "water_table_depth_m": 0.0,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["available"] is True
    assert payload["gqh_mode"] == "strength_controlled"
    assert payload["sigma_v_eff_mid_kpa"] is not None


def test_web_layer_calibration_preview_returns_fit_quality_fields() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/layer-calibration-preview",
        json={
            "layer": {
                "name": "GQH-Quality",
                "thickness_m": 4.0,
                "unit_weight_kN_m3": 20.0,
                "vs_m_s": 500.0,
                "material": "gqh",
                "fit_stale": True,
                "material_params": {"gmax": 509684.0, "tau_max": 420.0},
                "calibration": {
                    "source": "darendeli",
                    "plasticity_index": 15.0,
                    "ocr": 1.0,
                    "k0": 0.5,
                    "target_strength_kpa": 420.0,
                    "fit_procedure": "MRD",
                    "fit_limits": {
                        "mr_min_strain": 1e-6,
                        "mr_max_strain": 5e-4,
                        "damping_min_strain": 1e-6,
                        "damping_max_strain": 1e-2,
                        "min_strength_pct": 95.0,
                        "fix_theta3": 1.0,
                    },
                },
            }
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["available"] is True
    assert payload["fit_stale"] is True
    assert payload["fit_procedure"] == "MRD"
    assert payload["modulus_rmse"] is not None
    assert payload["damping_rmse"] is not None
    assert payload["strength_ratio_achieved"] is not None
    assert payload["fit_limits_applied"] is not None
    assert payload["fit_limits_applied"]["min_strength_pct"] == pytest.approx(95.0)


def test_web_layer_calibration_preview_refits_to_selected_reference_curve() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/layer-calibration-preview",
        json={
            "layer": {
                "name": "GQH-Reference",
                "thickness_m": 4.0,
                "unit_weight_kN_m3": 20.0,
                "vs_m_s": 500.0,
                "material": "gqh",
                "reference_curve": "seed_idriss_mean",
                "material_params": {"gmax": 509684.0, "tau_max": 420.0},
                "calibration": {
                    "source": "darendeli",
                    "plasticity_index": 15.0,
                    "ocr": 1.0,
                    "k0": 0.5,
                    "fit_strain_min": 1e-6,
                    "fit_strain_max": 5e-4,
                    "target_strength_kpa": 420.0,
                    "target_strength_ratio": 0.95,
                    "target_strength_strain": 0.1,
                },
            },
            "layer_index": 0,
            "water_table_depth_m": 0.0,
            "layers": [
                {
                    "name": "GQH-Reference",
                    "thickness_m": 4.0,
                    "unit_weight_kN_m3": 20.0,
                    "vs_m_s": 500.0,
                    "material": "gqh",
                    "reference_curve": "seed_idriss_mean",
                    "material_params": {"gmax": 509684.0, "tau_max": 420.0},
                    "calibration": {
                        "source": "darendeli",
                        "plasticity_index": 15.0,
                        "ocr": 1.0,
                        "k0": 0.5,
                        "target_strength_kpa": 420.0,
                    },
                }
            ],
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["available"] is True
    assert payload["source"] == "reference:seed_idriss_mean"
    assert payload["gqh_mode"] == "strength_controlled"
    assert "mrdf_p1" in payload["calibrated_material_params"]
    target_damping = payload["target_damping_ratio"]
    fitted_damping = payload["fitted_damping_ratio"]
    assert len(target_damping) == len(fitted_damping)
    assert max(target_damping) - min(target_damping) > 0.05
    assert max(fitted_damping) - min(fitted_damping) > 0.05


def test_web_profile_diagnostics_endpoint() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/profile-diagnostics",
        json={
            "profile_step": {
                "water_table_depth_m": 1.0,
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 4.0,
                        "unit_weight_kN_m3": 20.0,
                        "vs_m_s": 500.0,
                        "material": "gqh",
                        "material_params": {
                            "gmax": 509684.0,
                            "tau_max": 420.0,
                            "theta1": -2.88,
                            "theta2": -2.80,
                            "theta3": 0.2291,
                            "theta4": 0.99,
                            "theta5": 1.0,
                            "damping_min": 0.012,
                        },
                    }
                ],
            }
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["layer_count"] == 1
    row = payload["layers"][0]
    assert row["sigma_v_eff_mid_kpa"] is not None
    assert row["implied_strength_kpa"] is not None
    assert row["gqh_mode"] == "strength_controlled"


def test_web_config_from_wizard_wires_rayleigh_damping(tmp_path) -> None:
    from dsra1d.config import load_project_config
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/config/from-wizard",
        json={
            "analysis_step": {
                "project_name": "wizard-rayleigh-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "linear",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "mkz",
                        "material_params": {
                            "gmax": 60000.0,
                            "gamma_ref": 0.001,
                            "damping_min": 0.02,
                            "damping_max": 0.12,
                        },
                        "material_optional_args": [],
                    }
                ]
            },
            "motion_step": {
                "motion_path": "examples/motions/sample_motion.csv",
                "units": "m/s2",
                "baseline": "remove_mean",
                "scale_mode": "none",
            },
            "damping_step": {
                "mode": "rayleigh",
                "update_matrix": True,
                "mode_1": 1.0,
                "mode_2": 8.0,
            },
            "control_step": {
                "f_max": 25.0,
                "timeout_s": 120,
                "retries": 1,
                "write_hdf5": True,
                "write_sqlite": True,
                "parquet_export": False,
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_rayleigh.yml",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    cfg_path = Path(payload["config_path"])
    assert cfg_path.exists()
    cfg = load_project_config(cfg_path)
    assert cfg.analysis.damping_mode == "rayleigh"
    assert cfg.analysis.rayleigh_mode_1_hz == pytest.approx(1.0)
    assert cfg.analysis.rayleigh_mode_2_hz == pytest.approx(8.0)
    assert cfg.analysis.rayleigh_update_matrix is True
    assert payload["warnings"] == []


def test_web_wizard_sanity_check_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/sanity-check",
        json={
            "analysis_step": {
                "project_name": "wizard-sanity-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "nonlinear",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "mkz",
                        "material_params": {"gmax": 60000.0, "gamma_ref": 0.001, "damping_min": 0.02, "damping_max": 0.12},
                        "material_optional_args": [],
                    }
                ]
            },
            "motion_step": {
                "motion_path": "examples/motions/sample_motion.csv",
                "units": "m/s2",
                "baseline": "remove_mean",
                "scale_mode": "none",
            },
            "damping_step": {"mode": "frequency_independent", "update_matrix": False},
            "control_step": {
                "f_max": 25.0,
                "timeout_s": 120,
                "retries": 1,
                "write_hdf5": True,
                "write_sqlite": True,
                "parquet_export": False,
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_sanity.yml",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload.get("ok"), bool)
    assert "checks" in payload
    assert any(item.get("name") == "config_validation" for item in payload.get("checks", []))
    assert "derived" in payload


def test_web_motion_import_peer_at2_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    at2 = tmp_path / "motion.at2"
    at2.write_text(
        "AT2 EXAMPLE\nNPTS= 5, DT=0.01 SEC\n0.01 0.02 -0.03 0.00 0.01\n",
        encoding="utf-8",
    )
    client = TestClient(create_app())
    resp = client.post(
        "/api/motion/import/peer-at2",
        json={
            "path": str(at2),
            "units_hint": "g",
            "output_dir": str(tmp_path),
            "output_name": "converted.csv",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["npts"] == 5
    assert payload["dt_s"] == pytest.approx(0.01)
    assert Path(payload["converted_csv_path"]).exists()


def test_web_motion_upload_csv_endpoint(tmp_path) -> None:
    import base64

    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    encoded = base64.b64encode(b"0.0,0.1\n0.01,-0.2\n").decode("ascii")
    resp = client.post(
        "/api/motion/upload/csv",
        json={
            "file_name": "uploaded_motion.csv",
            "content_base64": encoded,
            "output_dir": str(tmp_path),
            "output_name": "uploaded_case",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["nbytes"] > 0
    assert Path(payload["uploaded_path"]).exists()


def test_web_motion_upload_peer_at2_endpoint(tmp_path) -> None:
    import base64

    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    encoded = base64.b64encode(
        b"AT2 EXAMPLE\nNPTS= 5, DT=0.01 SEC\n0.01 0.02 -0.03 0.00 0.01\n"
    ).decode("ascii")
    resp = client.post(
        "/api/motion/upload/peer-at2",
        json={
            "file_name": "uploaded_motion.at2",
            "content_base64": encoded,
            "units_hint": "g",
            "output_dir": str(tmp_path),
            "output_name": "uploaded_at2",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["npts"] == 5
    assert payload["dt_s"] == pytest.approx(0.01)
    assert Path(payload["converted_csv_path"]).exists()


def test_web_motion_process_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    motion = tmp_path / "motion.csv"
    motion.write_text("0.0,0.0\n0.01,0.1\n0.02,-0.05\n0.03,0.0\n", encoding="utf-8")

    client = TestClient(create_app())
    resp = client.post(
        "/api/motion/process",
        json={
            "motion_path": str(motion),
            "units_hint": "m/s2",
            "baseline_mode": "remove_mean",
            "scale_mode": "scale_by",
            "scale_factor": 2.0,
            "output_dir": str(tmp_path),
            "output_name": "processed_motion",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert Path(payload["processed_motion_path"]).exists()
    assert Path(payload["metrics_path"]).exists()
    assert payload["metrics"]["dt_s"] == pytest.approx(0.01)
    assert len(payload["spectra_preview"]["period_s"]) > 0


def test_web_motion_process_uses_fallback_dt_for_single_column(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    motion = tmp_path / "motion_1col.csv"
    motion.write_text("0.10\n-0.05\n0.02\n-0.01\n0.00\n", encoding="utf-8")

    client = TestClient(create_app())
    resp = client.post(
        "/api/motion/process",
        json={
            "motion_path": str(motion),
            "units_hint": "m/s2",
            "baseline_mode": "remove_mean",
            "scale_mode": "none",
            "fallback_dt": 0.005,
            "output_dir": str(tmp_path),
            "output_name": "processed_1col",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["metrics"]["dt_s"] == pytest.approx(0.005)
    assert len(payload["spectra_preview"]["period_s"]) > 0


def test_web_motion_preview_supports_custom_parse_settings(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    motion = tmp_path / "motion_semicolon.txt"
    motion.write_text(
        "record=demo\n"
        "units=gal\n"
        "0.00;100.0\n"
        "0.01;-50.0\n"
        "0.02;25.0\n",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    resp = client.get(
        "/api/motion/preview",
        params={
            "path": str(motion),
            "units_hint": "gal",
            "format_hint": "time_acc",
            "delimiter": "semicolon",
            "skip_rows": 2,
            "time_col": 0,
            "acc_col": 1,
            "has_time": True,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["input_units"] == "gal"
    assert payload["format_hint"] == "time_acc"
    assert payload["dt"] == pytest.approx(0.01)
    assert payload["time_s"][:3] == pytest.approx([0.0, 0.01, 0.02])
    assert payload["acc_input_units"][:3] == pytest.approx([100.0, -50.0, 25.0])
    assert payload["acc_m_s2"][:3] == pytest.approx([1.0, -0.5, 0.25])
    assert payload["pga_input_units"] == pytest.approx(100.0)
    assert payload["pgv_m_s"] >= 0.0
    assert payload["pgd_m"] >= 0.0
    assert len(payload["vel_m_s"]) == len(payload["time_s"])
    assert len(payload["disp_m"]) == len(payload["time_s"])
    assert len(payload["period_s"]) > 0
    assert len(payload["sa_input_units"]) == len(payload["period_s"])
    assert len(payload["sv_m_s"]) == len(payload["period_s"])
    assert len(payload["sd_m"]) == len(payload["period_s"])


def test_web_motion_preview_supports_scaling_and_processed_only_view(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    motion = tmp_path / "motion_g.csv"
    motion.write_text(
        "0.00,0.10\n"
        "0.01,-0.20\n"
        "0.02,0.40\n"
        "0.03,-0.10\n",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    resp = client.get(
        "/api/motion/preview",
        params={
            "path": str(motion),
            "units_hint": "g",
            "format_hint": "time_acc",
            "scale_mode": "scale_to_pga",
            "target_pga": 0.5,
            "show_uncorrected_preview": False,
            "trim_start": 0.0,
            "trim_end": 0.03,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["input_units"] == "g"
    assert payload["show_uncorrected_preview"] is False
    assert payload["raw_time_s"] == []
    assert payload["raw_acc_input_units"] == []
    assert payload["pga_input_units"] == pytest.approx(0.5, rel=1.0e-3)
    assert payload["pga_m_s2"] == pytest.approx(0.5 * 9.81, rel=1.0e-3)
    assert len(payload["vel_m_s"]) == len(payload["time_s"])
    assert len(payload["disp_m"]) == len(payload["time_s"])


def test_web_motion_process_supports_advanced_processing_options(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    motion = tmp_path / "motion_adv.csv"
    motion.write_text(
        "0.00,0.00\n"
        "0.01,0.10\n"
        "0.02,-0.08\n"
        "0.03,0.04\n"
        "0.04,-0.02\n"
        "0.05,0.00\n",
        encoding="utf-8",
    )

    client = TestClient(create_app())
    resp = client.post(
        "/api/motion/process",
        json={
            "motion_path": str(motion),
            "units_hint": "m/s2",
            "baseline_mode": "none",
            "scale_mode": "scale_by",
            "scale_factor": 1.5,
            "processing_order": "baseline_first",
            "baseline_on": True,
            "baseline_method": "linear",
            "filter_on": True,
            "filter_domain": "frequency",
            "filter_config": "bandpass",
            "f_low": 0.1,
            "f_high": 20.0,
            "residual_fix": True,
            "spectrum_damping_ratio": 0.1,
            "show_uncorrected_preview": False,
            "output_dir": str(tmp_path),
            "output_name": "processed_adv",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert Path(payload["processed_motion_path"]).exists()
    preview = payload["spectra_preview"]
    assert preview["show_uncorrected_preview"] is False
    assert preview["raw_time_s"] == []
    assert preview["raw_acc_m_s2"] == []
    assert len(preview["time_s"]) > 0
    assert len(preview["period_s"]) == len(preview["sa_m_s2"])
    assert payload["metrics"]["pgv_m_s"] >= 0.0
    assert payload["metrics"]["pgd_m"] >= 0.0


def test_web_motion_library_accepts_extra_directories(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    motion_root = tmp_path / "Input Motions"
    event_dir = motion_root / "Event_A"
    event_dir.mkdir(parents=True)
    (event_dir / "record_01.csv").write_text("0.0,0.1\n0.01,-0.1\n", encoding="utf-8")

    generated_dir = motion_root / "Outputs_GUI"
    generated_dir.mkdir(parents=True)
    (generated_dir / "derived.csv").write_text("0.0,0.0\n0.01,0.0\n", encoding="utf-8")

    client = TestClient(create_app())
    resp = client.get("/api/motions/library", params=[("extra_dir", str(motion_root))])
    assert resp.status_code == 200
    payload = resp.json()
    matching = [row for row in payload if row["path"] == str((event_dir / "record_01.csv").resolve())]
    assert len(matching) == 1
    assert all("derived.csv" not in row["path"] for row in payload)
    assert matching[0]["source_group_label"].endswith("Event_A")


def test_web_motion_timestep_reduction_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    dt = 0.005
    time = np.arange(0.0, 20.0, dt, dtype=np.float64)
    acc = 0.7 * np.sin(2.0 * np.pi * 1.5 * time) + 0.2 * np.sin(2.0 * np.pi * 9.0 * time)
    motion = tmp_path / "motion_reduce.csv"
    np.savetxt(motion, np.column_stack([time, acc]), delimiter=",")

    client = TestClient(create_app())
    resp = client.post(
        "/api/motion/tools/timestep-reduction",
        json={
            "motion_path": str(motion),
            "units_hint": "m/s2",
            "reduction_factor": 4,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["reduction_factor"] == 4
    assert payload["dt_original"] == pytest.approx(dt, rel=1.0e-3)
    assert payload["dt_reduced"] == pytest.approx(dt * 4.0, rel=1.0e-3)
    assert len(payload["time_s"]) > 10
    assert len(payload["acc_original_m_s2"]) == len(payload["time_s"])
    assert len(payload["acc_reduced_m_s2"]) == len(payload["time_s"])


def test_web_motion_kappa_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    dt = 0.002
    time = np.arange(0.0, 20.0, dt, dtype=np.float64)
    envelope = np.exp(-0.08 * time)
    acc = envelope * (
        0.8 * np.sin(2.0 * np.pi * 2.0 * time)
        + 0.35 * np.sin(2.0 * np.pi * 12.0 * time)
        + 0.2 * np.sin(2.0 * np.pi * 22.0 * time)
    )
    motion = tmp_path / "motion_kappa.csv"
    np.savetxt(motion, np.column_stack([time, acc]), delimiter=",")

    client = TestClient(create_app())
    resp = client.post(
        "/api/motion/tools/kappa",
        json={
            "motion_path": str(motion),
            "units_hint": "m/s2",
            "freq_min_hz": 8.0,
            "freq_max_hz": 35.0,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert "freq_hz" in payload
    assert "fas_amplitude" in payload
    assert len(payload["freq_hz"]) > 100
    assert len(payload["fas_amplitude"]) == len(payload["freq_hz"])
    if payload.get("kappa") is not None:
        assert payload["kappa"] >= 0.0


def test_web_run_endpoint_success_with_relative_paths(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    out_root = tmp_path / "run_out"
    resp = client.post(
        "/api/run",
        json={
            "config_path": "examples/configs/mkz_gqh_eql.yml",
            "motion_path": "examples/motions/sample_motion.csv",
            "output_root": str(out_root),
            "backend": "eql",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert Path(payload["output_root"]).resolve() == out_root.resolve()
    assert (out_root / payload["run_id"]).exists()


def test_web_run_batch_endpoint_success_with_duplicate_motions(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    out_root = tmp_path / "batch_out"
    resp = client.post(
        "/api/run-batch",
        json={
            "config_path": "examples/configs/mkz_gqh_eql.yml",
            "motion_paths": [
                "examples/motions/sample_motion.csv",
                "examples/motions/sample_motion.csv",
            ],
            "output_root": str(out_root),
            "backend": "eql",
            "n_jobs": 2,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["motion_count"] == 2
    assert payload["unique_run_count"] == 1
    assert len(payload["results"]) == 2
    assert payload["results"][0]["run_id"] == payload["results"][1]["run_id"]
    assert (out_root / payload["results"][0]["run_id"]).exists()


def test_web_scan_motion_library_recurses_sources(tmp_path) -> None:
    from dsra1d.web.app import _scan_motion_library

    lib_a = tmp_path / "DEEPSOIL 7" / "Input Motions"
    lib_b = tmp_path / "CampaignA" / "Input Motions"
    (lib_a / "nested").mkdir(parents=True)
    lib_b.mkdir(parents=True)
    (lib_a / "nested" / "motion_a.csv").write_text("0.0,0.0\n0.01,0.1\n", encoding="utf-8")
    (lib_b / "motion_b.at2").write_text("header\n", encoding="utf-8")

    rows = _scan_motion_library([lib_a, lib_b])
    names = {row["file_name"] for row in rows}
    assert names == {"motion_a.csv", "motion_b.at2"}
    source_labels = {row["source_label"] for row in rows}
    assert "DEEPSOIL 7 / Input Motions" in source_labels
    assert "CampaignA / Input Motions" in source_labels
    source_group_labels = {row["source_group_label"] for row in rows}
    assert "DEEPSOIL 7 / nested" in source_group_labels
    assert "CampaignA / Input Motions" in source_group_labels


def test_web_scan_motion_library_skips_generated_output_dirs(tmp_path) -> None:
    from dsra1d.web.app import _scan_motion_library

    lib_dir = tmp_path / "DEEPSOIL 7" / "Input Motions"
    (lib_dir / "Outputs_GUI").mkdir(parents=True)
    (lib_dir / "testDSOUT").mkdir(parents=True)
    (lib_dir / "Velux_Konvoy").mkdir(parents=True)
    (lib_dir / "Outputs_GUI" / "derived.txt").write_text("0.0\n", encoding="utf-8")
    (lib_dir / "testDSOUT" / "derived.csv").write_text("0.0,0.0\n", encoding="utf-8")
    (lib_dir / "Velux_Konvoy" / "record.txt").write_text("0.0\n", encoding="utf-8")

    rows = _scan_motion_library([lib_dir])

    assert [row["file_name"] for row in rows] == ["record.txt"]
    assert rows[0]["source_group_label"] == "DEEPSOIL 7 / Velux_Konvoy"


def test_web_load_example_returns_calibration_details() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post("/api/examples/deepsoil_gqh_5layer_baseline/load")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["project_name"] == "deepsoil-gqh-5layer-baseline"
    assert payload["timeout_s"] == 240
    assert payload["retries"] == 1
    assert payload["boundary_condition"] == "rigid"
    assert payload["motion_input_type"] == "outcrop"
    assert len(payload["layers"]) == 5
    first = payload["layers"][0]
    assert first["reference_curve"] == "darendeli"
    assert first["calibration"]["mean_effective_stress_kpa"] > 0.0
    assert first["material_params"]["tau_max"] > 0.0


def test_web_load_literal_example_preserves_theta_values_without_calibration() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post("/api/examples/deepsoil_gqh_5layer_literal/load")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["project_name"] == "deepsoil-gqh-5layer-literal"
    assert len(payload["layers"]) == 5
    first = payload["layers"][0]
    assert "calibration" not in first
    assert "reference_curve" not in first
    assert first["material_params"]["theta1"] == pytest.approx(-6.71)
    assert first["material_params"]["theta2"] == pytest.approx(1.17)
    assert first["material_params"]["theta3"] == pytest.approx(15.4881661891248)


def test_web_incomplete_run_dir_is_listed_and_signals_returns_409(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    root = tmp_path / "partial-runs"
    run_dir = root / "run-partial123456"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "run_id": run_dir.name,
                "timestamp_utc": "2026-03-05T10:00:00Z",
                "solver_backend": "nonlinear",
                "status": "error",
                "message": "Core solver failed before result stores were written.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    client = TestClient(create_app())
    list_resp = client.get("/api/runs", params={"output_root": str(root)})
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert any(row.get("run_id") == run_dir.name for row in rows)

    summary_resp = client.get(
        f"/api/runs/{run_dir.name}/results/summary",
        params={"output_root": str(root)},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["run_id"] == run_dir.name
    assert summary["status"] == "error"

    signals_resp = client.get(
        f"/api/runs/{run_dir.name}/signals",
        params={"output_root": str(root)},
    )
    assert signals_resp.status_code == 409
    detail = str(signals_resp.json().get("detail", ""))
    assert "Run artifacts incomplete" in detail


def test_web_run_endpoint_missing_motion_returns_400(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/run",
        json={
            "config_path": "examples/configs/mkz_gqh_eql.yml",
            "motion_path": "examples/motions/not_found_motion.csv",
            "output_root": str(tmp_path / "run_out"),
            "backend": "eql",
        },
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "Motion file not found" in detail


def test_web_runs_tree_and_results_summary_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    root = tmp_path / "web-runs"
    client = TestClient(create_app())

    tree_resp = client.get("/api/runs/tree", params={"output_root": str(root)})
    assert tree_resp.status_code == 200
    tree_payload = tree_resp.json()
    assert "tree" in tree_payload
    assert len(tree_payload["tree"]) >= 1
    project_runs = next(iter(tree_payload["tree"].values()))
    first_motion_runs = next(iter(project_runs.values()))
    first_run = first_motion_runs[0]
    assert "convergence_mode" in first_run
    assert "convergence_severity" in first_run

    summary_resp = client.get(
        f"/api/runs/{result.run_id}/results/summary",
        params={"output_root": str(root)},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["run_id"] == result.run_id
    assert "metrics" in summary
    assert "convergence" in summary


def test_web_results_summary_fallback_without_output_root() -> None:
    from dsra1d.config import load_project_config
    from dsra1d.motion import load_motion
    from dsra1d.pipeline import run_analysis
    from dsra1d.web.app import _repo_root, create_app
    from fastapi.testclient import TestClient

    fallback_root = _repo_root() / "out" / f"test_web_fallback_{uuid4().hex[:8]}"
    try:
        cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
        dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
        motion = load_motion(
            Path("examples/motions/sample_motion.csv"),
            dt=dt,
            unit=cfg.motion.units,
        )
        result = run_analysis(cfg, motion, output_dir=fallback_root)

        client = TestClient(create_app())
        resp = client.get(f"/api/runs/{result.run_id}/results/summary")
        assert resp.status_code == 200
        payload = resp.json()
        assert payload["run_id"] == result.run_id
    finally:
        shutil.rmtree(fallback_root, ignore_errors=True)


def test_web_runs_endpoint_scans_nested_output_root(tmp_path) -> None:
    from dsra1d.config import load_project_config
    from dsra1d.motion import load_motion
    from dsra1d.pipeline import run_analysis
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    nested_root = tmp_path / "workspace" / "campaign" / "runs"
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(
        Path("examples/motions/sample_motion.csv"),
        dt=dt,
        unit=cfg.motion.units,
    )
    result = run_analysis(cfg, motion, output_dir=nested_root)

    client = TestClient(create_app())
    # Point to parent directory; API should recursively discover nested run dirs.
    resp = client.get("/api/runs", params={"output_root": str(tmp_path / "workspace")})
    assert resp.status_code == 200
    rows = resp.json()
    assert any(row.get("run_id") == result.run_id for row in rows)


def test_web_run_detail_resolves_from_parent_output_root(tmp_path) -> None:
    from dsra1d.config import load_project_config
    from dsra1d.motion import load_motion
    from dsra1d.pipeline import run_analysis
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    nested_root = tmp_path / "workspace" / "campaign" / "runs"
    cfg = load_project_config(Path("examples/configs/mkz_gqh_nonlinear.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(
        Path("examples/motions/sample_motion.csv"),
        dt=dt,
        unit=cfg.motion.units,
    )
    result = run_analysis(cfg, motion, output_dir=nested_root)

    client = TestClient(create_app())
    # Query with parent output_root instead of direct run directory root.
    resp = client.get(
        f"/api/runs/{result.run_id}/signals",
        params={"output_root": str(tmp_path / "workspace")},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["run_id"] == result.run_id


def test_web_results_hysteresis_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    run_dir = Path(result.output_dir)
    assert (run_dir / "layer_1_strain.out").exists()
    assert (run_dir / "layer_1_stress.out").exists()
    assert (run_dir / "layer_response_summary.csv").exists()
    root = tmp_path / "web-runs"
    client = TestClient(create_app())

    resp = client.get(
        f"/api/runs/{result.run_id}/results/hysteresis",
        params={"output_root": str(root)},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["run_id"] == result.run_id
    assert "source" in payload
    assert "layers" in payload
    assert isinstance(payload["layers"], list)
    assert len(payload["layers"]) >= 1
    assert payload["source"] == "recorders"
    layer0 = payload["layers"][0]
    assert "layer_index" in layer0
    assert "strain" in layer0 and "stress" in layer0
    assert len(layer0["strain"]) >= 10
    assert len(layer0["stress"]) == len(layer0["strain"])
    assert layer0["is_proxy"] is False


def test_web_results_hysteresis_prefers_recorded_layer_channels(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    run_dir = Path(result.output_dir)
    t = np.linspace(0.0, 12.0, 240, dtype=np.float64)
    strain = 8.0e-4 * np.sin(2.0 * np.pi * 0.8 * t)
    stress = 42.0 * np.sin((2.0 * np.pi * 0.8 * t) + 0.28)
    # Recorder naming follows 1-based layer index convention.
    np.savetxt(
        run_dir / "layer_1_strain.out",
        np.column_stack([t, np.zeros_like(t), strain]),
    )
    np.savetxt(
        run_dir / "layer_1_stress.out",
        np.column_stack([t, np.zeros_like(t), stress]),
    )

    root = tmp_path / "web-runs"
    client = TestClient(create_app())
    resp = client.get(
        f"/api/runs/{result.run_id}/results/hysteresis",
        params={"output_root": str(root)},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["source"] in {"recorders", "mixed_recorders_proxy"}
    first_layer = next(layer for layer in payload["layers"] if layer["layer_index"] == 0)
    assert first_layer["is_proxy"] is False
    assert "recorded" in str(first_layer["model"])
    assert len(first_layer["strain"]) >= 20
    assert len(first_layer["stress"]) >= 20


def test_web_results_profile_summary_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    run_dir = Path(result.output_dir)
    t = np.linspace(0.0, 6.0, 120, dtype=np.float64)
    pwp = -np.linspace(0.0, 24.0, 120, dtype=np.float64)
    np.savetxt(run_dir / "layer_1_pwp_raw.out", np.column_stack([t, pwp]))

    root = tmp_path / "web-runs"
    client = TestClient(create_app())
    resp = client.get(
        f"/api/runs/{result.run_id}/results/profile-summary",
        params={"output_root": str(root)},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["run_id"] == result.run_id
    assert payload["layer_count"] >= 1
    assert isinstance(payload["layers"], list)
    assert len(payload["layers"]) >= 1
    first = payload["layers"][0]
    assert "name" in first
    assert "z_top_m" in first
    assert "z_bottom_m" in first
    assert first["gamma_max"] is not None
    assert first["tau_peak_kpa"] is not None
    assert first["secant_g_over_gmax"] is not None
    assert first["sigma_v0_mid_kpa"] is not None
    assert first["delta_u_max"] == pytest.approx(24.0, rel=1e-6)
    assert first["sigma_v_eff_min"] is not None
    assert first["ru_max"] is not None


def test_web_results_displacement_animation_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    root = tmp_path / "web-runs"
    client = TestClient(create_app())
    resp = client.post(
        "/api/results/displacement-animation",
        json={
            "run_id": result.run_id,
            "output_root": str(root),
            "frame_count": 80,
            "max_depth_points": 120,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["run_id"] == result.run_id
    assert payload["approximate"] is False
    assert len(payload["depth_m"]) >= 2
    assert len(payload["frame_time_s"]) >= 20
    assert len(payload["displacement_cm"]) == len(payload["frame_time_s"])
    assert len(payload["relative_displacement_cm"]) == len(payload["frame_time_s"])
    assert len(payload["displacement_cm"][0]) == len(payload["depth_m"])
    assert len(payload["relative_displacement_cm"][0]) == len(payload["depth_m"])
    assert payload["peak_surface_displacement_cm"] is not None
    assert payload["peak_profile_displacement_cm"] is not None
    assert payload["peak_surface_relative_displacement_cm"] is not None
    assert payload["peak_profile_relative_displacement_cm"] is not None
    assert "Recorded nodal displacement history" in payload["note"]
    sample_frame = payload["displacement_cm"][len(payload["displacement_cm"]) // 2]
    relative_frame = payload["relative_displacement_cm"][len(payload["relative_displacement_cm"]) // 2]
    if len(sample_frame) >= 3:
        assert max(abs(float(v)) for v in sample_frame) > 0.0
    if len(relative_frame) >= 2:
        assert abs(float(relative_frame[-1])) < 1.0e-6


def test_web_results_response_spectra_summary_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    root = tmp_path / "web-runs"
    client = TestClient(create_app())
    resp = client.get(
        "/api/results/response-spectra-summary",
        params={
            "run_id": result.run_id,
            "output_root": str(root),
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["run_id"] == result.run_id
    assert payload["row_count"] > 10
    assert len(payload["rows"]) == payload["row_count"]
    row0 = payload["rows"][0]
    assert "period_s" in row0
    assert "surface_psa_m_s2" in row0
    assert "amplification_ratio" in row0


def test_web_download_profile_summary_csv_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_core_run(tmp_path)
    run_dir = Path(result.output_dir)
    np.savetxt(
        run_dir / "layer_1_pwp_raw.out",
        np.column_stack(
            [
                np.array([0.0, 1.0], dtype=np.float64),
                np.array([0.0, -12.5], dtype=np.float64),
            ]
        ),
    )

    root = tmp_path / "web-runs"
    client = TestClient(create_app())
    resp = client.get(
        f"/api/runs/{result.run_id}/profile-summary.csv",
        params={"output_root": str(root)},
    )
    assert resp.status_code == 200
    text = resp.text
    assert "idx,name,material,z_top_m,z_bottom_m" in text
    assert "sigma_v0_mid_kpa" in text
    assert "ru_max" in text
    assert len(text.splitlines()) >= 2
