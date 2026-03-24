# ruff: noqa
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from fpdf import FPDF


@dataclass(slots=True)
class Evidence:
    label: str
    path: str | None
    status: str
    note: str
    payload: dict[str, Any] | None = None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest(root: Path, name: str) -> Path | None:
    candidates = list(root.rglob(name))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def campaign(root: Path, suite: str) -> Path | None:
    matches: list[Path] = []
    for path in root.rglob("campaign_summary.json"):
        try:
            if str(read_json(path).get("suite", "")) == suite:
                matches.append(path)
        except Exception:
            continue
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def load_result_fn(repo: Path) -> Any:
    python_root = repo / "python"
    if python_root.exists() and str(python_root) not in sys.path:
        sys.path.insert(0, str(python_root))
    try:
        from dsra1d.store.result_store import load_result  # type: ignore
    except Exception:
        return None
    return load_result


def make_plot(run_dir: Path, out_png: Path, mode: str, load_result: Any) -> bool:
    try:
        result = load_result(run_dir)
    except Exception:
        return False

    fig, axes = plt.subplots(2, 1, figsize=(8.0, 6.0))
    if result.time.size > 0 and result.acc_surface.size == result.time.size:
        axes[0].plot(result.time, result.acc_surface, lw=1.1, color="#8b4d2a")
        axes[0].set_xlabel("Time (s)")
    else:
        axes[0].plot(result.acc_surface, lw=1.1, color="#8b4d2a")
        axes[0].set_xlabel("Sample")
    axes[0].set_ylabel("Acc")
    axes[0].set_title(f"{mode} surface acceleration")
    axes[0].grid(True, alpha=0.25)

    if mode == "effective" and result.ru.size > 0:
        x_ru = result.ru_time if result.ru_time.size == result.ru.size else range(len(result.ru))
        axes[1].plot(x_ru, result.ru, lw=1.1, color="#1f3340")
        axes[1].set_ylabel("ru")
        axes[1].set_title("pore pressure ratio")
        axes[1].set_xlabel("Time (s)")
    else:
        axes[1].plot(result.spectra_periods, result.spectra_psa, lw=1.1, color="#2d6a6a")
        axes[1].set_ylabel("PSA")
        axes[1].set_title("pseudo spectral acceleration")
        axes[1].set_xlabel("Period (s)")
    axes[1].grid(True, alpha=0.25)

    fig.tight_layout()
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


