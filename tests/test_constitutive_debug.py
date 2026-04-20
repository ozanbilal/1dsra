from __future__ import annotations

import csv
import json
import sqlite3

import h5py
import numpy as np
import pytest

import dsra1d.constitutive_debug as constitutive_debug_module
from dsra1d.config import BedrockProperties, BoundaryCondition, load_project_config
from dsra1d.constitutive_debug import (
    LayerComplianceContribution,
    LayerSweepAuditArtifacts,
    LayerSweepAuditResult,
    LayerSweepAuditSummary,
    analyze_elastic_boundary_force_audit,
    compare_case_truth_profile_and_tangent_audit,
    compare_boundary_delta_signatures,
    compare_boundary_sensitivity_deepsoil_db_pair,
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
    assert result.summary.reconstructed_boundary_force_abs_max is not None
    assert result.summary.assembled_boundary_force_abs_max is not None
    assert result.summary.assembled_vs_reconstructed_force_nrmse == pytest.approx(0.0, abs=1.0e-12)


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
    motion_input_type: str = "outcrop",
    bottom_vs_m_s: float,
    bedrock_vs_m_s: float | None,
    raw_input: np.ndarray,
    applied_input: np.ndarray,
    surface_acc: np.ndarray,
    layer_scale: float,
    rigid_translation_scale: float = 0.0,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    time = np.arange(raw_input.size, dtype=np.float64) * 0.01
    node_depth_m = np.array([0.0, 4.0, 8.0, 12.0, 16.0, 20.0], dtype=np.float64)
    depth_scales = np.linspace(1.0, 0.35, node_depth_m.size, dtype=np.float64).reshape(-1, 1)
    nodal_displacement_m = depth_scales * (
        0.004 * layer_scale * np.sin(2.0 * np.pi * 1.4 * time)
        + 0.0015 * np.sin(2.0 * np.pi * 2.2 * time)
    )
    if rigid_translation_scale != 0.0:
        rigid_translation = rigid_translation_scale * np.sin(2.0 * np.pi * 0.9 * time)
        nodal_displacement_m = nodal_displacement_m + rigid_translation.reshape(1, -1)

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
    cfg.motion.input_type = str(motion_input_type)
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


def _write_synthetic_deepsoil_db_run(
    run_dir,
    *,
    halfspace: str,
    input_acc_g: np.ndarray,
    surface_acc_g: np.ndarray,
    surface_disp_m: np.ndarray,
    profile_scale: float,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    db_path = run_dir / "deepsoilout.db3"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("CREATE TABLE INPUT (INPUT BLOB)")
        conn.execute(
            "CREATE TABLE RESPONSE_SPECTRA (PERIOD REAL, INPUT_MOTION_RS REAL, LAYER1_RS REAL)"
        )
        conn.execute(
            "CREATE TABLE PROFILES ("
            "LAYER_NUMBER INTEGER, DEPTH_LAYER_TOP REAL, PGA_TOTAL REAL, PGV_RELATIVE REAL, "
            "MIN_DISP_RELATIVE REAL, MAX_DISP_RELATIVE REAL, DEPTH_LAYER_MID REAL, "
            "INITIAL_EFFECTIVE_STRESS REAL, MAX_STRAIN REAL, MAX_STRESS_RATIO REAL)"
        )
        conn.execute(
            "CREATE TABLE TIME_HISTORIES (TIME REAL, LAYER1_ACCEL REAL, LAYER1_VEL REAL, "
            "LAYER1_DISP REAL, LAYER1_ARIAS REAL, LAYER1_STRAIN REAL, LAYER1_STRESS REAL)"
        )
        conn.execute(
            "CREATE TABLE VEL_DISP (TIME REAL, LAYER1_VEL_TOTAL REAL, LAYER1_VEL_RELATIVE REAL, "
            "LAYER1_DISP_TOTAL REAL, LAYER1_DISP_RELATIVE REAL)"
        )

        periods = np.logspace(np.log10(0.05), np.log10(10.0), 120)
        input_rs = compute_spectra(9.81 * input_acc_g, 0.01, periods=periods).psa / 9.81
        surface_rs = compute_spectra(9.81 * surface_acc_g, 0.01, periods=periods).psa / 9.81
        conn.executemany(
            "INSERT INTO RESPONSE_SPECTRA (PERIOD, INPUT_MOTION_RS, LAYER1_RS) VALUES (?, ?, ?)",
            [
                (float(period), float(inp), float(surf))
                for period, inp, surf in zip(periods, input_rs, surface_rs, strict=True)
            ],
        )

        for idx in range(5):
            depth_top = 4.0 * idx
            depth_mid = depth_top + 2.0
            max_disp = float((0.0025 + 0.0005 * idx) * profile_scale)
            conn.execute(
                "INSERT INTO PROFILES VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    idx + 1,
                    depth_top,
                    float((0.26 + 0.03 * idx) * profile_scale),
                    float((0.08 + 0.01 * idx) * profile_scale),
                    -0.85 * max_disp,
                    max_disp,
                    depth_mid,
                    float(20.0 + 40.0 * idx),
                    float((0.020 + 0.004 * idx) * profile_scale),
                    float((0.55 + 0.08 * idx) * profile_scale),
                ),
            )

        vel = np.gradient(surface_disp_m, 0.01)
        for idx, (t, acc_g, vel_v, disp_v) in enumerate(
            zip(
                np.arange(surface_acc_g.size, dtype=np.float64) * 0.01,
                surface_acc_g,
                vel,
                surface_disp_m,
                strict=True,
            )
        ):
            conn.execute(
                "INSERT INTO TIME_HISTORIES VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    float(t),
                    float(acc_g),
                    float(vel_v),
                    float(disp_v),
                    0.0,
                    float(0.0005 * profile_scale * np.sin(2.0 * np.pi * 1.1 * t)),
                    float(0.12 * profile_scale * np.sin(2.0 * np.pi * 1.1 * t)),
                ),
            )
            conn.execute(
                "INSERT INTO VEL_DISP VALUES (?, ?, ?, ?, ?)",
                (
                    float(t),
                    float(vel_v),
                    float(vel_v),
                    float(disp_v),
                    float(disp_v),
                ),
            )

        input_lines = [
            "[FILE_VERSION]:[1]",
            "[ANALYSIS_TYPE]:[NONLINEAR]",
            f"[HALFSPACE]:[{halfspace}]",
            "[ACCELERATION_HISTORY]:[INTERNAL]",
            f"\t[TIME_STEP]:[0.01] [NUM_POINTS]:[{input_acc_g.size}]",
        ]
        input_lines.extend(f"\t[ACCEL]:[{float(value):.8e}]" for value in input_acc_g)
        conn.execute("INSERT INTO INPUT (INPUT) VALUES (?)", ("\r\n".join(input_lines).encode("utf-8"),))
        conn.commit()
    finally:
        conn.close()


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
    assert result.summary.input_pga_g_a == pytest.approx(0.28, rel=1.0e-6)
    assert result.summary.input_pga_g_b == pytest.approx(0.28, rel=1.0e-6)
    assert result.summary.surface_to_input_pga_amp_a is not None
    assert result.summary.surface_to_input_pga_amp_b is not None
    assert result.summary.surface_to_input_pga_amp_b > result.summary.surface_to_input_pga_amp_a
    assert result.summary.surface_to_input_peak_psa_amp_a is not None
    assert result.summary.surface_to_input_peak_psa_amp_b is not None
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
    assert "Case-Local Amplification" in markdown
    with result.artifacts.layer_delta_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        first_row = next(reader)
    assert "gamma_max_ratio_b_over_a" in first_row


