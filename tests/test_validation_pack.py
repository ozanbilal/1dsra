from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader

from scripts.build_validation_pack import build_validation_pack


def test_build_validation_pack(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    out_dir = tmp_path / "validation"
    manifest = build_validation_pack(repo_root, out_dir)

    pdf_path = Path(manifest["pdf_path"])
    md_path = Path(manifest["markdown_path"])
    json_path = out_dir / "validation_pack.json"

    assert pdf_path.exists()
    assert md_path.exists()
    assert json_path.exists()
    assert manifest["smoke_summary"]["passed_cases"] == 4
    assert manifest["smoke_summary"]["total_cases"] == 4
    assert manifest["core_verdict"] == "Calisiyor"

    reader = PdfReader(str(pdf_path))
    assert len(reader.pages) >= 4
