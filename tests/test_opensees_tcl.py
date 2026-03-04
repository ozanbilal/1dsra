from pathlib import Path

import pytest
from dsra1d.config import load_project_config
from dsra1d.config.models import BoundaryCondition
from dsra1d.interop.opensees import (
    build_element_slices,
    build_layer_slices,
    render_tcl,
    validate_tcl_script,
)


def test_build_layer_slices_depth_consistency() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    slices = build_layer_slices(cfg)

    total_depth = sum(layer.thickness_m for layer in cfg.profile.layers)
    assert len(slices) == len(cfg.profile.layers)
    assert slices[-1].z_bot_m == pytest.approx(total_depth)
    assert all(layer.n_sublayers >= 1 for layer in slices)


def test_render_tcl_contains_expected_blocks() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    script = render_tcl(
        cfg,
        motion_file=Path("examples/motions/sample_motion.csv"),
        output_dir=Path("out/test"),
    )

    assert "model BasicBuilder -ndm 2 -ndf 3" in script
    assert "nDMaterial PM4Sand" in script
    assert "nDMaterial PM4Silt" in script
    assert "element quadUP" in script
    assert "pattern UniformExcitation" in script
    assert "surface_acc.out" in script
    assert "pwp_ru.out" in script
    assert "-dof 3 disp" in script
    validate_tcl_script(script)


def test_render_tcl_boundary_rigid() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.boundary_condition = BoundaryCondition.RIGID
    script = render_tcl(
        cfg,
        motion_file=Path("examples/motions/sample_motion.csv"),
        output_dir=Path("out/test"),
    )
    assert "Base boundary: rigid" in script
    assert "fix $nodeL($nNodeY) 1 1 1" in script
    assert "uniaxialMaterial Viscous 9001" not in script


def test_render_tcl_boundary_elastic_halfspace_dashpot() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.boundary_condition = BoundaryCondition.ELASTIC_HALFSPACE
    script = render_tcl(
        cfg,
        motion_file=Path("examples/motions/sample_motion.csv"),
        output_dir=Path("out/test"),
    )
    assert "Base boundary: elastic half-space" in script
    assert "uniaxialMaterial Viscous 9001" in script
    assert "element zeroLength 9001" in script


def test_render_tcl_uses_opensees_u_p_parameters_from_config() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.opensees.column_width_m = 2.5
    cfg.opensees.thickness_m = 1.3
    cfg.opensees.fluid_bulk_modulus = 3.1e6
    cfg.opensees.fluid_mass_density = 1.2
    cfg.opensees.h_perm = 2.0e-5
    cfg.opensees.v_perm = 4.0e-5
    cfg.opensees.gravity_steps = 33
    script = render_tcl(
        cfg,
        motion_file=Path("examples/motions/sample_motion.csv"),
        output_dir=Path("out/test"),
    )
    assert "set colWidth 2.50000000" in script
    assert "set thickness 1.30000000" in script
    assert "set fBulk 3100000.00000000" in script
    assert "set fMass 1.20000000" in script
    assert "set hPerm 0.00002000" in script
    assert "set vPerm 0.00004000" in script
    assert "set okG [analyze 33 $dt]" in script


def test_render_tcl_appends_pm4_optional_material_args() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    cfg.profile.layers[0].material_optional_args = [101.0, 0.7, 250.0]
    script = render_tcl(
        cfg,
        motion_file=Path("examples/motions/sample_motion.csv"),
        output_dir=Path("out/test"),
    )
    assert "nDMaterial PM4Sand 1 0.420000 620.000000 0.550000" in script
    assert "101 0.7 250" in script


def test_build_element_slices_total_matches_subdivisions() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    layer_slices = build_layer_slices(cfg)
    elements = build_element_slices(layer_slices)
    expected = sum(layer.n_sublayers for layer in layer_slices)
    assert len(elements) == expected


def test_validate_tcl_script_rejects_unbalanced_braces() -> None:
    with pytest.raises(ValueError):
        validate_tcl_script("set x {1\n")
