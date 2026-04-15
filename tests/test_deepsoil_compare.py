from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import h5py
import numpy as np
import pytest
from dsra1d.deepsoil_compare import (
    _load_profile_from_run,
    compare_deepsoil_manifest,
    compare_deepsoil_run,
)
from dsra1d.deepsoil_excel import import_deepsoil_excel_bundle
from dsra1d.post import compute_spectra


def _workbook_path(name: str) -> Path:
    path = Path(__file__).with_name(name)
    if not path.exists():
        pytest.skip(f"Missing DeepSoil workbook fixture: {name}")
    return path


def _write_minimal_run(run_dir: Path, time: np.ndarray, acc: np.ndarray) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    dt = float(np.median(np.diff(time)))
    spectra = compute_spectra(acc, dt)
    with h5py.File(run_dir / "results.h5", "w") as h5:
        h5.create_dataset("/meta/delta_t_s", data=np.asarray([dt], dtype=np.float64))
        h5.create_dataset("/time", data=time)
        h5.create_dataset("/signals/surface_acc", data=acc)
        h5.create_dataset("/spectra/periods", data=spectra.periods)
        h5.create_dataset("/spectra/psa", data=spectra.psa)


def _write_profile_sqlite(run_dir: Path) -> None:
    conn = sqlite3.connect(run_dir / "results.sqlite")
    try:
        conn.execute(
            "CREATE TABLE layers ("
            "idx INTEGER, name TEXT, thickness_m REAL, unit_weight_kN_m3 REAL, "
            "vs_m_s REAL, material TEXT)"
        )
        conn.execute(
            "CREATE TABLE mesh_slices (layer_name TEXT, z_top REAL, z_bot REAL, n_sub INTEGER)"
        )
        conn.execute(
            "CREATE TABLE eql_layers (layer_idx INTEGER, gamma_max REAL)"
        )
        conn.execute(
            "INSERT INTO layers VALUES (0, 'Layer-1', 5.0, 18.0, 180.0, 'mkz')"
        )
        conn.execute(
            "INSERT INTO mesh_slices VALUES ('Layer-1', 0.0, 5.0, 2)"
        )
        conn.execute(
            "INSERT INTO eql_layers VALUES (0, 0.0015)"
        )
        conn.commit()
    finally:
        conn.close()