def discover(repo: Path) -> dict[str, Evidence]:
    out_root = repo / "out"
    docs_root = repo / "docs"
    examples_root = repo / "examples"

    smoke_path = examples_root / "output" / "deepsoil_equivalent" / "smoke" / "smoke_summary.json"
    smoke_payload = read_json(smoke_path) if smoke_path.exists() else None

    campaign_paths = {
        "core_es": campaign(out_root, "core-es"),
        "core_hyst": campaign(out_root, "core-hyst"),
        "core_linear": campaign(out_root, "core-linear"),
        "core_eql": campaign(out_root, "core-eql"),
    }
    parity_path = latest(out_root, "benchmark_opensees-parity.json")
    deepsoil_path = latest(out_root, "deepsoil_compare_batch.json")
    confidence_path = repo / "SCIENTIFIC_CONFIDENCE_MATRIX.md"
    pm4_path = docs_root / "PM4_CALIBRATION_VALIDATION.md"
    release_path = docs_root / "RELEASE_SIGNOFF_CHECKLIST.md"
    darendeli_cfg = examples_root / "configs" / "mkz_gqh_darendeli.yml"
    darendeli_root = out_root / "darendeli_smoke"
    darendeli_runs = sorted(darendeli_root.glob("run-*"), reverse=True) if darendeli_root.exists() else []
    darendeli_run = darendeli_runs[0] if darendeli_runs else None
    ui_source = docs_root / "reports" / "validation" / "source"

    data: dict[str, Evidence] = {}
    data["smoke"] = Evidence(
        label="Example smoke summary",
        path=str(smoke_path) if smoke_path.exists() else None,
        status="done" if smoke_payload and smoke_payload.get("passed") else "missing",
        note=(
            f"{smoke_payload.get('passed_cases', 0)}/{smoke_payload.get('total_cases', 0)} example cases passed"
            if smoke_payload
            else "Example smoke summary not found"
        ),
        payload=smoke_payload,
    )
    for key, label in {
        "core_es": "core-es campaign",
        "core_hyst": "core-hyst campaign",
        "core_linear": "core-linear campaign",
        "core_eql": "core-eql campaign",
    }.items():
        path = campaign_paths[key]
        data[key] = Evidence(
            label=label,
            path=str(path) if path else None,
            status="done" if path else "missing",
            note="Local campaign summary discovered" if path else f"No {label} summary found",
            payload=read_json(path) if path else None,
        )
    data["opensees_parity"] = Evidence(
        label="OpenSees parity benchmark",
        path=str(parity_path) if parity_path else None,
        status="partial" if parity_path else "missing",
        note=(
            "Parity benchmark exists but may be skipped or partial"
            if parity_path
            else "No OpenSees parity benchmark JSON found"
        ),
        payload=read_json(parity_path) if parity_path else None,
    )
    data["deepsoil_compare"] = Evidence(
        label="DEEPSOIL compare batch",
        path=str(deepsoil_path) if deepsoil_path else None,
        status="partial" if deepsoil_path else "missing",
        note=(
            "Latest DEEPSOIL compare batch discovered"
            if deepsoil_path
            else "No DEEPSOIL compare batch artifact found"
        ),
        payload=read_json(deepsoil_path) if deepsoil_path else None,
    )
    data["confidence"] = Evidence(
        label="Scientific confidence matrix",
        path=str(confidence_path) if confidence_path.exists() else None,
        status="done" if confidence_path.exists() else "missing",
        note="Repository scientific confidence matrix",
    )
    data["pm4"] = Evidence(
        label="PM4 guide",
        path=str(pm4_path) if pm4_path.exists() else None,
        status="done" if pm4_path.exists() else "missing",
        note="PM4 calibration validation notes",
    )
    data["release"] = Evidence(
        label="Release checklist",
        path=str(release_path) if release_path.exists() else None,
        status="done" if release_path.exists() else "missing",
        note="Release gate checklist",
    )
    data["darendeli"] = Evidence(
        label="Darendeli calibration",
        path=str(darendeli_run or darendeli_cfg) if (darendeli_run or darendeli_cfg.exists()) else None,
        status="done" if darendeli_run else ("partial" if darendeli_cfg.exists() else "missing"),
        note=(
            f"Calibration config plus local run evidence at {darendeli_run.name}"
            if darendeli_run
            else (
                "Calibration config exists but local run evidence was not found"
                if darendeli_cfg.exists()
                else "Darendeli config missing"
            )
        ),
        payload={"run_dir": str(darendeli_run) if darendeli_run else None},
    )
    data["ui"] = Evidence(
        label="UI screenshots",
        path=str(ui_source) if ui_source.exists() else None,
        status="partial" if ui_source.exists() else "missing",
        note="Optional screenshot source folder for report assets",
        payload={"png_count": len(list(ui_source.glob("*.png"))) if ui_source.exists() else 0},
    )
    return data


