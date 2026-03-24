from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import h5py
import numpy as np
import pytest
from dsra1d.deepsoil_compare import compare_deepsoil_manifest, compare_deepsoil_run
from dsra1d.post import compute_spectra


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
