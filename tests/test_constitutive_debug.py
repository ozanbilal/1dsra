from __future__ import annotations

import csv
import json
import sqlite3

import h5py
import numpy as np
import pytest

from dsra1d.config import BedrockProperties, BoundaryCondition, load_project_config
from dsra1d.constitutive_debug import (
    analyze_elastic_boundary_force_audit,
    compare_boundary_sensitivity_runs,
    replay_reference_hysteresis,
    run_elastic_boundary_force_audit,
    run_solver_layer_sweep_audit,
)
from dsra1d.post import compute_spectra


def test_replay_reference_hysteresis_writes_debug_artifacts(tmp_path) -> None:
    reference_csv = tmp_path / "hysteresis.csv"
    with reference_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["strain", "stress"])
        writer.writerows(
            [
                [0.0, 0.0],
                [0.0010, 50.0],
                [0.0020, 70.0],
                [0.0010, 45.0],
                [-0.0010, -40.0],
                [-0.0020, -68.0],
                [-0.0010, -42.0],
                [0.0005, 20.0],
            ]
        )

    result = replay_reference_hysteresis(
        "examples/native/deepsoil_gqh_5layer_baseline.yml",
        reference_csv,
        tmp_path / "debug_out",
        layer_index=0,
        mode_code_override=3.0,
    )

    assert result.artifacts.replay_csv.exists()
    assert result.artifacts.summary_json.exists()
    assert result.summary.point_count == 8
    assert result.summary.reason_counts["0"] >= 1
    with result.artifacts.replay_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        first_row = next(reader)
    assert "branch_kind" in first_row
    assert "f_mrdf" in first_row


def test_run_solver_layer_sweep_audit_writes_layer_summary(tmp_path) -> None:
    motion_csv = tmp_path / "motion.csv"
    with motion_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["time_s", "acc_m_s2"])
        for idx in range(12):
            writer.writerow([idx * 0.005, 0.25 * (-1 if idx % 2 else 1)])

    result = run_solver_layer_sweep_audit(
        "examples/native/deepsoil_gqh_5layer_baseline.yml",
        motion_csv,
        tmp_path / "sweep_out",
        mode_code_override=4.0,
    )

    assert result.artifacts.audit_csv.exists()
    assert result.artifacts.layer_summary_csv.exists()
    assert result.summary.state_count > 0
    assert len(result.summary.layers) == 5
    mean_sum = sum(
        row.mean_compliance_fraction for row in result.summary.layers if row.mean_compliance_fraction is not None
    )
    assert mean_sum == pytest.approx(1.0, rel=1.0e-6, abs=1.0e-6)


def test_run_elastic_boundary_force_audit_writes_summary(tmp_path) -> None:
    motion_csv = tmp_path / "motion.csv"
    with motion_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["time_s", "acc_m_s2"])
        for idx in range(24):
            writer.writerow([idx * 0.005, 0.05 * (idx + 1)])

    result = run_elastic_boundary_force_audit(
        "examples/native/deepsoil_gqh_5layer_baseline.yml",
        motion_csv,
        tmp_path / "boundary_out",
    )

    assert result.artifacts.audit_csv.exists()
    assert result.artifacts.summary_json.exists()
    assert result.summary.row_count == 24
    assert result.summary.incident_force_abs_max is not None
    assert result.summary.incident_force_abs_max > 0.0
    assert result.summary.dashpot_force_abs_max is not None
    assert result.summary.net_boundary_force_abs_max is not None


def test_analyze_elastic_boundary_force_audit_extracts_frequency_metrics(tmp_path) -> None:
    audit_csv = tmp_path / "elastic_boundary_force_audit.csv"
    with audit_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "step",
                "time_s",
                "input_acc_m_s2",
                "input_vel_m_s",
                "incident_force",
                "base_relative_velocity_m_s",
                "dashpot_force",
                "net_boundary_force",
                "base_relative_displacement_m",
                "base_relative_acceleration_m_s2",
                "surface_acceleration_m_s2",
                "impedance_c",
            ]
        )
        dt = 0.01
        freq_hz = 2.0
        for idx in range(256):
            t = idx * dt
            incident = float(np.sin(2.0 * np.pi * freq_hz * t))
            net = 0.2 * incident
            surface = float(np.sin(2.0 * np.pi * freq_hz * t - np.pi / 4.0))
            writer.writerow(
                [
                    idx,
                    t,
                    0.0,
                    0.0,
                    incident,
                    0.0,
                    0.8 * incident,
                    net,
                    0.0,
                    0.0,
                    surface,
                    100.0,
                ]
            )

    result = analyze_elastic_boundary_force_audit(audit_csv, tmp_path / "freq_out")

    assert result.artifacts.summary_json.exists()
    assert result.artifacts.summary_md.exists()
    assert result.summary.row_count == 256
    assert result.summary.dominant_surface_frequency_hz == pytest.approx(1.953125, rel=1.0e-6)
    assert result.summary.net_to_incident_amplitude_ratio_at_surface_peak == pytest.approx(0.2, rel=1.0e-3)