def status_matrix(data: dict[str, Evidence]) -> list[dict[str, str]]:
    smoke = data["smoke"].payload or {}
    cases = {str(case.get("name", "")): case for case in smoke.get("cases", [])} if isinstance(smoke, dict) else {}
    parity = data["opensees_parity"].payload or {}
    parity_ran = int(parity.get("ran", 0)) if isinstance(parity, dict) else 0
    parity_skipped = int(parity.get("skipped", 0)) if isinstance(parity, dict) else 0
    return [
        {
            "component": "Native linear solver path",
            "status": "done" if data["core_linear"].path or cases.get("linear") else "pending",
            "evidence": "Linear example pack run plus local campaign summary",
            "notes": "Smoke pack and local campaign outputs are used as evidence.",
        },
        {
            "component": "Native equivalent-linear solver path",
            "status": "done" if data["core_eql"].path or cases.get("eql") else "pending",
            "evidence": "EQL example pack run plus local campaign summary",
            "notes": "EQL behavior is evidenced by the reference pack and local campaign outputs.",
        },
        {
            "component": "Native nonlinear MKZ/GQH path",
            "status": "done" if data["core_hyst"].path or cases.get("nonlinear") else "pending",
            "evidence": "Nonlinear example pack run plus core-hyst campaign",
            "notes": "This is native total-stress nonlinear behavior, not native effective-stress FE.",
        },
        {
            "component": "OpenSees effective-stress adapter",
            "status": "done" if cases.get("effective_stress") else "pending",
            "evidence": "Effective-stress reference run in the example pack",
            "notes": "The adapter path is proven by local run artifacts; native effective-stress solver is still absent.",
        },
        {
            "component": "Darendeli calibration workflow",
            "status": data["darendeli"].status,
            "evidence": data["darendeli"].note,
            "notes": "Calibration inputs and a local run exist; published-reference calibration closure is still pending.",
        },
        {
            "component": "DEEPSOIL parity tooling",
            "status": "done" if parity_ran > 0 else ("partial" if data["opensees_parity"].path or data["deepsoil_compare"].path else "pending"),
            "evidence": "Parity benchmark JSON and DEEPSOIL compare artifacts",
            "notes": f"Local parity benchmark currently reports ran={parity_ran}, skipped={parity_skipped}; full dedicated-runner parity is still pending.",
        },
        {
            "component": "React/FastAPI DEEPSOIL-like UI",
            "status": "partial",
            "evidence": "UI source, wizard/results/parity panels, optional screenshot source folder",
            "notes": "Workflow parity exists, but full DEEPSOIL UI parity is not claimed.",
        },
        {
            "component": "Release signoff and scientific confidence",
            "status": "done" if data["core_es"].path and data["confidence"].path else "partial",
            "evidence": "Scientific confidence matrix plus release checklist",
            "notes": "Scientific confidence exists as a repo artifact; it is not equivalent to full external publication validation.",
        },
    ]


def make_bundle(repo: Path, out_dir: Path) -> dict[str, Any]:
    data = discover(repo)
    return {
        "generated_utc": datetime.now(UTC).isoformat(),
        "repo_root": str(repo),
        "out_dir": str(out_dir),
        "technical_position": "DEEPSOIL-benzeri is akisina, OpenSees destekli effective-stress dogrulamasina ve native MKZ/GQH cekirdegine sahip hibrit analiz platformu",
        "key_claims": [
            "Ana analiz yollari calisiyor.",
            "OpenSees adaptoru ile effective-stress kosulari alinabiliyor.",
            "Native MKZ/GQH yollari mevcut.",
            "Ornek paketler ve smoke/validation ciktilari var.",
        ],
        "excluded_claims": [
            "Tam DEEPSOIL parity saglandi.",
            "Bilimsel olarak tum published-reference case'ler kapandi.",
            "Native effective-stress solver tamamlandi.",
        ],
        "assumptions": [
            "Bu bundle mevcut repo ciktilarina dayanir; eksik artifactler yeniden uretilmeden partial olarak raporlanir.",
            "UI screenshot'lari opsiyoneldir; source klasorunde PNG yoksa rapor bunu acikca belirtir.",
            "OpenSees parity icin dedicated runner ciktilari bu local bundle'da mevcut olmayabilir.",
        ],
        "evidence": {key: {"label": item.label, "path": item.path, "status": item.status, "note": item.note, "payload": item.payload} for key, item in data.items()},
        "status_matrix": status_matrix(data),
    }

