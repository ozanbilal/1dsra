from __future__ import annotations

from pathlib import Path

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
    assert payload["requested"] == "OpenSees"
    assert "available" in payload
    assert "version" in payload


def test_web_runs_endpoint_returns_list() -> None:
    from dsra1d.web.app import create_app
    from fastapi.testclient import TestClient

    client = TestClient(create_app())
    resp = client.get("/api/runs")
    assert resp.status_code == 200
    payload = resp.json()
    assert isinstance(payload, list)


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

    summary_resp = client.get(
        f"/api/runs/{result.run_id}/results/summary",
        params={"output_root": str(root)},
    )
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["run_id"] == result.run_id
    assert "metrics" in summary
    assert "convergence" in summary


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