def test_compare_boundary_sensitivity_runs_uses_relative_displacement_for_pgd(tmp_path) -> None:
    time = np.arange(0, 2.56, 0.01, dtype=np.float64)
    raw_input = 0.28 * 9.81 * np.sin(2.0 * np.pi * 1.9 * time)
    applied_rigid = raw_input
    applied_elastic = 0.5 * raw_input
    surface_rigid = 0.70 * 9.81 * np.sin(2.0 * np.pi * 1.65 * time - 0.05)
    surface_elastic = 0.44 * 9.81 * np.sin(2.0 * np.pi * 1.88 * time - 0.03)

    rigid_dir = tmp_path / "run-rigid-within"
    elastic_dir = tmp_path / "run-elastic-outcrop"
    _write_synthetic_run(
        rigid_dir,
        boundary_condition=BoundaryCondition.RIGID,
        motion_input_type="within",
        bottom_vs_m_s=500.0,
        bedrock_vs_m_s=None,
        raw_input=raw_input,
        applied_input=applied_rigid,
        surface_acc=surface_rigid,
        layer_scale=1.0,
        rigid_translation_scale=0.0,
    )
    _write_synthetic_run(
        elastic_dir,
        boundary_condition=BoundaryCondition.ELASTIC_HALFSPACE,
        motion_input_type="outcrop",
        bottom_vs_m_s=760.0,
        bedrock_vs_m_s=760.0,
        raw_input=raw_input,
        applied_input=applied_elastic,
        surface_acc=surface_elastic,
        layer_scale=0.62,
        rigid_translation_scale=0.08,
    )

    result = compare_boundary_sensitivity_runs(
        rigid_dir,
        elastic_dir,
        tmp_path / "boundary_compare_relative",
        label_a="rigid_within",
        label_b="elastic_outcrop",
    )

    assert result.summary.surface_pgd_ratio_b_over_a is not None
    assert result.summary.surface_pgd_ratio_b_over_a < 1.0


