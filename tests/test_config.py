from pathlib import Path

import pytest
from dsra1d.config import load_project_config


def test_load_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    assert cfg.project_name == "sample-effective-stress"
    assert cfg.analysis.dt is not None
    assert cfg.analysis.dt > 0.0


def test_load_strict_plus_example_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress_strict_plus.yml"))
    assert cfg.project_name == "sample-effective-stress-strict-plus"
    assert cfg.analysis.pm4_validation_profile == "strict_plus"


def test_invalid_extension() -> None:
    with pytest.raises(ValueError):
        load_project_config(Path("examples/configs/effective_stress.txt"))


def test_invalid_pm4sand_param_range(tmp_path: Path) -> None:
    cfg = tmp_path / "bad_pm4sand.yml"
    cfg.write_text(
        """
project_name: bad-pm4
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 1.4
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_unknown_material_param_key(tmp_path: Path) -> None:
    cfg = tmp_path / "bad_key.yml"
    cfg.write_text(
        """
project_name: bad-key
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4silt
      material_params:
        unknown_k: 3.0
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_opensees_requires_pm4_parameters(tmp_path: Path) -> None:
    cfg = tmp_path / "missing_pm4.yml"
    cfg.write_text(
        """
project_name: missing-pm4
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
analysis:
  solver_backend: opensees
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_mock_backend_allows_missing_pm4_parameters(tmp_path: Path) -> None:
    cfg = tmp_path / "missing_pm4_mock.yml"
    cfg.write_text(
        """
project_name: missing-pm4-mock
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    loaded = load_project_config(cfg)
    assert loaded.analysis.solver_backend == "mock"


def test_invalid_motion_unit_rejected(tmp_path: Path) -> None:
    cfg = tmp_path / "bad_unit.yml"
    cfg.write_text(
        """
project_name: bad-unit
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: elastic
motion:
  units: foo
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_pm4_strict_profile_accepts_valid_ranges(tmp_path: Path) -> None:
    cfg = tmp_path / "strict_ok.yml"
    cfg.write_text(
        """
project_name: strict-ok
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
analysis:
  solver_backend: opensees
  pm4_validation_profile: strict
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    loaded = load_project_config(cfg)
    assert loaded.analysis.pm4_validation_profile == "strict"


def test_pm4_strict_profile_rejects_out_of_range(tmp_path: Path) -> None:
    cfg = tmp_path / "strict_bad.yml"
    cfg.write_text(
        """
project_name: strict-bad
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 50000.0
        hpo: 0.53
analysis:
  solver_backend: opensees
  pm4_validation_profile: strict
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_pm4_strict_plus_profile_accepts_valid_config(tmp_path: Path) -> None:
    cfg = tmp_path / "strict_plus_ok.yml"
    cfg.write_text(
        """
project_name: strict-plus-ok
profile:
  layers:
    - name: L1
      thickness_m: 6.0
      unit_weight_kN_m3: 18.5
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
    - name: L2
      thickness_m: 8.0
      unit_weight_kN_m3: 19.0
      vs_m_s: 240.0
      material: pm4silt
      material_params:
        Su: 35.0
        Su_Rat: 0.25
        G_o: 500.0
        h_po: 0.60
boundary_condition: elastic_halfspace
analysis:
  solver_backend: opensees
  pm4_validation_profile: strict_plus
opensees:
  executable: OpenSees
  h_perm: 1.0e-5
  v_perm: 1.0e-5
  gravity_steps: 20
""".strip(),
        encoding="utf-8",
    )
    loaded = load_project_config(cfg)
    assert loaded.analysis.pm4_validation_profile == "strict_plus"


def test_pm4_strict_plus_rejects_rigid_boundary(tmp_path: Path) -> None:
    cfg = tmp_path / "strict_plus_rigid.yml"
    cfg.write_text(
        """
project_name: strict-plus-rigid
profile:
  layers:
    - name: L1
      thickness_m: 6.0
      unit_weight_kN_m3: 18.5
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
boundary_condition: rigid
analysis:
  solver_backend: opensees
  pm4_validation_profile: strict_plus
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_pm4_strict_plus_rejects_invalid_permeability(tmp_path: Path) -> None:
    cfg = tmp_path / "strict_plus_perm.yml"
    cfg.write_text(
        """
project_name: strict-plus-perm
profile:
  layers:
    - name: L1
      thickness_m: 6.0
      unit_weight_kN_m3: 18.5
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
boundary_condition: elastic_halfspace
analysis:
  solver_backend: opensees
  pm4_validation_profile: strict_plus
opensees:
  executable: OpenSees
  h_perm: 5.0e-1
  v_perm: 1.0e-5
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_pm4_strict_plus_rejects_extreme_permeability_ratio(tmp_path: Path) -> None:
    cfg = tmp_path / "strict_plus_perm_ratio.yml"
    cfg.write_text(
        """
project_name: strict-plus-perm-ratio
profile:
  layers:
    - name: L1
      thickness_m: 6.0
      unit_weight_kN_m3: 18.5
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
boundary_condition: elastic_halfspace
analysis:
  solver_backend: opensees
  pm4_validation_profile: strict_plus
opensees:
  executable: OpenSees
  h_perm: 1.0e-2
  v_perm: 1.0e-8
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_pm4_strict_plus_rejects_non_pm4_layer(tmp_path: Path) -> None:
    cfg = tmp_path / "strict_plus_non_pm4.yml"
    cfg.write_text(
        """
project_name: strict-plus-non-pm4
profile:
  layers:
    - name: L1
      thickness_m: 6.0
      unit_weight_kN_m3: 18.5
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
    - name: L2
      thickness_m: 6.0
      unit_weight_kN_m3: 19.0
      vs_m_s: 260.0
      material: elastic
boundary_condition: elastic_halfspace
analysis:
  solver_backend: opensees
  pm4_validation_profile: strict_plus
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_opensees_u_p_parameters_must_be_positive(tmp_path: Path) -> None:
    cfg = tmp_path / "bad_up_params.yml"
    cfg.write_text(
        """
project_name: bad-up-params
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
analysis:
  solver_backend: opensees
opensees:
  executable: OpenSees
  h_perm: -1.0e-5
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_non_finite_material_optional_args_rejected(tmp_path: Path) -> None:
    cfg = tmp_path / "bad_optional_args.yml"
    cfg.write_text(
        """
project_name: bad-optional-args
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
        G0: 600.0
        hpo: 0.53
      material_optional_args: [1.0, .nan]
analysis:
  solver_backend: opensees
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_mkz_mock_backend_accepts_required_params(tmp_path: Path) -> None:
    cfg = tmp_path / "mkz_mock.yml"
    cfg.write_text(
        """
project_name: mkz-mock
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: mkz
      material_params:
        gmax: 65000.0
        gamma_ref: 0.0012
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    loaded = load_project_config(cfg)
    assert loaded.profile.layers[0].material.value == "mkz"


def test_gqh_missing_required_params_rejected(tmp_path: Path) -> None:
    cfg = tmp_path / "gqh_bad.yml"
    cfg.write_text(
        """
project_name: gqh-bad
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: gqh
      material_params:
        gmax: 65000.0
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_opensees_backend_rejects_mkz_and_gqh(tmp_path: Path) -> None:
    cfg = tmp_path / "mkz_opensees.yml"
    cfg.write_text(
        """
project_name: mkz-opensees
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: mkz
      material_params:
        gmax: 65000.0
        gamma_ref: 0.0012
analysis:
  solver_backend: opensees
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)
