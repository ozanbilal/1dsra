import numpy as np
from dsra1d.config import MaterialType
from dsra1d.materials import (
    bounded_damping_from_reduction,
    generate_masing_loop,
    gqh_backbone_stress,
    gqh_backbone_stress_from_params,
    gqh_modulus_reduction,
    gqh_modulus_reduction_from_params,
    layer_hysteretic_proxy,
    mkz_backbone_stress,
    mkz_modulus_reduction,
)


def test_mkz_modulus_reduction_half_at_gamma_ref() -> None:
    red = mkz_modulus_reduction(np.array([0.001], dtype=np.float64), gamma_ref=0.001)
    assert red.shape == (1,)
    assert np.isclose(red[0], 0.5, atol=1.0e-12)


def test_mkz_backbone_applies_tau_cap() -> None:
    strain = np.array([0.005], dtype=np.float64)
    tau = mkz_backbone_stress(strain, gmax=70000.0, gamma_ref=0.001, tau_max=40.0)
    assert tau.shape == (1,)
    assert np.isclose(tau[0], 40.0, atol=1.0e-12)


def test_gqh_modulus_reduction_monotonic_with_strain() -> None:
    strain = np.array([1.0e-5, 1.0e-4, 1.0e-3], dtype=np.float64)
    red = gqh_modulus_reduction(strain, gamma_ref=0.001, a1=1.0, a2=0.4, m=2.0)
    assert red[0] > red[1] > red[2]


def test_gqh_backbone_returns_finite_values() -> None:
    strain = np.array([0.0, 1.0e-4, 1.0e-3], dtype=np.float64)
    tau = gqh_backbone_stress(
        strain,
        gmax=65000.0,
        gamma_ref=0.001,
        a1=1.1,
        a2=0.3,
        m=2.0,
    )
    assert np.all(np.isfinite(tau))
    assert tau.shape == strain.shape


def test_bounded_damping_from_reduction_limits_range() -> None:
    red = np.array([1.2, 0.7, -0.2], dtype=np.float64)
    damping = bounded_damping_from_reduction(red, damping_min=0.01, damping_max=0.10)
    assert np.all(damping >= 0.01)
    assert np.all(damping <= 0.10)


def test_layer_hysteretic_proxy_for_mkz_is_bounded() -> None:
    proxy = layer_hysteretic_proxy(
        material=MaterialType.MKZ,
        material_params={"gamma_ref": 0.001, "damping_min": 0.01, "damping_max": 0.12},
        strain_proxy=0.001,
    )
    assert 0.0 <= proxy.reduction <= 1.0
    assert 0.0 <= proxy.damping <= 0.5
    assert 0.0 <= proxy.ru_target <= 1.0


def test_generate_masing_loop_mkz_has_positive_dissipation() -> None:
    loop = generate_masing_loop(
        material=MaterialType.MKZ,
        material_params={"gmax": 65000.0, "gamma_ref": 0.0012},
        strain_amplitude=0.0025,
        n_points_per_branch=100,
    )
    assert loop.strain.shape == loop.stress.shape
    assert loop.strain.size == (3 * 100) - 2
    assert np.isclose(loop.strain[0], 0.0, atol=1.0e-12)
    assert np.isclose(loop.strain[-1], 0.0025, atol=1.0e-12)
    assert np.all(np.isfinite(loop.stress))
    assert loop.energy_dissipation > 0.0


def test_generate_masing_loop_gqh_has_positive_dissipation() -> None:
    loop = generate_masing_loop(
        material=MaterialType.GQH,
        material_params={
            "gmax": 70000.0,
            "gamma_ref": 0.001,
            "a1": 1.1,
            "a2": 0.3,
            "m": 2.0,
        },
        strain_amplitude=0.002,
    )
    assert loop.strain.shape == loop.stress.shape
    assert np.all(np.isfinite(loop.strain))
    assert np.all(np.isfinite(loop.stress))
    assert loop.energy_dissipation > 0.0


def test_generate_masing_loop_rejects_non_hysteretic_material() -> None:
    with np.testing.assert_raises(ValueError):
        generate_masing_loop(
            material=MaterialType.PM4SAND,
            material_params={},
            strain_amplitude=0.001,
        )


def test_gqh_strength_controlled_reduction_decreases_with_strain() -> None:
    strain = np.array([1.0e-5, 1.0e-4, 1.0e-3], dtype=np.float64)
    params = {
        "gmax": 95000.0,
        "tau_max": 420.0,
        "theta1": -2.88,
        "theta2": -2.80,
        "theta3": 0.2291,
        "theta4": 0.99,
        "theta5": 1.0,
    }
    red = gqh_modulus_reduction_from_params(strain, params)
    assert red[0] > red[1] > red[2]


def test_gqh_strength_controlled_backbone_is_bounded_by_tau_max() -> None:
    strain = np.logspace(-5, -1, 20, dtype=np.float64)
    params = {
        "gmax": 95000.0,
        "tau_max": 420.0,
        "theta1": -2.88,
        "theta2": -2.80,
        "theta3": 0.2291,
        "theta4": 0.99,
        "theta5": 1.0,
    }
    tau = gqh_backbone_stress_from_params(strain, params)
    assert np.all(np.isfinite(tau))
    assert np.max(tau) <= params["tau_max"] * 1.001
