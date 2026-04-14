from pathlib import Path

import numpy as np
import pytest
from dsra1d.config import BoundaryCondition, load_project_config
from dsra1d.interop.opensees import build_element_slices, build_layer_slices
from dsra1d.linear import solve_equivalent_linear_sh_response, solve_linear_sh_response
from dsra1d.materials.damping import layer_damping, modal_matched_damping_matrix
from dsra1d.motion import load_motion
from dsra1d.pipeline import load_result, run_analysis
from dsra1d.verify import verify_run
from dsra1d.linear import _solver_column_area


def test_linear_solver_returns_finite_response() -> None:
    cfg = load_project_config(Path("examples/native/linear_3layer_sand.yml"))
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    time, surface = solve_linear_sh_response(cfg, motion)
    assert time.shape == surface.shape
    assert surface.size == motion.acc.size
    assert np.all(np.isfinite(surface))
    assert float(np.std(surface)) > 0.0


def test_run_analysis_linear_backend_writes_verifiable_outputs(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/native/linear_3layer_sand.yml"))
    cfg.analysis.solver_backend = "linear"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    result = run_analysis(cfg, motion, output_dir=tmp_path)
    assert result.status == "ok"
    report = verify_run(result.output_dir)
    assert report.ok is True


def test_eql_solver_returns_finite_response_and_iterations() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "eql"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    eql = solve_equivalent_linear_sh_response(cfg, motion)
    assert eql.iterations >= 1
    assert isinstance(eql.converged, bool)
    assert len(eql.max_change_history) == eql.iterations
    assert eql.response.time.shape == eql.response.surface_acc.shape
    assert eql.response.surface_acc.size == motion.acc.size
    assert np.all(np.isfinite(eql.response.surface_acc))
    assert float(np.std(eql.response.surface_acc)) > 0.0


def test_linear_solver_rayleigh_mode_changes_response() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "linear"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    _, surface_default = solve_linear_sh_response(cfg, motion)

    cfg_rayleigh = cfg.model_copy(deep=True)
    cfg_rayleigh.analysis.damping_mode = "rayleigh"
    cfg_rayleigh.analysis.rayleigh_mode_1_hz = 0.8
    cfg_rayleigh.analysis.rayleigh_mode_2_hz = 12.0
    _, surface_rayleigh = solve_linear_sh_response(cfg_rayleigh, motion)

    assert surface_default.shape == surface_rayleigh.shape
    assert np.all(np.isfinite(surface_rayleigh))
    assert not np.allclose(surface_default, surface_rayleigh)


def test_linear_solver_elastic_halfspace_changes_response() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "linear"
    cfg.boundary_condition = BoundaryCondition.RIGID
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    _, surface_rigid = solve_linear_sh_response(cfg, motion)

    cfg_halfspace = cfg.model_copy(deep=True)
    cfg_halfspace.boundary_condition = BoundaryCondition.ELASTIC_HALFSPACE
    _, surface_halfspace = solve_linear_sh_response(cfg_halfspace, motion)

    assert surface_rigid.shape == surface_halfspace.shape
    assert np.all(np.isfinite(surface_halfspace))
    assert not np.allclose(surface_rigid, surface_halfspace)


def test_modal_matched_damping_matrix_targets_first_modes() -> None:
    cfg = load_project_config(Path("examples/native/deepsoil_gqh_5layer_baseline.yml"))
    layer_slices = build_layer_slices(cfg, points_per_wavelength=10.0, min_dz_m=0.25)
    element_slices = build_element_slices(layer_slices)
    layer_by_idx = {layer.index: layer for layer in layer_slices}
    area = _solver_column_area(cfg)

    n_elem = len(element_slices)
    n_nodes = n_elem + 1
    n_free = n_nodes - 1
    m_elem = np.zeros(n_elem, dtype=np.float64)
    k_elem = np.zeros(n_elem, dtype=np.float64)
    xi_elem = np.zeros(n_elem, dtype=np.float64)

    for j, elem in enumerate(element_slices):
        layer_slice = layer_by_idx[elem.layer_index]
        layer = cfg.profile.layers[layer_slice.index - 1]
        rho = float(max(layer.unit_weight_kn_m3 / 9.81, 1.0e-6))
        vs = float(max(layer.vs_m_s, 1.0e-6))
        dz = float(max(elem.dz_m, 1.0e-6))
        g_mod = rho * vs * vs
        m_elem[j] = rho * area * dz
        k_elem[j] = g_mod * area / dz
        xi_elem[j] = layer_damping(layer.material, layer.material_params)

    m_diag_full = np.zeros(n_nodes, dtype=np.float64)
    m_diag_full[0] += 0.5 * m_elem[0]
    m_diag_full[-1] += 0.5 * m_elem[-1]
    for j in range(n_elem - 1):
        m_diag_full[j + 1] += 0.5 * (m_elem[j] + m_elem[j + 1])
    m_diag = m_diag_full[:n_free]

    k_mat = np.zeros((n_nodes, n_nodes), dtype=np.float64)
    for j, k_val in enumerate(k_elem):
        k_mat[j, j] += k_val
        k_mat[j, j + 1] -= k_val
        k_mat[j + 1, j] -= k_val
        k_mat[j + 1, j + 1] += k_val
    k_mat = k_mat[:n_free, :n_free]

    xi_target = float(np.average(xi_elem, weights=np.maximum(m_elem, 1.0e-12)))
    c_mat = modal_matched_damping_matrix(m_diag, k_mat, xi_target)

    inv_sqrt_m = 1.0 / np.sqrt(np.maximum(m_diag, 1.0e-12))
    dyn = (inv_sqrt_m[:, None] * k_mat) * inv_sqrt_m[None, :]
    eigvals, eigvecs = np.linalg.eigh(0.5 * (dyn + dyn.T))
    pos = np.where(eigvals > 1.0e-12)[0]
    phi = inv_sqrt_m[:, None] * eigvecs[:, pos]
    m_mat = np.diag(m_diag)

    for mode_idx in range(2):
        mode = phi[:, mode_idx]
        modal_mass = float(mode.T @ m_mat @ mode)
        modal_stiffness = float(mode.T @ k_mat @ mode)
        modal_damping = float(mode.T @ c_mat @ mode)
        xi_mode = modal_damping / (2.0 * np.sqrt(modal_stiffness * modal_mass))
        assert np.isfinite(xi_mode)
        assert xi_mode == pytest.approx(xi_target, rel=0.15)


def test_linear_solver_halves_rigid_outcrop_motion() -> None:
    cfg = load_project_config(Path("examples/native/linear_3layer_sand.yml"))
    cfg.boundary_condition = BoundaryCondition.RIGID
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)

    cfg_within = cfg.model_copy(deep=True)
    cfg_within.motion.input_type = "within"
    _, surface_within = solve_linear_sh_response(cfg_within, motion)

    cfg_outcrop = cfg.model_copy(deep=True)
    cfg_outcrop.motion.input_type = "outcrop"
    _, surface_outcrop = solve_linear_sh_response(cfg_outcrop, motion)

    ratio = float(np.max(np.abs(surface_outcrop)) / max(np.max(np.abs(surface_within)), 1.0e-12))
    assert ratio == pytest.approx(0.5, rel=0.02)


def test_run_analysis_eql_backend_writes_summary_artifact(tmp_path: Path) -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_mock.yml"))
    cfg.analysis.solver_backend = "eql"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    result = run_analysis(cfg, motion, output_dir=tmp_path)
    assert result.status == "ok"
    assert (result.output_dir / "eql_summary.json").exists()
    store = load_result(result.output_dir)
    assert store.eql_iterations is not None
    assert store.eql_iterations >= 1
    assert store.eql_converged is not None
    assert store.eql_layer_idx.size >= 1
    assert store.eql_layer_vs_m_s.size == store.eql_layer_idx.size


def test_eql_solver_accepts_darendeli_calibrated_config() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_darendeli.yml"))
    cfg.analysis.solver_backend = "eql"
    dt = cfg.analysis.dt or (1.0 / (20.0 * cfg.analysis.f_max))
    motion = load_motion(Path("examples/motions/sample_motion.csv"), dt=dt, unit=cfg.motion.units)
    eql = solve_equivalent_linear_sh_response(cfg, motion)
    assert eql.response.time.shape == eql.response.surface_acc.shape
    assert np.all(np.isfinite(eql.response.surface_acc))
    assert eql.iterations >= 1
