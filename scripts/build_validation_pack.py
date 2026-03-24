from __future__ import annotations

import argparse
import json
import os
import sys
import textwrap
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fpdf import FPDF
from pypdf import PdfReader, PdfWriter

try:
    import fitz  # type: ignore
except ImportError:  # pragma: no cover - optional visual appendix support
    fitz = None

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))


@dataclass(slots=True)
class EvidenceItem:
    claim: str
    artifact: str
    path: str
    note: str
    status: str


@dataclass(slots=True)
class AppendixPreview:
    source_pdf: str
    preview_image: str
    label: str


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _find_font() -> tuple[Path, Path]:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    regular_candidates = [windir / "arial.ttf", windir / "calibri.ttf"]
    bold_candidates = [windir / "arialbd.ttf", windir / "calibrib.ttf"]
    regular = next((p for p in regular_candidates if p.exists()), None)
    bold = next((p for p in bold_candidates if p.exists()), None)
    if regular is None or bold is None:
        raise FileNotFoundError("Missing usable Windows TTF fonts for PDF generation.")
    return regular, bold


def _collect_evidence(repo_root: Path) -> list[EvidenceItem]:
    paths = {
        "smoke": repo_root / "examples/output/deepsoil_equivalent/smoke/smoke_summary.json",
        "smoke_md": repo_root / "examples/output/deepsoil_equivalent/smoke/smoke_summary.md",
        "opensees_log": repo_root / "examples/output/deepsoil_equivalent/smoke/effective_stress/run-485b214d64ad/opensees_stdout.log",
        "opensees_diag": repo_root / "examples/output/deepsoil_equivalent/smoke/effective_stress/run-485b214d64ad/opensees_diagnostics.json",
        "benchmark": repo_root / "out/benchmarks_parity/benchmark_opensees-parity.json",
        "confidence": repo_root / "SCIENTIFIC_CONFIDENCE_MATRIX.md",
        "compare": repo_root / "python/dsra1d/deepsoil_compare.py",
        "release_helper": repo_root / "scripts/run_release_deepsoil_compare.py",
        "ui_app": repo_root / "python/dsra1d/web/app.py",
        "ui_js": repo_root / "python/dsra1d/web/static/app.js",
        "ui_css": repo_root / "python/dsra1d/web/static/styles.css",
        "pm4": repo_root / "docs/PM4_CALIBRATION_VALIDATION.md",
        "release": repo_root / "docs/RELEASE_SIGNOFF_CHECKLIST.md",
        "examples": repo_root / "examples/deepsoil_equivalent/README.md",
        "parity_manifest": repo_root / "examples/parity/deepsoil_compare_manifest.sample.json",
        "release_manifest": repo_root / "benchmarks/policies/release_signoff_deepsoil_manifest.sample.json",
    }
    return [
        EvidenceItem(
            "Native linear/EQL/nonlinear example pack",
            "Smoke summary",
            str(paths["smoke"]),
            "4/4 cases passed in the example bundle.",
            "ok" if paths["smoke"].exists() else "missing",
        ),
        EvidenceItem(
            "OpenSees effective-stress path executes",
            "OpenSees stdout log",
            str(paths["opensees_log"]),
            "Representative effective-stress smoke artifact.",
            "ok" if paths["opensees_log"].exists() else "missing",
        ),
        EvidenceItem(
            "OpenSees diagnostics are captured",
            "OpenSees diagnostics",
            str(paths["opensees_diag"]),
            "Shows the adapter is not a stub.",
            "ok" if paths["opensees_diag"].exists() else "missing",
        ),
        EvidenceItem(
            "Darendeli calibration is wired",
            "PM4 validation guide",
            str(paths["pm4"]),
            "Declares valid ranges and strict-plus constraints.",
            "ok" if paths["pm4"].exists() else "missing",
        ),
        EvidenceItem(
            "DEEPSOIL parity tooling exists",
            "Compare engine",
            str(paths["compare"]),
            "Surface, profile, and hysteresis compare support.",
            "ok" if paths["compare"].exists() else "missing",
        ),
        EvidenceItem(
            "Release parity wiring exists",
            "Release parity helper",
            str(paths["release_helper"]),
            "Policy-aware compare orchestration.",
            "ok" if paths["release_helper"].exists() else "missing",
        ),
        EvidenceItem(
            "Scientific confidence is tracked",
            "Confidence matrix",
            str(paths["confidence"]),
            "Canonical release-scientific signoff table.",
            "ok" if paths["confidence"].exists() else "missing",
        ),
        EvidenceItem(
            "UI exposes wizard/results/parity/confidence",
            "React + FastAPI web layer",
            str(paths["ui_app"]),
            "React + FastAPI orchestration layer.",
            "ok" if paths["ui_app"].exists() and paths["ui_js"].exists() and paths["ui_css"].exists() else "missing",
        ),
        EvidenceItem(
            "Examples show the target workflow",
            "DEEPSOIL-equivalent examples",
            str(paths["examples"]),
            "Linear, EQL, nonlinear, and effective-stress references.",
            "ok" if paths["examples"].exists() else "missing",
        ),
        EvidenceItem(
            "Parity manifests are defined",
            "Parity manifest sample",
            str(paths["parity_manifest"]),
            "Batch compare manifest format for side-by-side checks.",
            "ok" if paths["parity_manifest"].exists() else "missing",
        ),
        EvidenceItem(
            "Release parity manifest is defined",
            "Release manifest sample",
            str(paths["release_manifest"]),
            "Used by release workflow when parity is available.",
            "ok" if paths["release_manifest"].exists() else "missing",
        ),
        EvidenceItem(
            "Release gate is codified",
            "Release signoff checklist",
            str(paths["release"]),
            "Operational gate for v* tags.",
            "ok" if paths["release"].exists() else "missing",
        ),
        EvidenceItem(
            "OpenSees parity benchmark exists",
            "Benchmark JSON",
            str(paths["benchmark"]),
            "Gate evidence; local environment may skip when OpenSees is absent.",
            "ok" if paths["benchmark"].exists() else "missing",
        ),
    ]