def _write_synthetic_run(
    run_dir,
    *,
    boundary_condition: BoundaryCondition,
    bottom_vs_m_s: float,
    bedrock_vs_m_s: float | None,
    raw_input: np.ndarray,
    applied_input: np.ndarray,
    surface_acc: np.ndarray,
    layer_scale: float,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    time = np.arange(raw_input.size, dtype=np.float64) * 0.01
    node_depth_m = np.array([0.0, 4.0, 8.0, 12.0, 16.0, 20.0], dtype=np.float64)
    depth_scales = np.linspace(1.0, 0.35, node_depth_m.size, dtype=np.float64).reshape(-1, 1)
    nodal_displacement_m = depth_scales * (
        0.004 * layer_scale * np.sin(2.0 * np.pi * 1.4 * time)
        + 0.0015 * np.sin(2.0 * np.pi * 2.2 * time)
    )

    periods = np.logspace(np.log10(0.05), np.log10(10.0), 140)
    spectra = compute_spectra(surface_acc, 0.01, periods=periods)

    with h5py.File(run_dir / "results.h5", "w") as h5:
        h5.create_dataset("/meta/delta_t_s", data=np.array([0.01], dtype=np.float64))
        h5.create_dataset("/meta/input_delta_t_s", data=np.array([0.01], dtype=np.float64))
        h5.create_dataset("/time", data=time)
        h5.create_dataset("/signals/surface_acc", data=surface_acc)
        h5.create_dataset("/signals/input_acc", data=raw_input)
        h5.create_dataset("/signals/applied_input_acc", data=applied_input)
        h5.create_dataset("/spectra/periods", data=spectra.periods)
        h5.create_dataset("/spectra/psa", data=spectra.psa)
        h5.create_dataset("/mesh/node_depth_m", data=node_depth_m)
        h5.create_dataset("/signals/nodal_disp_m", data=nodal_displacement_m)

    cfg = load_project_config("examples/native/deepsoil_gqh_5layer_baseline.yml")
    cfg.boundary_condition = boundary_condition
    cfg.motion.input_type = "outcrop"
    cfg.profile.layers[-1].vs_m_s = float(bottom_vs_m_s)
    if bedrock_vs_m_s is None:
        cfg.profile.bedrock = None
    else:
        cfg.profile.bedrock = BedrockProperties(
            name="Bedrock",
            vs_m_s=float(bedrock_vs_m_s),
            unit_weight_kN_m3=25.0,
            damping_ratio=0.02,
        )
    (run_dir / "config_snapshot.json").write_text(
        cfg.model_dump_json(by_alias=True, exclude_none=True, indent=2),
        encoding="utf-8",
    )

    conn = sqlite3.connect(run_dir / "results.sqlite")
    try:
        conn.execute(
            "CREATE TABLE layers (idx INTEGER, name TEXT, thickness_m REAL, unit_weight_kN_m3 REAL, vs_m_s REAL, material TEXT)"
        )
        conn.execute(
            "CREATE TABLE mesh_slices (layer_name TEXT, z_top REAL, z_bot REAL, n_sub INTEGER)"
        )
        depth = 0.0
        for idx, layer in enumerate(cfg.profile.layers):
            conn.execute(
                "INSERT INTO layers (idx, name, thickness_m, unit_weight_kN_m3, vs_m_s, material) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    idx,
                    layer.name,
                    float(layer.thickness_m),
                    float(layer.unit_weight_kn_m3),
                    float(layer.vs_m_s),
                    str(layer.material),
                ),
            )
            conn.execute(
                "INSERT INTO mesh_slices (layer_name, z_top, z_bot, n_sub) VALUES (?, ?, ?, ?)",
                (
                    layer.name,
                    depth,
                    depth + float(layer.thickness_m),
                    1,
                ),
            )
            depth += float(layer.thickness_m)
        conn.commit()
    finally:
        conn.close()

    with (run_dir / "layer_response_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            [
                "layer_index",
                "layer_tag",
                "layer_name",
                "z_mid_m",
                "gamma_max",
                "tau_peak_kpa",
                "secant_g_pa",
                "secant_g_over_gmax",
            ]
        )
        depth = 0.0
        for idx, layer in enumerate(cfg.profile.layers):
            z_mid = depth + 0.5 * float(layer.thickness_m)
            gamma_max = (0.003 + 0.0002 * idx) * layer_scale
            tau_peak_kpa = (55.0 + 4.0 * idx) * layer_scale
            secant_g_pa = (8.0e7 - 2.5e6 * idx) * layer_scale
            secant_g_over_gmax = (0.72 - 0.04 * idx) * (0.92 + 0.08 * layer_scale)
            writer.writerow(
                [
                    idx,
                    idx + 1,
                    layer.name,
                    z_mid,
                    gamma_max,
                    tau_peak_kpa,
                    secant_g_pa,
                    secant_g_over_gmax,
                ]
            )
            depth += float(layer.thickness_m)