def test_compare_boundary_sensitivity_deepsoil_db_pair_reads_known_schema(tmp_path) -> None:
    time = np.arange(0, 2.56, 0.01, dtype=np.float64)
    input_acc_g = 0.22 * np.sin(2.0 * np.pi * 1.9 * time)
    rigid_surface_acc_g = 0.82 * np.sin(2.0 * np.pi * 1.65 * time - 0.04)
    elastic_surface_acc_g = 0.48 * np.sin(2.0 * np.pi * 1.88 * time - 0.03)
    rigid_disp = 0.007 * np.sin(2.0 * np.pi * 0.65 * time)
    elastic_disp = 0.0038 * np.sin(2.0 * np.pi * 0.72 * time)

    rigid_dir = tmp_path / "deepsoil-rigid"
    elastic_dir = tmp_path / "deepsoil-elastic"
    _write_synthetic_deepsoil_db_run(
        rigid_dir,
        halfspace="RIGID",
        input_acc_g=input_acc_g,
        surface_acc_g=rigid_surface_acc_g,
        surface_disp_m=rigid_disp,
        profile_scale=1.0,
    )
    _write_synthetic_deepsoil_db_run(
        elastic_dir,
        halfspace="ELASTIC",
        input_acc_g=input_acc_g,
        surface_acc_g=elastic_surface_acc_g,
        surface_disp_m=elastic_disp,
        profile_scale=0.62,
    )

    result = compare_boundary_sensitivity_deepsoil_db_pair(
        rigid_dir,
        elastic_dir,
        tmp_path / "deepsoil-compare",
    )

    assert result.artifacts.summary_json.exists()
    assert result.summary.surface_psa_peak_ratio_b_over_a is not None
    assert result.summary.surface_psa_peak_ratio_b_over_a < 1.0
    assert result.summary.surface_peak_period_shift_pct_b_vs_a is not None
    assert result.summary.surface_peak_period_shift_pct_b_vs_a < 0.0
    assert result.summary.surface_pga_ratio_b_over_a is not None
    assert result.summary.surface_pga_ratio_b_over_a < 1.0
    assert result.summary.surface_pgd_ratio_b_over_a is not None
    assert result.summary.surface_pgd_ratio_b_over_a < 1.0
    assert result.summary.surface_to_input_pga_amp_a is not None
    assert result.summary.surface_to_input_pga_amp_b is not None
    assert result.summary.surface_to_input_pga_amp_b < result.summary.surface_to_input_pga_amp_a
    assert result.summary.surface_to_input_peak_psa_amp_a is not None
    assert result.summary.surface_to_input_peak_psa_amp_b is not None
    assert result.summary.surface_to_input_peak_psa_amp_b < result.summary.surface_to_input_peak_psa_amp_a


