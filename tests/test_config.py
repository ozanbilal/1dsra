from pathlib import Path

import pytest

from dsra1d.config import (
    available_config_templates,
    get_config_template_payload,
    load_project_config,
)
from dsra1d.config.models import ProjectConfig


def test_load_core_example_configs_ok() -> None:
    nonlinear_cfg = load_project_config(Path("examples/native/deepsoil_gqh_5layer_baseline.yml"))
    fitted_cfg = load_project_config(Path("examples/native/deepsoil_gqh_5layer_fitted_candidate.yml"))
    literal_cfg = load_project_config(Path("examples/native/deepsoil_gqh_5layer_literal.yml"))
    eql_cfg = load_project_config(Path("examples/native/eql_5layer_darendeli.yml"))
    linear_cfg = load_project_config(Path("examples/native/linear_3layer_sand.yml"))

    assert nonlinear_cfg.analysis.solver_backend == "nonlinear"
    assert fitted_cfg.analysis.solver_backend == "nonlinear"
    assert literal_cfg.analysis.solver_backend == "nonlinear"
    assert eql_cfg.analysis.solver_backend == "eql"
    assert linear_cfg.analysis.solver_backend == "linear"
    assert nonlinear_cfg.motion.input_type == "outcrop"
    assert fitted_cfg.motion.input_type == "outcrop"
    assert literal_cfg.motion.input_type == "outcrop"
    assert {layer.material.value for layer in nonlinear_cfg.profile.layers} == {"gqh"}
    assert {layer.material.value for layer in fitted_cfg.profile.layers} == {"gqh"}
    assert {layer.material.value for layer in literal_cfg.profile.layers} == {"gqh"}
    assert {layer.material.value for layer in eql_cfg.profile.layers}.issubset({"mkz", "gqh"})
    assert {layer.material.value for layer in linear_cfg.profile.layers}.issubset({"mkz", "gqh", "elastic"})


def test_core_defaults_align_to_baseline_semantics() -> None:
    cfg = ProjectConfig.model_validate(
        {
            "project_name": "defaults-check",
            "profile": {
                "layers": [
                    {
                        "name": "L1",
                        "thickness_m": 5.0,
                        "unit_weight_kN_m3": 18.0,
                        "vs_m_s": 180.0,
                        "material": "elastic",
                    }
                ]
            },
        }
    )
    assert cfg.boundary_condition.value == "rigid"
    assert cfg.motion.input_type == "outcrop"


def test_load_literal_deepsoil_example_preserves_theta_values() -> None:
    cfg = load_project_config(Path("examples/native/deepsoil_gqh_5layer_baseline.yml"))
    first = cfg.profile.layers[0]
    assert first.calibration is None
    assert first.material_params["tau_max"] == pytest.approx(419.514)
    assert first.material_params["theta1"] == pytest.approx(-6.71)
    assert first.material_params["theta2"] == pytest.approx(1.17)
    assert first.material_params["theta3"] == pytest.approx(15.4881661891248)
    assert first.material_params["theta4"] == pytest.approx(1.0)
    assert first.material_params["theta5"] == pytest.approx(0.99)
    assert first.material_params["reload_factor"] == pytest.approx(1.1)
    assert first.material_params["adaptive_reload_mode_code"] == pytest.approx(1.0)
    assert first.material_params["adaptive_reload_exponent"] == pytest.approx(0.5)


def test_load_fitted_candidate_example_preserves_calibration() -> None:
    cfg = load_project_config(Path("examples/native/deepsoil_gqh_5layer_fitted_candidate.yml"))
    first = cfg.profile.layers[0]
    assert first.calibration is not None
    assert first.calibration.source == "darendeli"
    assert first.calibration.mean_effective_stress_kpa == pytest.approx(20.38)


def test_effective_bedrock_falls_back_to_last_layer() -> None:
    cfg = load_project_config(Path("examples/native/deepsoil_gqh_5layer_baseline.yml"))
    bedrock = cfg.effective_bedrock()
    last = cfg.profile.layers[-1]
    assert bedrock.vs_m_s == pytest.approx(last.vs_m_s)
    assert bedrock.unit_weight_kn_m3 == pytest.approx(last.unit_weight_kn_m3)