def test_compare_boundary_sensitivity_runs_writes_verification_artifacts(tmp_path) -> None:
    time = np.arange(0, 2.56, 0.01, dtype=np.float64)
    raw_input = 0.28 * 9.81 * np.sin(2.0 * np.pi * 1.9 * time)
    applied_rigid = 0.50 * raw_input
    applied_elastic = 0.93 * raw_input
    surface_rigid = (
        0.55 * 9.81 * np.sin(2.0 * np.pi * 2.00 * time - 0.06)
        + 0.08 * 9.81 * np.sin(2.0 * np.pi * 4.20 * time)
    )
    surface_elastic = (
        0.76 * 9.81 * np.sin(2.0 * np.pi * 1.78 * time - 0.04)
        + 0.10 * 9.81 * np.sin(2.0 * np.pi * 4.00 * time)
    )

    rigid_dir = tmp_path / "run-rigid"
    elastic_dir = tmp_path / "run-elastic"
    _write_synthetic_run(
        rigid_dir,
        boundary_condition=BoundaryCondition.RIGID,
        bottom_vs_m_s=500.0,
        bedrock_vs_m_s=None,
        raw_input=raw_input,
        applied_input=applied_rigid,
        surface_acc=surface_rigid,
        layer_scale=1.00,
    )
    _write_synthetic_run(
        elastic_dir,
        boundary_condition=BoundaryCondition.ELASTIC_HALFSPACE,
        bottom_vs_m_s=760.0,
        bedrock_vs_m_s=760.0,
        raw_input=raw_input,
        applied_input=applied_elastic,
        surface_acc=surface_elastic,
        layer_scale=1.18,
    )

    result = compare_boundary_sensitivity_runs(
        rigid_dir,
        elastic_dir,
        tmp_path / "boundary_compare",
        label_a="rigid",
        label_b="elastic_halfspace",
    )

    assert result.artifacts.summary_json.exists()
    assert result.artifacts.summary_md.exists()
    assert result.artifacts.layer_delta_csv.exists()
    assert result.summary.config.same_upper_layers is True
    assert result.summary.config.only_last_layer_or_boundary_changed is True
    assert result.summary.raw_input_history_nrmse == pytest.approx(0.0, abs=1.0e-12)
    assert result.summary.applied_input_history_nrmse is not None
    assert result.summary.applied_input_history_nrmse > 0.0
    assert result.summary.surface_pga_ratio_b_over_a is not None
    assert result.summary.surface_pga_ratio_b_over_a > 1.0
    assert result.summary.surface_peak_period_shift_pct_b_vs_a is not None
    assert result.summary.surface_peak_period_shift_pct_b_vs_a > 0.0
    assert result.summary.profile_depth_points == 5
    with result.artifacts.summary_json.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    assert payload["summary"]["config"]["boundary_condition_a"] == "rigid"
    assert payload["summary"]["config"]["boundary_condition_b"] == "elastic_halfspace"
    with result.artifacts.summary_md.open("r", encoding="utf-8") as fh:
        markdown = fh.read()
    assert "Boundary Sensitivity Verification" in markdown
    with result.artifacts.layer_delta_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        first_row = next(reader)
    assert "gamma_max_ratio_b_over_a" in first_row