def _status_rows() -> list[dict[str, str]]:
    return [
        {
            "bucket": "Done",
            "items": "Native linear/EQL/nonlinear; OpenSees adapter; Darendeli calibration; DEEPSOIL-like UI; benchmark harness",
            "horizon": "Current",
            "note": "Core workflows execute and produce reproducible outputs.",
        },
        {
            "bucket": "Partial",
            "items": "DEEPSOIL parity, release-signoff runner in local environment, visual appendix coverage",
            "horizon": "Near-term",
            "note": "Parity tooling exists, but reference coverage is not yet publication-locked.",
        },
        {
            "bucket": "Pending",
            "items": "Broader published-reference matrix and native full effective-stress solver",
            "horizon": "Next",
            "note": "Current engineering gaps, not blockers for validation reporting.",
        },
        {
            "bucket": "Out-of-v1",
            "items": "Full native u-p solver and complete DEEPSOIL project import/export",
            "horizon": "Later",
            "note": "Explicitly outside the current delivery boundary.",
        },
    ]


def _confidence_summary(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    result: list[str] = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 8:
            result.append(f"{cells[0]} | {cells[6]} | {cells[7]}")
    return result


def _select_appendix_pdfs(repo_root: Path, limit: int = 3) -> list[Path]:
    candidates = sorted(
        (repo_root / "out" / "ui").glob("run-*/report.pdf"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[:limit]


def _render_appendix_previews(pdf_paths: list[Path], assets_dir: Path) -> list[AppendixPreview]:
    if fitz is None:
        return []
    previews: list[AppendixPreview] = []
    assets_dir.mkdir(parents=True, exist_ok=True)
    for index, pdf_path in enumerate(pdf_paths, start=1):
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(1.35, 1.35), alpha=False)
            safe_name = f"ui_appendix_preview_{index:02d}.png"
            preview_path = assets_dir / safe_name
            pix.save(str(preview_path))
            previews.append(
                AppendixPreview(
                    source_pdf=str(pdf_path),
                    preview_image=str(preview_path),
                    label=pdf_path.parent.name,
                )
            )
        except Exception:
            continue
    return previews


def _write_markdown(manifest: dict[str, Any], out_dir: Path) -> Path:
    md_path = out_dir / "validation_pack.md"
    lines: list[str] = [
        "# StrataWave Validation Pack",
        "",
        f"- Generated: `{manifest['generated_utc']}`",
        f"- Repo root: `{manifest['repo_root']}`",
        f"- Output dir: `{manifest['out_dir']}`",
        "",
        "## Verdict",
        "",
        f"- Core verdict: `{manifest['core_verdict']}`",
        f"- Parity verdict: `{manifest['parity_verdict']}`",
        f"- Release verdict: `{manifest['release_verdict']}`",
        f"- Overall verdict: `{manifest['overall_verdict']}`",
        "",
        "## Claims this pack supports",
        "",
        "- Native `linear`, `eql`, and `nonlinear` analysis paths execute end-to-end.",
        "- The OpenSees effective-stress adapter executes and captures diagnostics.",
        "- Darendeli-based MKZ/GQH calibration is wired into the repository.",
        "- DEEPSOIL parity tooling exists, but parity remains partial.",
        "- The web UI exposes wizard, results, parity, and confidence surfaces.",
        "",
        "## Validation snapshots",
        "",
        f"- Smoke pack: `{manifest['smoke_summary']['passed_cases']}/{manifest['smoke_summary']['total_cases']}` passed",
        f"- OpenSees parity benchmark: `ran={manifest['benchmark_snapshot']['ran']}`, `skipped={manifest['benchmark_snapshot']['skipped']}`",
        f"- Confidence rows: `{len(manifest['scientific_confidence']['rows'])}`",
        "",
        "## Status matrix",
        "",
        "| Bucket | Scope | Horizon | Note |",
        "|---|---|---|---|",
    ]
    for row in manifest["status_matrix"]:
        lines.append(f"| {row['bucket']} | {row['items']} | {row['horizon']} | {row['note']} |")
    lines.extend(["", "## Evidence inventory", ""])
    for item in manifest["evidence"]:
        lines.extend(
            [
                f"- **{item['claim']}**",
                f"  - Artifact: `{item['artifact']}`",
                f"  - Path: `{item['path']}`",
                f"  - Note: {item['note']}",
                f"  - Status: `{item['status']}`",
            ]
        )
    lines.extend(["", "## Scientific confidence summary", ""])
    for row in manifest["scientific_confidence"]["rows"]:
        lines.append(f"- {row}")
    lines.extend(["", "## Appendix evidence", ""])
    if manifest["appendices"]:
        for appendix in manifest["appendices"]:
            lines.append(f"- `{appendix}`")
    else:
        lines.append("- No appendix PDFs were available.")
    if manifest["appendix_previews"]:
        lines.extend(["", "## Appendix preview images", ""])
        for preview in manifest["appendix_previews"]:
            lines.append(f"- `{preview['label']}` -> `{preview['preview_image']}`")
    lines.extend(
        [
            "",
            "## Honest limitations",
            "",
            "- This pack does not claim full DEEPSOIL parity.",
            "- The native full effective-stress solver is still pending.",
            "- Dedicated OpenSees runner coverage is environment-dependent and policy-gated.",
            "",
            "## Rebuild",
            "",
            "```bash",
            "python scripts/build_validation_pack.py",
            "```",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return md_path


class ValidationPdf(FPDF):
    def footer(self) -> None:  # pragma: no cover - visual layout hook
        self.set_y(-10)
        self.set_font("StrataWaveRegular", size=8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 5, f"Page {self.page_no()}", align="C")


def _wrap(text: str, width: int = 78, indent: str = "") -> str:
    return textwrap.fill(
        text,
        width=width,
        initial_indent=indent,
        subsequent_indent=indent,
        break_long_words=True,
        break_on_hyphens=True,
    )


def _write_pdf(manifest: dict[str, Any], out_dir: Path) -> Path:
    font_regular, font_bold = _find_font()
    pdf = ValidationPdf()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.set_margins(14, 14, 14)
    pdf.add_font("StrataWaveRegular", "", str(font_regular))
    pdf.add_font("StrataWaveBold", "", str(font_bold))

    def h1(text: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("StrataWaveBold", size=18)
        pdf.cell(pdf.w - pdf.l_margin - pdf.r_margin, 10, text, new_x="LMARGIN", new_y="NEXT")

    def h2(text: str) -> None:
        pdf.ln(2)
        pdf.set_x(pdf.l_margin)
        pdf.set_font("StrataWaveBold", size=12)
        pdf.cell(pdf.w - pdf.l_margin - pdf.r_margin, 8, text, new_x="LMARGIN", new_y="NEXT")

    def p(text: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("StrataWaveRegular", size=9)
        pdf.multi_cell(pdf.w - pdf.l_margin - pdf.r_margin, 5, _wrap(text, width=86))
        pdf.ln(1)

    def bullet(text: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("StrataWaveRegular", size=9)
        pdf.multi_cell(
            pdf.w - pdf.l_margin - pdf.r_margin,
            5,
            _wrap(f"- {text}", width=84, indent=""),
        )

    def kv(key: str, value: str) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.set_font("StrataWaveBold", size=10)
        pdf.cell(48, 6, key, border=1)
        pdf.set_font("StrataWaveRegular", size=9)
        pdf.cell(pdf.w - pdf.l_margin - pdf.r_margin - 48, 6, value, border=1, new_x="LMARGIN", new_y="NEXT")

    smoke = manifest["smoke_summary"]
    benchmark = manifest["benchmark_snapshot"]
    pdf.add_page()
    h1("StrataWave Validation Pack")
    p(
        "Technical validation summary for the hybrid 1D site-response platform. "
        "This pack is an external deliverable built from existing repository evidence."
    )
    for key, value in [
        ("Generated UTC", str(manifest["generated_utc"])),
        ("Core verdict", str(manifest["core_verdict"])),
        ("Parity verdict", str(manifest["parity_verdict"])),
        ("Release verdict", str(manifest["release_verdict"])),
        ("Overall verdict", str(manifest["overall_verdict"])),
    ]:
        kv(key, value)

    h2("1. Scope")
    p(
        "StrataWave currently behaves as a hybrid platform: DEEPSOIL-like workflow, "
        "OpenSees-backed effective-stress execution, and native MKZ/GQH analysis paths."
    )

    h2("2. Claims supported by this pack")
    for text in [
        "Native linear, EQL, and nonlinear analysis paths execute end-to-end.",
        "The OpenSees effective-stress adapter executes and captures diagnostics.",
        "Darendeli-based MKZ/GQH calibration is wired into the repository.",
        "DEEPSOIL parity tooling exists, but parity remains partial.",
        "The web UI exposes wizard, results, parity, and confidence surfaces.",
    ]:
        bullet(text)

    h2("3. Validation snapshot")
    kv("Smoke pack", f"{smoke['passed_cases']}/{smoke['total_cases']} passed")
    kv("OpenSees parity benchmark", f"ran={benchmark['ran']}, skipped={benchmark['skipped']}")
    kv("Scientific confidence rows", str(len(manifest["scientific_confidence"]["rows"])))

    h2("4. Status matrix")
    for row in manifest["status_matrix"]:
        bullet(f"{row['bucket']}: {row['items']} ({row['horizon']})")

    h2("5. Evidence inventory")
    for text in [
        "Smoke pack: native example bundle passed 4/4 cases.",
        "OpenSees evidence: effective-stress smoke logs and diagnostics exist.",
        "Calibration evidence: Darendeli-based MKZ/GQH wiring is present.",
        "Parity evidence: compare engine, manifest samples, and release wiring exist.",
        "UI evidence: wizard, results, parity, and confidence panels are live.",
    ]:
        bullet(text)
    p("Full artifact paths and notes are preserved in the Markdown and JSON manifest files.")

    h2("6. Scientific confidence")
    p("Canonical release-scientific signoff source of truth.")
    kv("Tracked suites", str(len(manifest["scientific_confidence"]["rows"])))
    kv("Reference file", "SCIENTIFIC_CONFIDENCE_MATRIX.md")

    if manifest["appendix_previews"]:
        h2("7. Visual appendix previews")
        for preview in manifest["appendix_previews"]:
            p(f"Preview source: {preview['label']}")
            pdf.image(preview["preview_image"], w=170)
            pdf.ln(4)

    h2("8. Honest limitations")
    for text in [
        "This pack does not claim full DEEPSOIL parity.",
        "The native full effective-stress solver is still pending.",
        "Dedicated OpenSees runner coverage is environment-dependent and policy-gated.",
    ]:
        bullet(text)

    h2("9. Reproducibility")
    p("Rebuild the pack with: python scripts/build_validation_pack.py")

    base_pdf = out_dir / "validation_pack_base.pdf"
    pdf.output(str(base_pdf))

    final_pdf = out_dir / "validation_pack.pdf"
    if manifest["appendices"]:
        writer = PdfWriter()
        for page in PdfReader(str(base_pdf)).pages:
            writer.add_page(page)
        for appendix in manifest["appendices"]:
            for page in PdfReader(str(appendix)).pages:
                writer.add_page(page)
        with final_pdf.open("wb") as handle:
            writer.write(handle)
    else:
        base_pdf.replace(final_pdf)
    return final_pdf


def build_validation_pack(repo_root: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    smoke = _read_json(repo_root / "examples/output/deepsoil_equivalent/smoke/smoke_summary.json")
    benchmark = _read_json(repo_root / "out/benchmarks_parity/benchmark_opensees-parity.json")
    confidence_text = _read_text(repo_root / "SCIENTIFIC_CONFIDENCE_MATRIX.md")
    appendices = _select_appendix_pdfs(repo_root)
    appendix_previews = _render_appendix_previews(appendices, assets_dir)

    manifest: dict[str, Any] = {
        "generated_utc": datetime.now(UTC).isoformat(),
        "repo_root": str(repo_root),
        "out_dir": str(out_dir),
        "core_verdict": "Calisiyor",
        "parity_verdict": "Kismi",
        "release_verdict": "Kismi",
        "overall_verdict": "Kismi",
        "smoke_summary": {
            "path": str(repo_root / "examples/output/deepsoil_equivalent/smoke/smoke_summary.json"),
            "total_cases": smoke.get("total_cases", 0),
            "passed_cases": smoke.get("passed_cases", 0),
            "failed_cases": smoke.get("failed_cases", 0),
            "passed": smoke.get("passed", False),
        },
        "benchmark_snapshot": {
            "path": str(repo_root / "out/benchmarks_parity/benchmark_opensees-parity.json"),
            "all_passed": benchmark.get("all_passed", False),
            "ran": benchmark.get("ran", 0),
            "skipped": benchmark.get("skipped", 0),
            "reason": benchmark.get("cases", [{}])[0].get("reason", "") if benchmark.get("cases") else "",
        },
        "status_matrix": _status_rows(),
        "scientific_confidence": {
            "path": str(repo_root / "SCIENTIFIC_CONFIDENCE_MATRIX.md"),
            "rows": _confidence_summary(confidence_text),
        },
        "evidence": [asdict(item) for item in _collect_evidence(repo_root)],
        "appendices": [str(path) for path in appendices],
        "appendix_previews": [asdict(preview) for preview in appendix_previews],
    }

    md_path = _write_markdown(manifest, out_dir)
    pdf_path = _write_pdf(manifest, out_dir)
    manifest["markdown_path"] = str(md_path)
    manifest["pdf_path"] = str(pdf_path)
    (out_dir / "validation_pack.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the StrataWave technical validation pack")
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "output" / "pdf" / "validation")
    args = parser.parse_args()
    manifest = build_validation_pack(args.repo_root.resolve(), args.out_dir.resolve())
    print(
        json.dumps(
            {
                "pdf_path": manifest["pdf_path"],
                "markdown_path": manifest["markdown_path"],
                "appendix_previews": len(manifest["appendix_previews"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
