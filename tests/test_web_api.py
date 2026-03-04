from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import uuid4

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
    assert "available" in payload
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
    assert "pm4sand-calibration" in payload["template_defaults"]


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
    assert (out_root / payload["run_id"]).exists()


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


def test_web_results_profile_summary_endpoint(tmp_path) -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    result = _make_mock_run(tmp_path)
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
        "benchmark": {"all_passed": True},
        "verify_batch": {"ok": True},
        "policy": {"campaign": {"passed": False}},
        "signoff": {
            "strict_signoff": True,
            "passed": False,
            "conditions": {"campaign_policy_passed": False, "backend_fingerprint_ok": True},
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
    assert payload["benchmark_ran"] == 0
    assert payload["benchmark_total_cases"] == 0
    assert payload["benchmark_execution_coverage"] == 0.0
    assert payload["fingerprint_match"] is False
    assert payload["severity_score"] >= 20
    assert payload["severity_label"] in {"warning", "high", "critical"}
    assert "campaign_policy_passed" in payload["condition_failures"]
    assert "campaign_policy_failed" in payload["blocker_categories"]
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
