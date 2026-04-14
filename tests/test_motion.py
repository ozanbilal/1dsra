from pathlib import Path

import numpy as np
from dsra1d.config.models import BaselineMode, MotionConfig, ScaleMode
from dsra1d.motion import import_peer_at2_to_csv, load_motion, load_motion_series
from dsra1d.motion.processing import preprocess_motion
from dsra1d.types import Motion
from dsra1d.units import STD_GRAVITY_M_S2


def test_preprocess_scale_by() -> None:
    mot = Motion(dt=0.01, acc=np.array([1.0, -1.0, 0.0], dtype=np.float64))
    cfg = MotionConfig(scale_mode=ScaleMode.SCALE_BY, scale_factor=2.0)
    out = preprocess_motion(mot, cfg)
    assert np.max(np.abs(out.acc)) == 2.0


def test_preprocess_scale_to_pga() -> None:
    mot = Motion(dt=0.01, acc=np.array([0.5, -0.5, 0.0], dtype=np.float64))
    cfg = MotionConfig(scale_mode=ScaleMode.SCALE_TO_PGA, target_pga=1.0)
    out = preprocess_motion(mot, cfg)
    assert np.isclose(np.max(np.abs(out.acc)), 1.0)


def test_load_motion_unit_conversion_from_g(tmp_path: Path) -> None:
    motion_file = tmp_path / "motion_g.csv"
    motion_file.write_text("0.1\n-0.2\n0.0\n", encoding="utf-8")
    mot = load_motion(motion_file, dt=0.01, unit="g")
    assert mot.unit == "m/s2"
    assert np.isclose(mot.acc[0], 0.1 * STD_GRAVITY_M_S2)
    assert np.isclose(mot.acc[1], -0.2 * STD_GRAVITY_M_S2)


def test_load_motion_with_csv_header_row(tmp_path: Path) -> None:
    motion_file = tmp_path / "motion_with_header.csv"
    motion_file.write_text(
        "time_s,acc_m_s2\n0.00,0.10\n0.01,-0.20\n0.02,0.00\n",
        encoding="utf-8",
    )
    mot = load_motion(motion_file, dt=0.01, unit="m/s2")
    assert mot.acc.shape == (3,)
    assert np.isclose(mot.acc[0], 0.10)
    assert np.isclose(mot.acc[1], -0.20)


def test_load_motion_series_with_csv_header_row(tmp_path: Path) -> None:
    motion_file = tmp_path / "motion_with_header.csv"
    motion_file.write_text(
        "time_s,acc_m_s2\n0.00,0.10\n0.01,-0.20\n0.02,0.00\n",
        encoding="utf-8",
    )
    time, acc = load_motion_series(motion_file, fallback_dt=0.02)
    assert time.shape == (3,)
    assert acc.shape == (3,)
    assert np.isclose(time[1] - time[0], 0.01)
    assert np.isclose(acc[1], -0.20)


def test_load_motion_prefers_time_column_dt_over_passed_dt(tmp_path: Path) -> None:
    motion_file = tmp_path / "motion_time_acc.csv"
    motion_file.write_text(
        "time_s,acc_m_s2\n0.000,0.10\n0.005,-0.20\n0.010,0.00\n",
        encoding="utf-8",
    )
    mot = load_motion(motion_file, dt=0.002, unit="m/s2")
    assert np.isclose(mot.dt, 0.005)
    assert mot.acc.shape == (3,)


def test_scale_to_pga_respects_config_units(tmp_path: Path) -> None:
    motion_file = tmp_path / "motion_g.csv"
    motion_file.write_text("0.2\n-0.2\n0.0\n", encoding="utf-8")
    mot = load_motion(motion_file, dt=0.01, unit="g")
    cfg = MotionConfig(
        units="g",
        scale_mode=ScaleMode.SCALE_TO_PGA,
        target_pga=0.5,
    )
    out = preprocess_motion(mot, cfg)
    assert np.isclose(np.max(np.abs(out.acc)), 0.5 * STD_GRAVITY_M_S2)


def test_preprocess_deepsoil_bap_like_baseline() -> None:
    acc = np.array([0.0, 0.02, -0.01, 0.03, -0.02, 0.01, -0.005, 0.0], dtype=np.float64)
    mot = Motion(dt=0.01, acc=acc)
    cfg = MotionConfig(baseline=BaselineMode.DEEPSOIL_BAP_LIKE, scale_mode=ScaleMode.NONE)
    out = preprocess_motion(mot, cfg)
    assert out.acc.size > 0
    assert np.isfinite(out.acc).all()


def test_import_peer_at2_to_csv(tmp_path: Path) -> None:
    at2 = tmp_path / "sample.at2"
    at2.write_text(
        "AT2 EXAMPLE\nNPTS= 4, DT=0.02 SEC\n0.10 -0.10 0.00 0.05\n",
        encoding="utf-8",
    )
    res = import_peer_at2_to_csv(
        at2,
        output_dir=tmp_path,
        units_hint="g",
        output_name="converted.csv",
    )
    assert res.csv_path.exists()
    assert res.npts == 4
    assert np.isclose(res.dt_s, 0.02)
    assert res.pga_si > 0.0
