from pathlib import Path

import pytest
from dsra1d.config import (
    available_config_templates,
    get_config_template_payload,
    load_project_config,
)


def test_load_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    assert cfg.project_name == "sample-effective-stress"
    assert cfg.analysis.dt is not None
    assert cfg.analysis.dt > 0.0


def test_load_strict_plus_example_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress_strict_plus.yml"))
    assert cfg.project_name == "sample-effective-stress-strict-plus"
    assert cfg.analysis.pm4_validation_profile == "strict_plus"


def test_load_pm4sand_calibration_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/pm4sand_calibration.yml"))
    assert cfg.project_name == "pm4sand-calibration-template"
    assert all(layer.material == "pm4sand" for layer in cfg.profile.layers)


def test_load_pm4silt_calibration_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/pm4silt_calibration.yml"))
    assert cfg.project_name == "pm4silt-calibration-template"
    assert all(layer.material == "pm4silt" for layer in cfg.profile.layers)


def test_load_mkz_gqh_darendeli_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_darendeli.yml"))
    assert cfg.project_name == "sample-mkz-gqh-darendeli"
    assert cfg.profile.layers[0].material.value == "mkz"
    assert cfg.profile.layers[1].material.value == "gqh"
    assert cfg.profile.layers[0].material_params["gamma_ref"] > 0.0
    assert cfg.profile.layers[1].material_params["a1"] > 0.0
    assert cfg.analysis.nonlinear_substeps >= 1


def test_load_deepsoil_equivalent_reference_pack_configs_ok() -> None:
    linear_cfg = load_project_config(Path("examples/deepsoil_equivalent/linear_reference.yml"))
    eql_cfg = load_project_config(Path("examples/deepsoil_equivalent/eql_reference.yml"))
    nonlinear_cfg = load_project_config(
        Path("examples/deepsoil_equivalent/nonlinear_reference.yml")
    )
    effective_cfg = load_project_config(
        Path("examples/deepsoil_equivalent/effective_stress_reference.yml")
    )

    assert linear_cfg.analysis.solver_backend == "linear"
    assert all(layer.material.value == "elastic" for layer in linear_cfg.profile.layers)

    assert eql_cfg.analysis.solver_backend == "eql"
    assert {layer.material.value for layer in eql_cfg.profile.layers} == {"mkz", "gqh"}

    assert nonlinear_cfg.analysis.solver_backend == "nonlinear"
    assert {layer.material.value for layer in nonlinear_cfg.profile.layers} == {"mkz", "gqh"}

    assert effective_cfg.analysis.solver_backend == "opensees"
    assert {layer.material.value for layer in effective_cfg.profile.layers} == {
        "pm4sand",
        "pm4silt",
    }


def test_available_config_templates_contains_pm4_calibration() -> None:
    names = available_config_templates()
    assert "effective-stress" in names
    assert "pm4sand-calibration" in names
    assert "pm4silt-calibration" in names
    assert "mkz-gqh-nonlinear" in names
    assert "mkz-gqh-darendeli" in names


def test_get_config_template_payload_returns_profile_layers() -> None:
    payload = get_config_template_payload("pm4sand-calibration")
    assert payload["project_name"] == "pm4sand-calibration-template"
    profile = payload.get("profile", {})
    assert isinstance(profile, dict)
    layers = profile.get("layers", [])
    assert isinstance(layers, list)
    assert len(layers) >= 2


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


def test_linear_backend_allows_missing_pm4_parameters(tmp_path: Path) -> None:
    cfg = tmp_path / "missing_pm4_linear.yml"
    cfg.write_text(
        """
project_name: missing-pm4-linear
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
analysis:
  solver_backend: linear
""".strip(),
        encoding="utf-8",
    )
    loaded = load_project_config(cfg)
    assert loaded.analysis.solver_backend == "linear"


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


def test_darendeli_calibration_derives_mkz_parameters(tmp_path: Path) -> None:
    cfg = tmp_path / "mkz_darendeli.yml"
    cfg.write_text(
        """
project_name: mkz-darendeli
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: mkz
      calibration:
        source: darendeli
        plasticity_index: 18.0
        ocr: 1.3
        mean_effective_stress_kpa: 75.0
analysis:
  solver_backend: nonlinear
""".strip(),
        encoding="utf-8",
    )
    loaded = load_project_config(cfg)
    params = loaded.profile.layers[0].material_params
    assert params["gmax"] > 0.0
    assert params["gamma_ref"] > 0.0
    assert params["damping_max"] >= params["damping_min"]


def test_darendeli_calibration_rejected_for_non_hysteretic_material(tmp_path: Path) -> None:
    cfg = tmp_path / "elastic_darendeli.yml"
    cfg.write_text(
        """
project_name: elastic-darendeli
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: elastic
      calibration:
        source: darendeli
        plasticity_index: 18.0
        ocr: 1.3
        mean_effective_stress_kpa: 75.0
analysis:
  solver_backend: linear
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)