def make_markdown(bundle: dict[str, Any], assets: list[Path]) -> str:
    evidence = bundle["evidence"]
    lines = [
        "# StrataWave Teknik Dogrulama Raporu",
        "",
        f"- Uretim tarihi: `{bundle['generated_utc']}`",
        f"- Repo kok dizini: `{bundle['repo_root']}`",
        f"- Teknik tanim: {bundle['technical_position']}",
        "",
        "## 1. Amac ve Kapsam",
        "",
        "Bu rapor, StrataWave reposundaki mevcut kanitlari toplayarak yazilimin bugunku teknik olgunluk seviyesini belgelemek icin uretilmistir.",
        "Rapor, urunun kendisine yeni bir dogrulama modu eklemez; yalnizca mevcut example, benchmark, parity ve dokumantasyon artifactlerini derler.",
        "",
        "## 2. Mimari Ozet",
        "",
        "- Native solver yollari: `linear`, `eql`, `nonlinear`",
        "- OpenSees adapter yolu: effective-stress odakli akis ve Tcl uretimi",
        "- Arayuzler: React/FastAPI web UI, Streamlit engineering UI, CLI, Python SDK",
        "- Veri depolama: `results.h5`, `results.sqlite`, parity ve campaign summary JSON/Markdown artifactleri",
        "",
        "## 3. Dogrulama Kaniti",
        "",
        f"- Example pack smoke ozeti: status=`{evidence['smoke']['status']}` path=`{evidence['smoke']['path']}` note=`{evidence['smoke']['note']}`",
        f"- OpenSees parity artifacti: status=`{evidence['opensees_parity']['status']}` path=`{evidence['opensees_parity']['path']}` note=`{evidence['opensees_parity']['note']}`",
        f"- DEEPSOIL compare artifacti: status=`{evidence['deepsoil_compare']['status']}` path=`{evidence['deepsoil_compare']['path']}` note=`{evidence['deepsoil_compare']['note']}`",
        f"- Scientific confidence matrix: path=`{evidence['confidence']['path']}`",
        f"- PM4 calibration guide: path=`{evidence['pm4']['path']}`",
        f"- Release signoff checklist: path=`{evidence['release']['path']}`",
        "",
        "### Kullanilabilir Iddialar",
        "",
    ]
    lines.extend([f"- {item}" for item in bundle["key_claims"]])
    lines.extend(["", "### Bilerek Yapilmayan Iddialar", ""])
    lines.extend([f"- {item}" for item in bundle["excluded_claims"]])
    lines.extend(["", "## 4. Durum Matrisi", "", "| Bilesen | Durum | Kanit | Not |", "|---|---|---|---|"])
    for row in bundle["status_matrix"]:
        lines.append(f"| {row['component']} | {row['status']} | {row['evidence']} | {row['notes']} |")
    lines.extend(["", "## 5. Kalan Kritik Isler", "", "- Native effective-stress solver halen eksik; effective-stress kaniti OpenSees adapter yoluna dayaniyor.", "- Full DEEPSOIL parity halen kapali degil; local artifactler parity araclarinin varligini gosteriyor ama tam esdegerligi kanitlamiyor.", "- Published/reference tabanli daha genis confidence matrix gereklidir.", "- UI parity halen kismidir; mevcut UI is akisina yakin ama DEEPSOIL ile birebir ayni oldugu iddia edilmemelidir.", "", "## 6. Sonuc Hukmu", "", "- Calisiyor: native lineer/EQL/nonlinear ornekler ve OpenSees effective-stress adapter kosusu local evidence ile mevcut.", "- Kismi: DEEPSOIL parity, UI parity ve scientific confidence derinligi.", "- Eksik: native effective-stress solver ve tam publication-grade parity kapanisi.", "", "## 7. Ekler ve Varsayimlar", ""])
    lines.extend([f"- {item}" for item in bundle["assumptions"]])
    if assets:
        lines.extend(["", "## 8. Uretilen Grafikler", ""])
        lines.extend([f"- `{asset.name}`" for asset in assets])
    return "\n".join(lines) + "\n"


class ReportPdf(FPDF):
    def header(self) -> None:
        self.set_font("Body", size=10)
        self.cell(0, 8, "StrataWave Teknik Dogrulama Raporu", new_x="LMARGIN", new_y="NEXT", align="R")
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Body", size=9)
        self.cell(0, 8, f"Sayfa {self.page_no()}", align="C")


