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


def test_web_backend_probe_endpoint() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/backend/opensees/probe", params={"executable": "OpenSees"})
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload.get("requested"), str)
    assert payload["requested"]
    assert isinstance(payload.get("requested_input"), str)
    assert "available" in payload
    assert "assumed_available" in payload
    assert isinstance(payload["assumed_available"], bool)
    assert "env_override_used" in payload
    assert isinstance(payload["env_override_used"], bool)
    assert "version" in payload


def test_web_backend_probe_trims_wrapping_quotes() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    exe = shutil.which("python")
    assert exe is not None
    client = TestClient(create_app())
    resp = client.get("/api/backend/opensees/probe", params={"executable": f'"{exe}"'})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["requested"] == exe
    assert payload["requested_input"] == exe


def test_web_backend_probe_reports_env_override(monkeypatch) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    exe = shutil.which("python")
    assert exe is not None
    monkeypatch.setenv("DSRA1D_OPENSEES_EXE_OVERRIDE", exe)

    client = TestClient(create_app())
    resp = client.get("/api/backend/opensees/probe", params={"executable": "OpenSees"})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["env_override"] == exe
    assert payload["env_override_used"] is True


def test_web_runs_endpoint_returns_list() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)


def test_web_deepsoil_parity_latest_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    out_dir = tmp_path / "parity"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "deepsoil_compare_batch.json"
    report_path.write_text(
        json.dumps(
            {
                "manifest_path": str(tmp_path / "manifest.json"),
                "total_cases": 2,
                "passed_cases": 1,
                "failed_cases": 1,
                "policy": {
                    "surface_corrcoef_min": 0.95,
                    "profile_nrmse_max": 0.25,
                },
                "cases": [
                    {
                        "name": "case-fail",
                        "passed": False,
                        "run": "out/case-fail",
                        "surface_csv": "refs/fail_surface.csv",
                        "profile_csv": "refs/fail_profile.csv",
                        "checks": {"surface_nrmse_max": False, "profile_nrmse_max": True},
                        "metrics": {"surface_corrcoef": 0.91},
                    },
                    {
                        "name": "case-pass",
                        "passed": True,
                        "run": "out/case-pass",
                        "surface_csv": "refs/pass_surface.csv",
                        "checks": {"surface_nrmse_max": True},
                        "metrics": {"surface_corrcoef": 0.99},
                    },
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    client = TestClient(create_app())
    resp = client.get("/api/parity/deepsoil/latest", params={"output_root": str(tmp_path)})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["found"] is True
    assert payload["total_cases"] == 2
    assert payload["failed_cases"] == 1
    assert payload["cases"][0]["name"] == "case-fail"
    assert payload["cases"][0]["passed"] is False
    assert payload["cases"][1]["name"] == "case-pass"


def test_web_deepsoil_release_manifest_endpoint() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/parity/deepsoil/release-manifest")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["policy_path"].endswith("release_signoff.yml")
    assert payload["manifest_path"].endswith("release_signoff_deepsoil_manifest.json")
    assert payload["sample_manifest_path"].endswith("release_signoff_deepsoil_manifest.sample.json")
    assert "require_deepsoil_compare" in payload


def test_web_deepsoil_release_manifest_editor_and_save_endpoint(tmp_path, monkeypatch) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    repo_root = tmp_path / "repo"
    policy_dir = repo_root / "benchmarks" / "policies"
    policy_dir.mkdir(parents=True, exist_ok=True)
    (policy_dir / "release_signoff.yml").write_text(
        "require_deepsoil_compare: true\n",
        encoding="utf-8",
    )
    (policy_dir / "release_signoff_deepsoil_manifest.sample.json").write_text(
        json.dumps(
            {
                "defaults": {"surface_corrcoef_min": 0.95},
                "cases": [{"name": "sample-case", "run": "out/sample"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    import dsra1d.web.app as web_app_mod

    monkeypatch.setattr(web_app_mod, "_repo_root", lambda: repo_root)

    client = TestClient(create_app())
    resp = client.get("/api/parity/deepsoil/release-manifest/editor")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["loaded_from"] == "sample"
    assert payload["exists"] is False
    assert payload["cases"][0]["name"] == "sample-case"

    save_resp = client.post(
        "/api/parity/deepsoil/release-manifest/save",
        json={
            "defaults": {"surface_corrcoef_min": 0.97, "profile_nrmse_max": 0.22},
            "cases": [
                {
                    "name": "case-01",
                    "run": "out/release/case01",
                    "surface_csv": "refs/case01_surface.csv",
                    "psa_csv": "",
                    "profile_csv": "refs/case01_profile.csv",
                    "hysteresis_csv": "",
                    "hysteresis_layer": 0,
                }
            ],
        },
    )
    assert save_resp.status_code == 200
    saved = save_resp.json()
    assert saved["status"] == "ok"
    assert saved["case_count"] == 1
    manifest_path = policy_dir / "release_signoff_deepsoil_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["defaults"]["surface_corrcoef_min"] == 0.97
    assert manifest["cases"][0]["name"] == "case-01"


def test_web_runs_endpoint_includes_health_summary(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
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
    assert "/assets/app.js" in root.text

    app_js = client.get("/assets/app.js")
    assert app_js.status_code == 200
    assert "WIZARD_STEPS" in app_js.text


def test_web_list_config_templates_endpoint() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/config/templates")
    assert resp.status_code == 200
    payload = resp.json()
    assert "templates" in payload
    assert "effective-stress" in payload["templates"]
    assert "pm4sand-calibration" in payload["templates"]
    assert "pm4silt-calibration" in payload["templates"]


def test_web_create_config_template_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/config/template",
        json={
            "template": "effective-stress",
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


def _make_mock_run(tmp_path):
    from pathlib import Path

    from dsra1d.config import load_project_config
    from dsra1d.motion import load_motion
    from dsra1d.pipeline import run_analysis

    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "mock"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    return run_analysis(cfg, motion, output_dir=tmp_path / "web-runs")


def test_web_signals_endpoint_includes_extended_fields(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
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
        "period_s",
        "psa_m_s2",
        "dt_s",
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


def test_web_download_surface_csv_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
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

    result = _make_mock_run(tmp_path)
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
    assert "deepsoil_bap_like" in payload["enum_options"]["baseline"]
    assert "pm4sand-calibration" in payload["config_templates"]
    assert "pm4silt-calibration" in payload["config_templates"]
    assert "mkz-gqh-darendeli" in payload["config_templates"]
    assert "pm4sand-calibration" in payload["template_defaults"]
    darendeli_defaults = payload["template_defaults"]["mkz-gqh-darendeli"]["profile_step"]["layers"]
    assert darendeli_defaults[0]["calibration"]["source"] == "darendeli"
    assert darendeli_defaults[0]["material"] == "mkz"


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
                "solver_backend": "opensees",
                "pm4_validation_profile": "basic",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "pm4sand",
                        "material_params": {"Dr": 0.45, "G0": 600.0, "hpo": 0.53},
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
                "opensees_executable": "OpenSees",
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
                "pm4_validation_profile": "basic",
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
                "opensees_executable": "OpenSees",
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
                "pm4_validation_profile": "basic",
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
                "opensees_executable": "OpenSees",
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
                "solver_backend": "mock",
                "pm4_validation_profile": "basic",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "pm4sand",
                        "material_params": {"Dr": 0.45, "G0": 600.0, "hpo": 0.53},
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
                "opensees_executable": "OpenSees",
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


def test_web_wizard_sanity_check_warns_for_low_timeout_budget(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    motion_path = tmp_path / "long_motion.csv"
    t = np.arange(0.0, 200.0, 0.01, dtype=np.float64)
    acc = 0.5 * np.sin(2.0 * np.pi * 1.0 * t)
    np.savetxt(motion_path, np.column_stack([t, acc]), delimiter=",")

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/sanity-check",
        json={
            "analysis_step": {
                "project_name": "wizard-timeout-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "opensees",
                "pm4_validation_profile": "basic",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "pm4sand",
                        "material_params": {"Dr": 0.45, "G0": 600.0, "hpo": 0.53},
                        "material_optional_args": [],
                    }
                ]
            },
            "motion_step": {
                "motion_path": str(motion_path),
                "units": "m/s2",
                "baseline": "remove_mean",
                "scale_mode": "none",
                "dt_override": 0.01,
            },
            "damping_step": {"mode": "frequency_independent", "update_matrix": False},
            "control_step": {
                "f_max": 25.0,
                "timeout_s": 120,
                "retries": 1,
                "write_hdf5": True,
                "write_sqlite": True,
                "parquet_export": False,
                "opensees_executable": "OpenSees",
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_timeout.yml",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    warnings = payload.get("warnings", [])
    assert any("timeout_s=" in str(w) and "Recommended >=" in str(w) for w in warnings)
    checks = payload.get("checks", [])
    timeout_checks = [c for c in checks if c.get("name") == "timeout_budget"]
    assert timeout_checks
    assert timeout_checks[0].get("status") in {"warning", "ok"}
    derived = payload.get("derived", {})
    assert float(derived.get("timeout_recommended_s", 0.0)) >= 120.0


def test_web_wizard_sanity_check_warns_when_probe_is_assumed_available(
    tmp_path, monkeypatch
) -> None:
    from dsra1d.interop.opensees.runner import OpenSeesProbeResult
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    def _fake_probe(executable: str, extra_args=None, timeout_s: int = 5):
        _ = (executable, extra_args, timeout_s)
        return OpenSeesProbeResult(
            available=True,
            assumed_available=True,
            resolved=Path("C:/tools/OpenSees.exe"),
            version="unknown",
            stdout="",
            stderr="probe timeout fallback",
            command=["OpenSees", "-version"],
            binary_sha256="a" * 64,
        )

    monkeypatch.setattr("dsra1d.web.app.probe_opensees_executable", _fake_probe)

    client = TestClient(create_app())
    resp = client.post(
        "/api/wizard/sanity-check",
        json={
            "analysis_step": {
                "project_name": "wizard-assumed-probe-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "opensees",
                "pm4_validation_profile": "basic",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "pm4sand",
                        "material_params": {"Dr": 0.45, "G0": 600.0, "hpo": 0.53},
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
                "opensees_executable": "OpenSees",
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_assumed_probe.yml",
            },
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    checks = payload.get("checks", [])
    backend_checks = [c for c in checks if c.get("name") == "backend_probe"]
    assert backend_checks
    assert backend_checks[0].get("status") == "warning"
    assert "assumed" in str(backend_checks[0].get("message", "")).lower()
    derived = payload.get("derived", {})
    assert derived.get("opensees_probe_assumed_available") is True


def test_web_config_from_wizard_invalid_opensees_material_returns_400(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.post(
        "/api/config/from-wizard",
        json={
            "analysis_step": {
                "project_name": "wizard-invalid-case",
                "boundary_condition": "elastic_halfspace",
                "solver_backend": "opensees",
                "pm4_validation_profile": "basic",
            },
            "profile_step": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "mkz",
                        "material_params": {"gmax": 60000.0, "gamma_ref": 0.001},
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
                "opensees_executable": "OpenSees",
                "output_dir": str(tmp_path / "out"),
                "config_output_dir": str(tmp_path),
                "config_file_name": "wizard_case_invalid.yml",
            },
        },
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "OpenSees backend currently supports pm4sand/pm4silt/elastic" in detail


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


def test_web_run_endpoint_success_with_relative_paths(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    out_root = tmp_path / "run_out"
    resp = client.post(
        "/api/run",
        json={
            "config_path": "examples/configs/effective_stress.yml",
            "motion_path": "examples/motions/sample_motion.csv",
            "output_root": str(out_root),
            "backend": "mock",
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["backend"] == "mock"
    assert payload["status"] == "ok"
    assert Path(payload["output_root"]).resolve() == out_root.resolve()
    assert (out_root / payload["run_id"]).exists()


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
                "solver_backend": "opensees",
                "status": "error",
                "message": "OpenSees failed before result stores were written.",
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
            "config_path": "examples/configs/effective_stress.yml",
            "motion_path": "examples/motions/not_found_motion.csv",
            "output_root": str(tmp_path / "run_out"),
            "backend": "mock",
        },
    )
    assert resp.status_code == 400
    detail = resp.json().get("detail", "")
    assert "Motion file not found" in detail


def test_web_runs_tree_and_results_summary_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
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
        cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
        cfg.analysis.solver_backend = "mock"
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


def test_web_results_summary_exposes_timeout_recovery_convergence(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
    run_dir = Path(result.output_dir)
    run_meta_path = run_dir / "run_meta.json"
    meta = json.loads(run_meta_path.read_text(encoding="utf-8"))
    meta["solver_backend"] = "opensees"
    meta["timeout_s_configured"] = 120
    meta["timeout_s_effective"] = 540
    meta["opensees_timeout_recovered"] = {
        "recovered": True,
        "coverage_ratio": 0.91,
        "timeout_s_effective": 540,
    }
    meta.pop("opensees_diagnostics", None)
    run_meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    root = tmp_path / "web-runs"
    client = TestClient(create_app())
    summary_resp = client.get(
        f"/api/runs/{result.run_id}/results/summary",
        params={"output_root": str(root)},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    conv = summary["convergence"]
    assert conv["available"] is True
    assert conv["source"] == "opensees_timeout_recovered"
    assert conv["severity"] == "warning"
    assert int(conv["timeout_s_configured"]) == 120
    assert int(conv["timeout_s_effective"]) == 540
    assert conv["timeout_recovered"] is True

    runs_resp = client.get("/api/runs", params={"output_root": str(root)})
    assert runs_resp.status_code == 200
    rows = runs_resp.json()
    row = next(item for item in rows if item["run_id"] == result.run_id)
    assert row["convergence_mode"] == "solver"
    assert row["convergence_severity"] == "warning"


def test_web_runs_endpoint_scans_nested_output_root(tmp_path) -> None:
    from dsra1d.config import load_project_config
    from dsra1d.motion import load_motion
    from dsra1d.pipeline import run_analysis
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    nested_root = tmp_path / "workspace" / "campaign" / "runs"
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "mock"
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
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.analysis.solver_backend = "mock"
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

    result = _make_mock_run(tmp_path)
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
    layer0 = payload["layers"][0]
    assert "layer_index" in layer0
    assert "strain" in layer0 and "stress" in layer0
    assert len(layer0["strain"]) >= 10
    assert len(layer0["stress"]) == len(layer0["strain"])


def test_web_results_hysteresis_prefers_recorded_layer_channels(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
    run_dir = Path(result.output_dir)
    t = np.linspace(0.0, 12.0, 240, dtype=np.float64)
    strain = 8.0e-4 * np.sin(2.0 * np.pi * 0.8 * t)
    stress = 42.0 * np.sin((2.0 * np.pi * 0.8 * t) + 0.28)
    # Layer-1 recorder naming follows OpenSees material tag convention (1-based).
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
    assert payload["source"] in {"opensees_recorders", "mixed_recorders_proxy"}
    first_layer = next(layer for layer in payload["layers"] if layer["layer_index"] == 0)
    assert first_layer["is_proxy"] is False
    assert "recorded" in str(first_layer["model"])
    assert len(first_layer["strain"]) >= 20
    assert len(first_layer["stress"]) >= 20


def test_web_results_profile_summary_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
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
    assert first["sigma_v0_mid_kpa"] is not None
    assert first["delta_u_max"] == pytest.approx(24.0, rel=1e-6)
    assert first["sigma_v_eff_min"] is not None
    assert first["ru_max"] is not None


def test_web_download_profile_summary_csv_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
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


def test_web_parity_latest_endpoint_reads_latest_report(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    root = tmp_path / "campaign"
    root.mkdir(parents=True, exist_ok=True)
    benchmark = {
        "suite": "opensees-parity",
        "generated_utc": "2026-03-04T12:00:00Z",
        "all_passed": False,
        "ran": 5,
        "total_cases": 6,
        "skipped": 1,
        "skipped_backend": 1,
        "execution_coverage": 5.0 / 6.0,
        "backend_ready": False,
        "backend_fingerprint_ok": False,
        "backend_probe": {"binary_sha256": "abc123"},
        "cases": [
            {
                "name": "parity01",
                "status": "skipped",
                "skip_kind": "probe_failed",
                "reason": "OpenSees backend probe failed",
            }
        ],
    }
    (root / "benchmark_opensees-parity.json").write_text(
        json.dumps(benchmark, indent=2),
        encoding="utf-8",
    )

    client = TestClient(create_app())
    resp = client.get("/api/parity/latest", params={"output_root": str(root)})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["found"] is True
    assert payload["suite"] == "opensees-parity"
    assert isinstance(payload["suites"], list)
    assert len(payload["suites"]) >= 1
    row = payload["suites"][0]
    assert row["suite"] == "opensees-parity"
    assert "execution_coverage" in row
    assert "block_reasons" in row


def test_web_release_signoff_latest_endpoint_reads_summary(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    root = tmp_path / "campaign"
    root.mkdir(parents=True, exist_ok=True)
    summary = {
        "suite": "release-signoff",
        "generated_utc": "2026-03-04T12:45:00Z",
        "benchmark": {"all_passed": True, "backend_probe": {"assumed_available": True}},
        "verify_batch": {"ok": True},
        "policy": {"campaign": {"passed": False}},
        "signoff": {
            "strict_signoff": True,
            "passed": False,
            "conditions": {
                "campaign_policy_passed": False,
                "backend_fingerprint_ok": True,
                "backend_probe_not_assumed": False,
            },
            "observed": {"backend_probe_sha256": "a" * 64},
            "policy": {"opensees_fingerprint": "b" * 64},
        },
    }
    (root / "campaign_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    client = TestClient(create_app())
    resp = client.get("/api/release/signoff/latest", params={"output_root": str(root)})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["found"] is True
    assert payload["suite"] == "release-signoff"
    assert payload["strict_signoff"] is True
    assert payload["release_ready"] is False
    assert payload["signoff_passed"] is False
    assert payload["campaign_policy_passed"] is False
    assert payload["benchmark_all_passed"] is True
    assert payload["verify_ok"] is True
    assert payload["benchmark_backend_probe_assumed_available"] is True
    assert payload["benchmark_ran"] == 0
    assert payload["benchmark_total_cases"] == 0
    assert payload["benchmark_execution_coverage"] == 0.0
    assert payload["fingerprint_match"] is False
    assert payload["severity_score"] >= 20
    assert payload["severity_label"] in {"warning", "high", "critical"}
    assert "campaign_policy_passed" in payload["condition_failures"]
    assert "campaign_policy_failed" in payload["blocker_categories"]
    assert "backend_probe_assumed" in payload["blocker_categories"]
    assert "fingerprint_mismatch" in payload["blocker_categories"]
    assert "signoff_not_passed" in payload["blocker_categories"]
    assert payload["observed_backend_sha256"] == "a" * 64
    assert payload["policy_backend_sha256"] == "b" * 64


def test_web_release_signoff_latest_endpoint_handles_missing_summary(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    root = tmp_path / "empty"
    root.mkdir(parents=True, exist_ok=True)
    client = TestClient(create_app())
    resp = client.get("/api/release/signoff/latest", params={"output_root": str(root)})
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["found"] is False
    assert payload["severity_score"] == 0
    assert payload["severity_label"] == "unknown"


def test_web_science_confidence_endpoint_returns_rows() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/science/confidence")
    assert resp.status_code == 200
    payload = resp.json()
    assert "source_path" in payload
    assert "rows" in payload
    assert isinstance(payload["rows"], list)
    assert len(payload["rows"]) >= 1
    first = payload["rows"][0]
    assert "suite" in first
    assert "reference_basis" in first
    assert "confidence_tier" in first