def test_compare_boundary_delta_signatures_reports_directional_match(tmp_path) -> None:
    time = np.arange(0, 2.56, 0.01, dtype=np.float64)
    raw_input = 0.28 * 9.81 * np.sin(2.0 * np.pi * 1.9 * time)
    applied_rigid = raw_input
    applied_elastic = 0.5 * raw_input
    surface_rigid = 0.70 * 9.81 * np.sin(2.0 * np.pi * 1.65 * time - 0.05)
    surface_elastic = 0.44 * 9.81 * np.sin(2.0 * np.pi * 1.88 * time - 0.03)

    rigid_dir = tmp_path / "run-rigid-within"
    elastic_dir = tmp_path / "run-elastic-outcrop"
    _write_synthetic_run(
        rigid_dir,
        boundary_condition=BoundaryCondition.RIGID,
        motion_input_type="within",
        bottom_vs_m_s=500.0,
        bedrock_vs_m_s=None,
        raw_input=raw_input,
        applied_input=applied_rigid,
        surface_acc=surface_rigid,
        layer_scale=1.0,
    )
    _write_synthetic_run(
        elastic_dir,
        boundary_condition=BoundaryCondition.ELASTIC_HALFSPACE,
        motion_input_type="outcrop",
        bottom_vs_m_s=760.0,
        bedrock_vs_m_s=760.0,
        raw_input=raw_input,
        applied_input=applied_elastic,
        surface_acc=surface_elastic,
        layer_scale=0.65,
    )
    geo = compare_boundary_sensitivity_runs(
        rigid_dir,
        elastic_dir,
        tmp_path / "geo-compare",
        label_a="rigid_within",
        label_b="elastic_outcrop",
    )

    deepsoil_rigid = tmp_path / "deepsoil-rigid"
    deepsoil_elastic = tmp_path / "deepsoil-elastic"
    _write_synthetic_deepsoil_db_run(
        deepsoil_rigid,
        halfspace="RIGID",
        input_acc_g=raw_input / 9.81,
        surface_acc_g=surface_rigid / 9.81,
        surface_disp_m=0.007 * np.sin(2.0 * np.pi * 0.65 * time),
        profile_scale=1.0,
    )
    _write_synthetic_deepsoil_db_run(
        deepsoil_elastic,
        halfspace="ELASTIC",
        input_acc_g=raw_input / 9.81,
        surface_acc_g=surface_elastic / 9.81,
        surface_disp_m=0.0038 * np.sin(2.0 * np.pi * 0.72 * time),
        profile_scale=0.62,
    )
    deepsoil = compare_boundary_sensitivity_deepsoil_db_pair(
        deepsoil_rigid,
        deepsoil_elastic,
        tmp_path / "deepsoil-compare",
    )

    delta = compare_boundary_delta_signatures(
        deepsoil,
        geo,
        tmp_path / "delta-compare",
        reference_label="DeepSoil",
        candidate_label="GeoWave",
    )

    assert delta.artifacts.summary_json.exists()
    assert delta.summary.direction_match_peak_ratio is True
    assert delta.summary.direction_match_peak_period is True
    assert delta.summary.direction_match_surface_pga is True
    assert delta.summary.direction_match_surface_pgd is True
    assert delta.summary.directional_gate_passed is True
    assert delta.summary.mean_abs_rel_error is not None
    assert delta.summary.worst_metric_by_abs_rel_error is not None


