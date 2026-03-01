from pathlib import Path

import pytest
from dsra1d.config import load_project_config


def test_load_config_ok() -> None:
    cfg = load_project_config(Path("examples/configs/effective_stress.yml"))
    assert cfg.project_name == "sample-effective-stress"
    assert cfg.analysis.dt is not None
    assert cfg.analysis.dt > 0.0


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