def test_effective_bedrock_prefers_explicit_halfspace(tmp_path: Path) -> None:
    cfg = tmp_path / "explicit_bedrock.yml"
    cfg.write_text(
        """
project_name: explicit-bedrock
profile:
  bedrock:
    name: Rock
    vs_m_s: 760.0
    unit_weight_kN_m3: 25.0
  layers:
    - name: L1
      thickness_m: 20.0
      unit_weight_kN_m3: 20.0
      vs_m_s: 500.0
      material: elastic
motion:
  file: examples/motions/sample_motion.csv
  units: m/s2
analysis:
  solver_backend: nonlinear
""".strip(),
        encoding="utf-8",
    )
    loaded = load_project_config(cfg)
    bedrock = loaded.effective_bedrock()
    assert bedrock.name == "Rock"
    assert bedrock.vs_m_s == pytest.approx(760.0)
    assert bedrock.unit_weight_kn_m3 == pytest.approx(25.0)


def test_load_darendeli_core_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/mkz_gqh_darendeli.yml"))
    assert cfg.project_name == "sample-mkz-gqh-darendeli"
    assert cfg.profile.layers[0].material.value == "mkz"
    assert cfg.profile.layers[1].material.value == "gqh"
    assert cfg.profile.layers[0].calibration is not None
    assert cfg.profile.layers[1].calibration is not None


def test_available_config_templates_are_core_only() -> None:
    assert list(available_config_templates()) == [
        "linear-3layer-sand",
        "mkz-gqh-eql",
        "mkz-gqh-nonlinear",
        "mkz-gqh-darendeli",
    ]


def test_get_config_template_payload_returns_core_layers() -> None:
    payload = get_config_template_payload("mkz-gqh-nonlinear")
    assert payload["project_name"] == "mkz-gqh-nonlinear-template"
    layers = payload["profile"]["layers"]
    assert len(layers) == 2
    assert {layer["material"] for layer in layers} == {"mkz", "gqh"}


def test_invalid_extension() -> None:
    with pytest.raises(ValueError):
        load_project_config(Path("examples/configs/effective_stress.txt"))


def test_legacy_mock_core_config_migrates_to_nonlinear(tmp_path: Path) -> None:
    cfg = tmp_path / "legacy_mock.yml"
    cfg.write_text(
        """
project_name: legacy-mock
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: gqh
      material_params:
        gmax: 60000.0
        gamma_ref: 0.001
        a1: 1.0
        a2: 0.45
        m: 2.0
analysis:
  solver_backend: mock
""".strip(),
        encoding="utf-8",
    )
    with pytest.warns(UserWarning, match="deprecated solver_backend=mock"):
        loaded = load_project_config(cfg)
    assert loaded.analysis.solver_backend == "nonlinear"


def test_legacy_opensees_config_is_rejected(tmp_path: Path) -> None:
    cfg = tmp_path / "legacy_opensees.yml"
    cfg.write_text(
        """
project_name: legacy-opensees
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: gqh
      material_params:
        gmax: 60000.0
        gamma_ref: 0.001
        a1: 1.0
        a2: 0.45
        m: 2.0
analysis:
  solver_backend: opensees
opensees:
  executable: OpenSees
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="OpenSees config is no longer supported"):
        load_project_config(cfg)


def test_legacy_pm4_config_is_rejected(tmp_path: Path) -> None:
    cfg = tmp_path / "legacy_pm4.yml"
    cfg.write_text(
        """
project_name: legacy-pm4
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: pm4sand
      material_params:
        Dr: 0.45
analysis:
  solver_backend: nonlinear
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="PM4/OpenSees config is no longer supported"):
        load_project_config(cfg)


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
  solver_backend: nonlinear
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_project_config(cfg)


def test_elastic_layer_calibration_rejected(tmp_path: Path) -> None:
    cfg = tmp_path / "elastic_calib.yml"
    cfg.write_text(
        """
project_name: elastic-calib
profile:
  layers:
    - name: L1
      thickness_m: 5.0
      unit_weight_kN_m3: 18.0
      vs_m_s: 180.0
      material: elastic
      calibration:
        source: darendeli
        plasticity_index: 10
        ocr: 1
        mean_effective_stress_kpa: 50
analysis:
  solver_backend: nonlinear
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="supported only for MKZ/GQH"):
        load_project_config(cfg)