def _write_workbook_compare_run(run_dir: Path, bundle_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    surface = np.loadtxt(bundle_dir / "surface.csv", delimiter=",", skiprows=1)
    input_motion = np.loadtxt(bundle_dir / "input_motion.csv", delimiter=",", skiprows=1)
    profile = np.loadtxt(bundle_dir / "profile.csv", delimiter=",", skiprows=1)
    mobilized = np.loadtxt(bundle_dir / "mobilized_strength.csv", delimiter=",", skiprows=1)
    hysteresis = np.loadtxt(bundle_dir / "hysteresis_layer1.csv", delimiter=",", skiprows=1)

    if profile.ndim == 1:
        profile = profile.reshape(1, -1)
    if mobilized.ndim == 1:
        mobilized = mobilized.reshape(1, -1)

    time = np.asarray(surface[:, 0], dtype=np.float64)
    acc = np.asarray(surface[:, 1], dtype=np.float64)
    input_time = np.asarray(input_motion[:, 0], dtype=np.float64)
    input_acc = np.asarray(input_motion[:, 1], dtype=np.float64)
    dt = float(np.median(np.diff(time)))
    input_dt = float(np.median(np.diff(input_time)))
    spectra = compute_spectra(acc, dt)

    depth = np.asarray(profile[:, 0], dtype=np.float64)
    max_disp = np.asarray(profile[:, 3], dtype=np.float64)
    node_depth = np.concatenate(([0.0], depth))
    amp = np.concatenate(([max_disp[0]], max_disp))
    phase = np.sin(np.linspace(0.0, 2.0 * np.pi, time.size, dtype=np.float64))
    nodal_disp = amp[:, None] * phase[None, :]

    with h5py.File(run_dir / "results.h5", "w") as h5:
        h5.create_dataset("/meta/delta_t_s", data=np.asarray([dt], dtype=np.float64))
        h5.create_dataset("/meta/input_delta_t_s", data=np.asarray([input_dt], dtype=np.float64))
        h5.create_dataset("/time", data=time)
        h5.create_dataset("/signals/surface_acc", data=acc)
        h5.create_dataset("/signals/input_acc", data=input_acc)
        h5.create_dataset("/signals/applied_input_acc", data=0.5 * input_acc)
        h5.create_dataset("/spectra/periods", data=spectra.periods)
        h5.create_dataset("/spectra/psa", data=spectra.psa)
        h5.create_dataset("/mesh/node_depth_m", data=node_depth)
        h5.create_dataset("/signals/nodal_disp_m", data=nodal_disp)
        h5.create_dataset("/pwp/time", data=time)
        h5.create_dataset("/pwp/ru", data=np.zeros_like(time))
        h5.create_dataset("/pwp/delta_u", data=np.zeros_like(time))
        h5.create_dataset("/pwp/sigma_v_eff", data=np.full_like(time, 100.0))

    conn = sqlite3.connect(run_dir / "results.sqlite")
    try:
        conn.execute(
            "CREATE TABLE layers (idx INTEGER, name TEXT, thickness_m REAL, unit_weight_kN_m3 REAL, vs_m_s REAL, material TEXT)"
        )
        conn.execute(
            "CREATE TABLE mesh_slices (layer_name TEXT, z_top REAL, z_bot REAL, n_sub INTEGER)"
        )
        conn.execute(
            "CREATE TABLE eql_layers (layer_idx INTEGER, gamma_max REAL)"
        )
        for idx in range(5):
            z_top = idx * 4.0
            z_bot = z_top + 4.0
            conn.execute(
                "INSERT INTO layers VALUES (?, ?, ?, ?, ?, ?)",
                (idx, f"Layer-{idx + 1}", 4.0, 20.0, 500.0, "gqh"),
            )
            conn.execute(
                "INSERT INTO mesh_slices VALUES (?, ?, ?, ?)",
                (f"Layer-{idx + 1}", z_top, z_bot, 1),
            )
            gamma_pct = float(profile[min(idx, profile.shape[0] - 1), 4])
            conn.execute(
                "INSERT INTO eql_layers VALUES (?, ?)",
                (idx, gamma_pct / 100.0),
            )
        conn.commit()
    finally:
        conn.close()

    summary_lines = [
        "layer_index,layer_tag,layer_name,z_mid_m,gamma_max,tau_peak_kpa,secant_g_pa,secant_g_over_gmax"
    ]
    for idx in range(5):
        z_mid = 2.0 + 4.0 * idx
        gamma_pct = float(profile[min(idx, profile.shape[0] - 1), 4])
        strength = float(mobilized[min(idx, mobilized.shape[0] - 1), 1])
        summary_lines.append(
            ",".join(
                [
                    str(idx),
                    str(idx + 1),
                    f"\"Layer-{idx + 1}\"",
                    f"{z_mid:.8f}",
                    f"{(gamma_pct / 100.0):.10e}",
                    f"{strength:.10e}",
                    f"{1.0e8:.10e}",
                    f"{0.8:.10e}",
                ]
            )
        )
    (run_dir / "layer_response_summary.csv").write_text("\n".join(summary_lines), encoding="utf-8")
    if hysteresis.ndim == 1:
        hysteresis = hysteresis.reshape(1, -1)
    if hysteresis.shape[1] >= 2:
        n_h = hysteresis.shape[0]
        hysteresis_time = np.linspace(0.0, max((n_h - 1) * dt, dt), n_h, dtype=np.float64)
        np.savetxt(
            run_dir / "layer_1_strain.out",
            np.column_stack([hysteresis_time, hysteresis[:, 0]]),
        )
        np.savetxt(
            run_dir / "layer_1_stress.out",
            np.column_stack([hysteresis_time, hysteresis[:, 1]]),
        )

    config_snapshot = {
        "project_name": "compare-workbook-run",
        "boundary_condition": "rigid",
        "profile": {
            "layers": [
                {
                    "name": f"Layer-{idx + 1}",
                    "thickness_m": 4.0,
                    "unit_weight_kN_m3": 20.0,
                    "vs_m_s": 500.0,
                    "material": "gqh",
                    "material_params": {
                        "gmax": 509684.0,
                        "tau_max": 419.514,
                        "theta1": -6.71,
                        "theta2": 1.17,
                        "theta3": 15.4881661891248,
                        "theta4": 1.0,
                        "theta5": 0.99,
                        "reload_factor": 1.6,
                        "mrdf_p1": 0.82,
                        "mrdf_p2": 0.55,
                        "mrdf_p3": 20.0,
                    },
                }
                for idx in range(5)
            ]
        },
        "motion": {"units": "m/s2", "input_type": "outcrop"},
        "analysis": {
            "solver_backend": "nonlinear",
            "damping_mode": "frequency_independent",
            "viscous_damping_update": False,
            "dt": dt,
            "f_max": 25.0,
        },
    }
    (run_dir / "config_snapshot.json").write_text(
        json.dumps(config_snapshot, indent=2),
        encoding="utf-8",
    )


def test_compare_deepsoil_run_writes_artifacts(tmp_path: Path) -> None:
    dt = 0.01
    time = np.arange(0.0, 8.0 + dt, dt)
    acc = 0.6 * np.sin(2.0 * np.pi * 1.7 * time) * np.exp(-0.12 * time)
    run_dir = tmp_path / "run-sample"
    _write_minimal_run(run_dir, time, acc)

    ref_acc = 1.02 * acc
    surface_csv = tmp_path / "deepsoil_surface.csv"
    np.savetxt(
        surface_csv,
        np.column_stack([time, ref_acc]),
        delimiter=",",
        header="time_s,acc_m_s2",
        comments="",
    )

    out_dir = tmp_path / "compare_out"
    result = compare_deepsoil_run(run_dir, surface_csv=surface_csv, out_dir=out_dir)

    assert result.overlap_samples > 100
    assert result.surface_corrcoef > 0.999
    assert result.pga_ratio == pytest.approx(1.0 / 1.02, rel=1.0e-3)
    assert result.artifacts is not None
    assert result.artifacts.json_path.exists()
    assert result.artifacts.markdown_path.exists()

    payload = json.loads(result.artifacts.json_path.read_text(encoding="utf-8"))
    assert payload["run_id"] == "run-sample"
    assert payload["psa_point_count"] > 10


def test_compare_deepsoil_run_with_reference_psa_csv(tmp_path: Path) -> None:
    dt = 0.01
    time = np.arange(0.0, 6.0 + dt, dt)
    acc = 0.4 * np.sin(2.0 * np.pi * 2.3 * time)
    run_dir = tmp_path / "run-psa"
    _write_minimal_run(run_dir, time, acc)

    surface_csv = tmp_path / "deepsoil_surface.csv"
    np.savetxt(
        surface_csv,
        np.column_stack([time, acc]),
        delimiter=",",
        header="time_s,acc_m_s2",
        comments="",
    )

    ref_periods = np.logspace(np.log10(0.05), np.log10(3.0), 30)
    ref_psa = compute_spectra(1.03 * acc, dt, periods=ref_periods).psa
    psa_csv = tmp_path / "deepsoil_psa.csv"
    np.savetxt(
        psa_csv,
        np.column_stack([ref_periods, ref_psa]),
        delimiter=",",
        header="period_s,psa_m_s2",
        comments="",
    )

    result = compare_deepsoil_run(
        run_dir,
        surface_csv=surface_csv,
        psa_csv=psa_csv,
        out_dir=tmp_path / "compare_psa",
    )

    assert result.used_reference_psa_csv is True
    assert result.psa_point_count >= 3
    assert np.isfinite(result.psa_nrmse)
    assert result.psa_peak_period_s > 0.0


def test_compare_deepsoil_manifest_aggregates_cases(tmp_path: Path) -> None:
    dt = 0.01
    time = np.arange(0.0, 4.0 + dt, dt)
    acc = 0.3 * np.sin(2.0 * np.pi * 1.5 * time)

    run_ok = tmp_path / "run-ok"
    run_bad = tmp_path / "run-bad"
    _write_minimal_run(run_ok, time, acc)
    _write_minimal_run(run_bad, time, acc)

    surface_ok = tmp_path / "surface_ok.csv"
    surface_bad = tmp_path / "surface_bad.csv"
    np.savetxt(
        surface_ok,
        np.column_stack([time, 1.01 * acc]),
        delimiter=",",
        header="time_s,acc_m_s2",
        comments="",
    )
    np.savetxt(
        surface_bad,
        np.column_stack([time, 0.1 * acc]),
        delimiter=",",
        header="time_s,acc_m_s2",
        comments="",
    )

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "defaults": {
                    "surface_corrcoef_min": 0.9,
                    "surface_nrmse_max": 0.2,
                    "psa_nrmse_max": 0.2,
                    "pga_pct_diff_abs_max": 15.0,
                },
                "cases": [
                    {
                        "name": "ok-case",
                        "run": "run-ok",
                        "surface_csv": "surface_ok.csv",
                    },
                    {
                        "name": "bad-case",
                        "run": "run-bad",
                        "surface_csv": "surface_bad.csv",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    result = compare_deepsoil_manifest(manifest, out_dir=tmp_path / "batch_out")
    assert result.total_cases == 2
    assert result.passed_cases == 1
    assert result.failed_cases == 1
    assert result.artifacts is not None
    assert result.artifacts.json_path.exists()
    assert result.artifacts.markdown_path.exists()


def test_compare_deepsoil_run_with_profile_and_hysteresis(tmp_path: Path) -> None:
    dt = 0.01
    time = np.arange(0.0, 6.0 + dt, dt)
    acc = 0.3 * np.sin(2.0 * np.pi * 1.2 * time)
    run_dir = tmp_path / "run-profile-hyst"
    _write_minimal_run(run_dir, time, acc)
    _write_profile_sqlite(run_dir)

    pwp = -np.linspace(0.0, 10.0, time.size)
    np.savetxt(run_dir / "layer_1_pwp_raw.out", np.column_stack([time, pwp]))

    strain = 0.0015 * np.sin(np.linspace(0.0, 2.0 * np.pi, 400))
    stress = 45.0 * np.sin(np.linspace(0.0, 2.0 * np.pi, 400))
    np.savetxt(run_dir / "layer_1_strain.out", np.column_stack([time[:400], strain]))
    np.savetxt(run_dir / "layer_1_stress.out", np.column_stack([time[:400], stress]))

    surface_csv = tmp_path / "deepsoil_surface.csv"
    np.savetxt(
        surface_csv,
        np.column_stack([time, acc]),
        delimiter=",",
        header="time_s,acc_m_s2",
        comments="",
    )
    profile_csv = tmp_path / "deepsoil_profile.csv"
    profile_csv.write_text(
        "\n".join(
            [
                "depth_m,gamma_max,ru_max,sigma_v_eff_min,vs_m_s",
                "2.5,0.0015,0.2222222222,35.0,180.0",
            ]
        ),
        encoding="utf-8",
    )
    hysteresis_csv = tmp_path / "deepsoil_hysteresis.csv"
    np.savetxt(
        hysteresis_csv,
        np.column_stack([strain, stress]),
        delimiter=",",
        header="strain,stress",
        comments="",
    )

    result = compare_deepsoil_run(
        run_dir,
        surface_csv=surface_csv,
        profile_csv=profile_csv,
        hysteresis_csv=hysteresis_csv,
        hysteresis_layer=0,
        out_dir=tmp_path / "compare_full",
    )

    assert result.profile is not None
    assert "gamma_max" in result.profile.compared_metrics
    assert result.profile.gamma_max_nrmse == pytest.approx(0.0, abs=1.0e-9)
    assert result.hysteresis is not None
    assert result.hysteresis.stress_path_nrmse == pytest.approx(0.0, abs=1.0e-9)


def test_import_deepsoil_excel_bundle_primary_workbook(tmp_path: Path) -> None:
    workbook = _workbook_path("Results_profile_0_motion_Kocaeli.xlsx")

    bundle = import_deepsoil_excel_bundle(workbook, tmp_path / "bundle-primary")

    assert bundle.case_kind == "primary_gqh"
    assert bundle.sheet_map == {
        "layer_1": "Layer 1",
        "input_motion": "Input Motion",
        "profile": "Profile",
        "mobilized": "Mobilized Shear Stress",
    }
    assert set(bundle.available_artifacts) == {
        "surface.csv",
        "input_motion.csv",
        "psa_surface.csv",
        "psa_input.csv",
        "profile.csv",
        "mobilized_strength.csv",
        "hysteresis_layer1.csv",
    }
    assert bundle.meta_json is not None and bundle.meta_json.exists()
    meta = json.loads(bundle.meta_json.read_text(encoding="utf-8"))
    assert meta["case_kind"] == "primary_gqh"
    assert meta["sheet_map"]["profile"] == "Profile"
    assert meta["column_map"]["profile"]["effective_stress_kpa"] == 1
    assert meta["column_map"]["profile"]["max_displacement_m"] == 7

    surface = np.loadtxt(bundle.surface_csv, delimiter=",", skiprows=1)
    input_motion = np.loadtxt(bundle.input_motion_csv, delimiter=",", skiprows=1)
    psa_surface = np.loadtxt(bundle.psa_surface_csv, delimiter=",", skiprows=1)
    psa_input = np.loadtxt(bundle.psa_input_csv, delimiter=",", skiprows=1)
    profile = np.loadtxt(bundle.profile_csv, delimiter=",", skiprows=1)
    mobilized = np.loadtxt(bundle.mobilized_strength_csv, delimiter=",", skiprows=1)
    hysteresis = np.loadtxt(bundle.hysteresis_csv, delimiter=",", skiprows=1)

    assert surface.ndim == 2 and surface.shape[1] == 2 and surface.shape[0] > 1000
    assert input_motion.ndim == 2 and input_motion.shape[1] == 2 and input_motion.shape[0] > 1000
    assert psa_surface.ndim == 2 and psa_surface.shape[1] == 2 and psa_surface.shape[0] > 10
    assert psa_input.ndim == 2 and psa_input.shape[1] == 2 and psa_input.shape[0] > 10
    assert profile.ndim == 2 and profile.shape == (10, 6)
    assert mobilized.ndim == 2 and mobilized.shape == (5, 3)
    assert hysteresis.ndim == 2 and hysteresis.shape[1] == 2 and hysteresis.shape[0] > 1000
    assert float(np.nanmax(np.abs(hysteresis[:, 1]))) < 1000.0
    assert np.nanmax(profile[:, 1]) > 0.0
    assert np.nanmax(profile[:, 3]) > 0.0
    assert np.nanmax(mobilized[:, 1]) > 0.0


def test_import_deepsoil_excel_bundle_secondary_workbook(tmp_path: Path) -> None:
    workbook = _workbook_path("Results_profile_0_motion_Kocaeli-EL.xlsx")

    bundle = import_deepsoil_excel_bundle(workbook, tmp_path / "bundle-secondary")

    assert bundle.case_kind == "secondary_el"
    assert bundle.meta_json is not None and bundle.meta_json.exists()
    meta = json.loads(bundle.meta_json.read_text(encoding="utf-8"))
    assert meta["case_kind"] == "secondary_el"
    assert meta["sheet_map"]["layer_1"] == "Layer 1"

    profile = np.loadtxt(bundle.profile_csv, delimiter=",", skiprows=1)
    mobilized = np.loadtxt(bundle.mobilized_strength_csv, delimiter=",", skiprows=1)
    assert profile.shape == (10, 6)
    assert mobilized.shape == (5, 3)


def test_compare_deepsoil_run_accepts_real_workbook_bundle(tmp_path: Path) -> None:
    workbook = _workbook_path("Results_profile_0_motion_Kocaeli.xlsx")
    bundle = import_deepsoil_excel_bundle(workbook, tmp_path / "bundle")
    run_dir = tmp_path / "run-primary"
    _write_workbook_compare_run(run_dir, bundle.output_dir)

    result = compare_deepsoil_run(
        run_dir,
        deepsoil_excel=workbook,
        out_dir=tmp_path / "compare-primary",
    )

    assert result.reference_kind == "primary_gqh"
    assert result.base_motion_semantics_ok is True
    assert result.boundary_condition == "rigid"
    assert result.motion_input_type == "outcrop"
    assert result.damping_mode == "frequency_independent"
    assert result.input_history_nrmse is not None
    assert result.input_history_nrmse < 1.0e-9
    assert result.input_psa_nrmse is not None
    assert result.input_psa_nrmse < 0.05
    assert result.applied_input_history_nrmse is not None
    assert result.applied_input_history_nrmse < 1.0e-9
    assert result.applied_input_psa_nrmse is not None
    assert result.applied_input_psa_nrmse < 0.05
    assert result.psa_nrmse < 0.05
    assert result.psa_point_count > 10
    assert result.profile is not None
    assert "effective_stress_kpa" in result.profile.compared_metrics
    assert "max_strain_pct" in result.profile.compared_metrics
    assert "mobilized_strength_kpa" in result.profile.compared_metrics
    assert result.layer_parity is not None
    assert result.layer_parity.row_count == 5
    assert result.layer_parity.gamma_max_nrmse is not None
    assert result.layer_parity.tau_peak_kpa_nrmse is not None
    assert result.layer_parity.secant_g_over_gmax_nrmse is not None
    assert result.backbone_diagnostic is not None
    assert result.backbone_diagnostic.row_count == 5
    assert result.backbone_diagnostic.tau_peak_kpa_nrmse is not None
    assert result.backbone_diagnostic.secant_g_over_gmax_nrmse is not None
    assert result.reload_diagnostic is not None
    assert result.reload_diagnostic.layer_index == 0
    assert result.reload_diagnostic.suspected_driver != ""
    assert result.envelope_diagnostic is not None
    assert result.envelope_diagnostic.layer_index == 0
    assert result.envelope_diagnostic.point_count > 10
    assert result.envelope_diagnostic.recorded_tau_nrmse is not None
    assert result.envelope_diagnostic.backbone_tau_nrmse is not None
    assert result.artifacts is not None
    assert result.artifacts.json_path.exists()
    assert result.artifacts.markdown_path.exists()
    assert result.artifacts.layer_parity_csv is not None
    assert result.artifacts.layer_parity_csv.exists()
    assert result.artifacts.backbone_diagnostic_csv is not None
    assert result.artifacts.backbone_diagnostic_csv.exists()
    assert result.artifacts.hysteresis_envelope_csv is not None
    assert result.artifacts.hysteresis_envelope_csv.exists()


def test_load_profile_from_run_prefers_calibration_mean_effective_stress(
    tmp_path: Path,
) -> None:
    workbook = _workbook_path("Results_profile_0_motion_Kocaeli.xlsx")
    bundle = import_deepsoil_excel_bundle(workbook, tmp_path / "bundle")
    run_dir = tmp_path / "run-primary"
    _write_workbook_compare_run(run_dir, bundle.output_dir)

    snapshot_path = run_dir / "config_snapshot.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    expected = [20.38, 61.14, 101.90, 142.66, 183.42]
    for layer, mean_stress in zip(snapshot["profile"]["layers"], expected, strict=True):
        layer["calibration"] = {
            "source": "darendeli",
            "plasticity_index": 15.0,
            "ocr": 1.0,
            "mean_effective_stress_kpa": mean_stress,
            "frequency_hz": 1.0,
            "num_cycles": 10.0,
            "strain_min": 1.0e-6,
            "strain_max": 0.1,
            "fit_strain_min": 1.0e-6,
            "fit_strain_max": 5.0e-4,
            "target_strength_ratio": 0.95,
            "target_strength_strain": 0.1,
            "n_points": 60,
            "auto_refit_on_reference_change": True,
        }
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    profile = _load_profile_from_run(run_dir)

    assert profile["effective_stress_kpa"] == pytest.approx(expected, rel=0.0, abs=1.0e-9)


def test_compare_deepsoil_manifest_accepts_excel_cases(tmp_path: Path) -> None:
    primary_workbook = _workbook_path("Results_profile_0_motion_Kocaeli.xlsx")
    secondary_workbook = _workbook_path("Results_profile_0_motion_Kocaeli-EL.xlsx")

    primary_bundle = import_deepsoil_excel_bundle(primary_workbook, tmp_path / "bundle-primary")
    secondary_bundle = import_deepsoil_excel_bundle(secondary_workbook, tmp_path / "bundle-secondary")
    _write_workbook_compare_run(tmp_path / "run-primary", primary_bundle.output_dir)
    _write_workbook_compare_run(tmp_path / "run-secondary", secondary_bundle.output_dir)

    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "primary-gqh",
                        "run": "run-primary",
                        "deepsoil_excel": str(primary_workbook),
                    },
                    {
                        "name": "secondary-el",
                        "run": "run-secondary",
                        "deepsoil_excel": str(secondary_workbook),
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = compare_deepsoil_manifest(manifest, out_dir=tmp_path / "batch")

    assert result.total_cases == 2
    assert result.passed_cases == 2
    assert result.failed_cases == 0
    assert result.artifacts is not None
    assert result.artifacts.json_path.exists()
    assert result.artifacts.markdown_path.exists()
    assert result.cases[0]["comparison"]["reference_kind"] == "primary_gqh"
    assert result.cases[1]["comparison"]["reference_kind"] == "secondary_el"
