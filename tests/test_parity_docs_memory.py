from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

CANONICAL_CASE = "examples/native/deepsoil_gqh_5layer_baseline.yml"
PRIMARY_WORKBOOK = "tests/Results_profile_0_motion_Kocaeli.xlsx"
ALLOWED_VERDICTS = {
    "improved_non_accepting",
    "regressed",
    "falsified",
    "diagnostic_only",
    "accepted",
}
REQUIRED_FIELDS = {
    "id",
    "date",
    "status",
    "baseline_case",
    "reference_workbook",
    "family",
    "hypothesis",
    "change_summary",
    "artifacts",
    "metrics",
    "verdict",
    "do_not_repeat",
    "next_if_any",
}


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_manifest() -> list[dict]:
    manifest_path = REPO_ROOT / "parity_experiment_index.json"
    return json.loads(_read_text(manifest_path))


def test_parity_experiment_index_is_valid() -> None:
    entries = _load_manifest()
    assert isinstance(entries, list)
    assert entries

    for entry in entries:
        assert REQUIRED_FIELDS.issubset(entry.keys()), entry
        assert entry["verdict"] in ALLOWED_VERDICTS, entry["verdict"]
        assert str(entry["do_not_repeat"]).strip()
        assert entry["baseline_case"] == CANONICAL_CASE
        assert entry["reference_workbook"] == PRIMARY_WORKBOOK


def test_docs_share_canonical_case_and_workbook() -> None:
    doc_paths = [
        REPO_ROOT / "IMPLEMENTATION_STATUS.md",
        REPO_ROOT / "PROJECT_MAP.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "README.md",
        REPO_ROOT / "DEEPSOIL_BASELINE_PARITY_RESEARCH.md",
        REPO_ROOT / "PARITY_MEMORY.md",
    ]

    for path in doc_paths:
        text = _read_text(path)
        assert CANONICAL_CASE in text, path
        assert PRIMARY_WORKBOOK in text, path


def test_memory_and_research_reference_all_manifest_ids() -> None:
    entries = _load_manifest()
    research = _read_text(REPO_ROOT / "DEEPSOIL_BASELINE_PARITY_RESEARCH.md")
    memory = _read_text(REPO_ROOT / "PARITY_MEMORY.md")

    for entry in entries:
        experiment_id = entry["id"]
        assert experiment_id in research, experiment_id
        assert experiment_id in memory, experiment_id


def test_docs_include_current_technical_direction() -> None:
    status_text = _read_text(REPO_ROOT / "IMPLEMENTATION_STATUS.md")
    research_text = _read_text(REPO_ROOT / "DEEPSOIL_BASELINE_PARITY_RESEARCH.md")
    agents_text = _read_text(REPO_ROOT / "AGENTS.md")

    for term in ("F_mrdf evolution", "branch-progress", "previous-cycle memory"):
        assert term in status_text
        assert term in research_text
        assert term in agents_text


def test_docs_include_boundary_first_acceptance_truth() -> None:
    status_text = _read_text(REPO_ROOT / "IMPLEMENTATION_STATUS.md")
    research_text = _read_text(REPO_ROOT / "DEEPSOIL_BASELINE_PARITY_RESEARCH.md")
    agents_text = _read_text(REPO_ROOT / "AGENTS.md")

    for text in (status_text, research_text, agents_text):
        assert "elastic_halfspace + outcrop" in text
        assert "rigid + within" in text
        assert "deepsoilout.db3" in text


def test_project_map_mentions_debug_entrypoints_and_artifact_families() -> None:
    text = _read_text(REPO_ROOT / "PROJECT_MAP.md")

    expected_terms = [
        "python/dsra1d/constitutive_debug.py",
        "single_element_*",
        "tangent_audit_*",
        "layer_sweep_*",
        "mode4_*",
    ]

    for term in expected_terms:
        assert term in text