def test_compare_case_truth_profile_and_tangent_audit_writes_rigid_case_report(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    time = np.arange(0, 2.56, 0.01, dtype=np.float64)
    raw_input = 0.28 * 9.81 * np.sin(2.0 * np.pi * 1.9 * time)
    applied_rigid = raw_input
    surface_rigid = 0.70 * 9.81 * np.sin(2.0 * np.pi * 1.65 * time - 0.05)
    rigid_dir = tmp_path / "run-rigid-within"
    _write_synthetic_run(
        rigid_dir,
        boundary_condition=BoundaryCondition.RIGID,
        motion_input_type="within",
        bottom_vs_m_s=500.0,
        bedrock_vs_m_s=None,
        raw_input=raw_input,
        applied_input=applied_rigid,
        surface_acc=surface_rigid,
        layer_scale=1.0,
    )

    deepsoil_rigid = tmp_path / "deepsoil-rigid"
    _write_synthetic_deepsoil_db_run(
        deepsoil_rigid,
        halfspace="RIGID",
        input_acc_g=(raw_input / 9.81),
        surface_acc_g=(0.78 * np.sin(2.0 * np.pi * 1.65 * time - 0.04)),
        surface_disp_m=(0.006 * np.sin(2.0 * np.pi * 0.65 * time)),
        profile_scale=1.0,
    )

    fake_sweep_dir = tmp_path / "fake-layer-sweep"
    fake_sweep_dir.mkdir(parents=True, exist_ok=True)
    fake_summary_json = fake_sweep_dir / "all_layers_tangent_audit_summary.json"
    fake_summary_csv = fake_sweep_dir / "layer_compliance_summary.csv"
    fake_summary_json.write_text("{}", encoding="utf-8")
    fake_summary_csv.write_text("profile_layer_index\n", encoding="utf-8")
    fake_layers = [
        LayerComplianceContribution(
            profile_layer_index=idx,
            profile_layer_name=f"Layer {idx + 1}",
            element_count=1,
            mean_compliance_fraction=0.10 + 0.02 * idx,
            max_compliance_fraction=0.12 + 0.02 * idx,
            mean_kt_kpa=1000.0 - 50.0 * idx,
            min_kt_kpa=900.0 - 45.0 * idx,
            max_kt_kpa=1100.0 - 55.0 * idx,
            gamma_abs_max=0.001 + 0.0001 * idx,
            tau_abs_max=40.0 + 2.0 * idx,
            gamma_m_global_max=0.0015 + 0.0001 * idx,
            f_mrdf_min=0.82,
            f_mrdf_max=0.97,
            g_ref_min_kpa=600.0 - 20.0 * idx,
            g_ref_max_kpa=800.0 - 20.0 * idx,
            g_t_ref_min_kpa=500.0 - 15.0 * idx,
            g_t_ref_max_kpa=780.0 - 15.0 * idx,
            reason_counts={"1": 4},
            branch_kind_counts={"translated_local_bridge": 4},
        )
        for idx in range(5)
    ]
    fake_sweep = LayerSweepAuditResult(
        config_path=rigid_dir / "config_snapshot.json",
        motion_csv=fake_sweep_dir / "audit_motion.csv",
        mrdf_reference_mode_code=0.0,
        artifacts=LayerSweepAuditArtifacts(
            output_dir=fake_sweep_dir,
            audit_csv=fake_sweep_dir / "all_layers_tangent_audit.csv",
            summary_json=fake_summary_json,
            layer_summary_csv=fake_summary_csv,
            motion_csv=fake_sweep_dir / "audit_motion.csv",
        ),
        summary=LayerSweepAuditSummary(
            row_count=20,
            state_count=4,
            equivalent_stiffness_min=123.0,
            equivalent_stiffness_max=456.0,
            dominant_layer_by_mean_compliance=4,
            dominant_layer_mean_compliance=0.18,
            layers=fake_layers,
        ),
    )

    monkeypatch.setattr(
        constitutive_debug_module,
        "run_solver_layer_sweep_audit",
        lambda *args, **kwargs: fake_sweep,
    )

    result = compare_case_truth_profile_and_tangent_audit(
        rigid_dir,
        deepsoil_rigid,
        tmp_path / "case_truth_compare",
        label="rigid_within_case_truth",
    )

    assert result.artifacts.summary_json.exists()
    assert result.artifacts.summary_md.exists()
    assert result.artifacts.layer_csv.exists()
    assert result.artifacts.motion_csv.exists()
    assert result.summary.layer_count == 5
    assert result.summary.gamma_max_mean_ratio_geo_over_ref is not None
    assert result.summary.max_stress_ratio_mean_ratio_geo_over_ref is not None
    assert result.summary.stress_proxy_mean_ratio_geo_over_ref is not None
    assert result.summary.secant_proxy_mean_ratio_geo_over_ref is not None
    assert result.summary.tau_peak_proxy_mean_ratio_geo_over_ref is not None
    assert result.summary.mean_kt_ratio_geo_over_ref_secant_mean is not None
    assert result.summary.min_kt_ratio_geo_over_ref_secant_mean is not None
    assert result.summary.worst_layer_by_mean_kt_ratio_geo_over_ref_secant is not None
    assert result.summary.worst_layer_mean_kt_ratio_geo_over_ref_secant is not None
    assert result.summary.dominant_layer_by_mean_compliance == 4
    assert result.summary.layers[0].mean_kt_kpa == pytest.approx(1000.0)
    assert result.summary.layers[0].reason_counts["1"] == 4
    assert result.summary.layers[0].geowave_stress_proxy_kpa is not None
    assert result.summary.layers[0].deepsoil_stress_proxy_kpa is not None
    assert result.summary.layers[0].stress_proxy_ratio_geo_over_ref is not None
    assert result.summary.layers[0].geowave_secant_proxy_kpa is not None
    assert result.summary.layers[0].deepsoil_secant_proxy_kpa is not None
    assert result.summary.layers[0].secant_proxy_ratio_geo_over_ref is not None
    assert result.summary.layers[0].tau_peak_proxy_ratio_geo_over_ref is not None
    assert result.summary.layers[0].mean_kt_ratio_geo_over_ref_secant is not None
    assert result.summary.layers[0].min_kt_ratio_geo_over_ref_secant is not None
    with result.artifacts.summary_md.open("r", encoding="utf-8") as fh:
        markdown = fh.read()
    assert "Case Truth Compare" in markdown
    assert "Layer Sweep" in markdown
    assert "stress proxy" in markdown
    assert "secant proxy" in markdown
    assert "mean kt / ref secant" in markdown
    with result.artifacts.layer_csv.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        first_row = next(reader)
    assert "max_stress_ratio_geo_over_ref" in first_row
    assert "stress_proxy_ratio_geo_over_ref" in first_row
    assert "secant_proxy_ratio_geo_over_ref" in first_row
    assert "tau_peak_proxy_ratio_geo_over_ref" in first_row
    assert "mean_kt_ratio_geo_over_ref_secant" in first_row
    assert "min_kt_ratio_geo_over_ref_secant" in first_row


def test_compare_case_truth_profile_and_tangent_audit_aligns_one_based_sweep_layers(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    time = np.arange(0, 2.56, 0.01, dtype=np.float64)
    raw_input = 0.28 * 9.81 * np.sin(2.0 * np.pi * 1.9 * time)
    applied_rigid = raw_input
    surface_rigid = 0.70 * 9.81 * np.sin(2.0 * np.pi * 1.65 * time - 0.05)
    rigid_dir = tmp_path / "run-rigid-within"
    _write_synthetic_run(
        rigid_dir,
        boundary_condition=BoundaryCondition.RIGID,
        motion_input_type="within",
        bottom_vs_m_s=500.0,
        bedrock_vs_m_s=None,
        raw_input=raw_input,
        applied_input=applied_rigid,
        surface_acc=surface_rigid,
        layer_scale=1.0,
    )

    deepsoil_rigid = tmp_path / "deepsoil_rigid"
    _write_synthetic_deepsoil_db_run(
        deepsoil_rigid,
        halfspace="rigid",
        input_acc_g=applied_rigid / 9.81,
        surface_acc_g=surface_rigid / 9.81,
        surface_disp_m=0.006 * np.sin(2.0 * np.pi * 0.7 * time),
        profile_scale=1.0,
    )

    fake_sweep_dir = tmp_path / "fake_sweep_one_based"
    fake_summary_json = fake_sweep_dir / "all_layers_tangent_audit_summary.json"
    fake_summary_csv = fake_sweep_dir / "layer_compliance_summary.csv"
    fake_summary_json.parent.mkdir(parents=True, exist_ok=True)
    fake_summary_json.write_text("{}", encoding="utf-8")
    fake_summary_csv.write_text("profile_layer_index\n", encoding="utf-8")
    fake_layers = [
        LayerComplianceContribution(
            profile_layer_index=idx + 1,
            profile_layer_name=f"Layer {idx + 1}",
            element_count=1,
            mean_compliance_fraction=0.10 + 0.02 * idx,
            max_compliance_fraction=0.12 + 0.02 * idx,
            mean_kt_kpa=1000.0 - 50.0 * idx,
            min_kt_kpa=900.0 - 45.0 * idx,
            max_kt_kpa=1100.0 - 55.0 * idx,
            gamma_abs_max=0.001 + 0.0001 * idx,
            tau_abs_max=40.0 + 2.0 * idx,
            gamma_m_global_max=0.0015 + 0.0001 * idx,
            f_mrdf_min=0.82,
            f_mrdf_max=0.97,
            g_ref_min_kpa=600.0 - 20.0 * idx,
            g_ref_max_kpa=800.0 - 20.0 * idx,
            g_t_ref_min_kpa=500.0 - 15.0 * idx,
            g_t_ref_max_kpa=780.0 - 15.0 * idx,
            reason_counts={"1": 4},
            branch_kind_counts={"translated_local_bridge": 4},
        )
        for idx in range(5)
    ]
    fake_sweep = LayerSweepAuditResult(
        config_path=rigid_dir / "config_snapshot.json",
        motion_csv=rigid_dir / "input_motion.csv",
        mrdf_reference_mode_code=0.0,
        artifacts=LayerSweepAuditArtifacts(
            output_dir=fake_sweep_dir,
            audit_csv=fake_sweep_dir / "all_layers_tangent_audit.csv",
            summary_json=fake_summary_json,
            layer_summary_csv=fake_summary_csv,
            motion_csv=fake_sweep_dir / "audit_motion.csv",
        ),
        summary=LayerSweepAuditSummary(
            row_count=20,
            state_count=4,
            equivalent_stiffness_min=123.0,
            equivalent_stiffness_max=456.0,
            dominant_layer_by_mean_compliance=5,
            dominant_layer_mean_compliance=0.18,
            layers=fake_layers,
        ),
    )

    monkeypatch.setattr(
        constitutive_debug_module,
        "run_solver_layer_sweep_audit",
        lambda *args, **kwargs: fake_sweep,
    )

    result = compare_case_truth_profile_and_tangent_audit(
        rigid_dir,
        deepsoil_rigid,
        tmp_path / "case_truth_compare_one_based",
        label="rigid_within_case_truth",
    )

    assert result.summary.layers[0].mean_kt_kpa == pytest.approx(1000.0)
    assert result.summary.layers[0].tau_peak_proxy_ratio_geo_over_ref is not None