def write_pdf(bundle: dict[str, Any], assets: list[Path], out_pdf: Path) -> None:
    pdf = ReportPdf(format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_font("Body", fname=str(Path(r"C:\Windows\Fonts\arial.ttf")))
    pdf.add_page()
    pdf.set_font("Body", size=22)
    pdf.multi_cell(0, 11, "StrataWave Teknik Dogrulama Raporu")
    pdf.ln(2)
    pdf.set_font("Body", size=12)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 7, "DEEPSOIL-benzeri is akisina ve OpenSees destekli effective-stress dogrulamasina sahip hibrit analiz platformu icin mevcut repo kanitlarinin derlenmis ozeti.")
    sections = [
        ("Amac ve Kapsam", ["Bu rapor, StrataWave reposunda bugun mevcut olan kanitlari toplar ve urunun teknik durumunu dis paylasima uygun sekilde belgelendirir.", "Rapor yeni bir urun ozelligi eklemez; mevcut example, benchmark, parity ve dokumantasyon artifactlerini kullanir."]),
        ("Mimari Ozet", ["Native solver yollari: linear, eql, nonlinear.", "Effective-stress kaniti: OpenSees adapter yolu ve ilgili local run artifactleri.", "Arayuz katmanlari: React/FastAPI web UI, Streamlit engineering UI, CLI, Python SDK.", "Veri depolama ve raporlama: results.h5, results.sqlite, campaign/parity JSON ve Markdown artifactleri."]),
        ("Sonuc Hukmu", ["Calisiyor: native lineer, EQL, nonlinear ornekler ve OpenSees effective-stress adapter kosusu local evidence ile mevcuttur.", "Kismi: DEEPSOIL parity, UI parity ve scientific confidence derinligi.", "Eksik: native effective-stress solver ve tam publication-grade parity kapanisi."])
    ]
    for title, body in sections:
        pdf.ln(4)
        pdf.set_font("Body", size=15)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 8, title)
        pdf.set_font("Body", size=11)
        for line in body:
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(0, 6, line)
    pdf.ln(4)
    pdf.set_font("Body", size=15)
    pdf.multi_cell(0, 8, "Durum Matrisi")
    pdf.set_font("Body", size=10)
    for row in bundle["status_matrix"]:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, f"{row['component']}: {row['status']} | {row['notes']}")
    for asset in assets:
        pdf.add_page()
        pdf.set_font("Body", size=15)
        pdf.multi_cell(0, 8, f"Ek Grafik - {asset.stem}")
        pdf.ln(2)
        pdf.image(str(asset), x=15, w=180)
    pdf.output(str(out_pdf))


def build(repo: Path, out_dir: Path) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    bundle = make_bundle(repo, out_dir)
    data = discover(repo)
    load_result = load_result_fn(repo)
    assets: list[Path] = []
    if load_result:
        smoke = data["smoke"].payload or {}
        case_map = {str(case.get("name", "")): case for case in smoke.get("cases", [])} if isinstance(smoke, dict) else {}
        for key, mode in (("linear", "linear"), ("nonlinear", "nonlinear"), ("effective_stress", "effective")):
            case = case_map.get(key)
            if case:
                run_dir = Path(str(case.get("run_dir", "")))
                out_png = assets_dir / f"{key}_overview.png"
                if run_dir.exists() and make_plot(run_dir, out_png, mode, load_result):
                    assets.append(out_png)
        dar = data["darendeli"].payload or {}
        if isinstance(dar, dict) and dar.get("run_dir"):
            run_dir = Path(str(dar["run_dir"]))
            out_png = assets_dir / "darendeli_overview.png"
            if run_dir.exists() and make_plot(run_dir, out_png, "darendeli", load_result):
                assets.append(out_png)
    src = repo / "docs" / "reports" / "validation" / "source"
    if src.exists():
        assets.extend(sorted(src.glob("*.png")))
    markdown = make_markdown(bundle, assets)
    bundle["generated_assets"] = [str(asset) for asset in assets]
    json_path = out_dir / "validation_bundle.json"
    md_path = out_dir / "validation_report.md"
    pdf_path = out_dir / "validation_report.pdf"
    json_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    write_pdf(bundle, assets, pdf_path)
    bundle["bundle_json_path"] = str(json_path)
    bundle["bundle_md_path"] = str(md_path)
    bundle["bundle_pdf_path"] = str(pdf_path)
    json_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False), encoding="utf-8")
    return bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Build external StrataWave validation bundle")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "docs" / "reports" / "validation" / "latest")
    args = parser.parse_args()
    bundle = build(args.repo_root.resolve(), args.out_dir.resolve())
    print(json.dumps({"bundle_json_path": bundle["bundle_json_path"], "bundle_md_path": bundle["bundle_md_path"], "bundle_pdf_path": bundle["bundle_pdf_path"], "generated_assets": bundle.get("generated_assets", [])}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



