from __future__ import annotations

import json
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOT = REPO_ROOT / "python"
if str(PYTHON_ROOT) not in sys.path:
    sys.path.insert(0, str(PYTHON_ROOT))

from dsra1d.store.result_store import load_result  # noqa: E402


@dataclass(slots=True)
class CaseConfig:
    key: str
    label: str
    boundary: str
    compare_json: Path
    deepsoil_surface_csv: Path
    deepsoil_psa_csv: Path
    run_dir: Path | None = None


@dataclass(slots=True)
class CaseSummary:
    key: str
    label: str
    boundary: str
    run_id: str
    compare_json: str
    run_dir: str
    deepsoil_surface_csv: str
    deepsoil_psa_csv: str
    stratawave_dt_s: float
    deepsoil_dt_s: float
    surface_nrmse: float
    surface_corrcoef: float
    pga_ratio: float
    pga_pct_diff: float
    psa_nrmse: float
    psa_pct_diff_at_peak: float
    psa_peak_period_s: float
    warnings: list[str]
    verdict: str
    note: str


def _default_out_dir() -> Path:
    return REPO_ROOT / "output" / "pdf" / "validation" / "deepsoil_examples" / "report"


def _default_case_configs() -> list[CaseConfig]:
    base = REPO_ROOT / "output" / "pdf" / "validation" / "deepsoil_examples"
    return [
        CaseConfig(
            key="linear_1b",
            label="Example 1B linear",
            boundary="rigid",
            compare_json=base / "linear_1b" / "compare" / "deepsoil_compare.json",
            deepsoil_surface_csv=base / "linear_1b" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "linear_1b" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="linear_1b_mkz0",
            label="Example 1B linear proxy (MKZ zero-damping)",
            boundary="rigid",
            compare_json=base / "linear_1b_mkz0" / "compare" / "deepsoil_compare.json",
            deepsoil_surface_csv=base / "linear_1b" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "linear_1b" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="nonlinear_5a",
            label="Example 5A nonlinear",
            boundary="elastic_halfspace",
            compare_json=base / "nonlinear_5a" / "compare" / "deepsoil_compare.json",
            deepsoil_surface_csv=base / "nonlinear_5a" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "nonlinear_5a" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="nonlinear_5a_rigid",
            label="Example 5A nonlinear rigid-base",
            boundary="rigid",
            compare_json=base / "nonlinear_5a_rigid" / "compare" / "deepsoil_compare.json",
            deepsoil_surface_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="nonlinear_5a_rigid_dt005",
            label="Example 5A nonlinear rigid-base dt=0.005",
            boundary="rigid",
            compare_json=base / "nonlinear_5a_rigid_dt005" / "compare" / "deepsoil_compare.json",
            deepsoil_surface_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="nonlinear_5a_rigid_dt0025",
            label="Example 5A nonlinear rigid-base dt=0.0025",
            boundary="rigid",
            compare_json=(
                base / "nonlinear_5a_rigid_dt0025_fix" / "compare" / "deepsoil_compare.json"
            ),
            deepsoil_surface_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="nonlinear_5a_rigid_dt0025_tuned",
            label="Example 5A nonlinear rigid-base dt=0.0025 tuned",
            boundary="rigid",
            compare_json=(
                base
                / "nonlinear_5a_rigid_dt0025_tuned"
                / "run-eb0e3d716974"
                / "compare"
                / "deepsoil_compare.json"
            ),
            deepsoil_surface_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "nonlinear_5a_rigid" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="nonlinear_5a_elastic_dt005",
            label="Example 5A nonlinear elastic-halfspace dt=0.005",
            boundary="elastic_halfspace",
            compare_json=(
                base / "nonlinear_5a_elastic_dt005_v2" / "compare" / "deepsoil_compare.json"
            ),
            deepsoil_surface_csv=base / "nonlinear_5a" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "nonlinear_5a" / "deepsoil_ref" / "psa.csv",
        ),
        CaseConfig(
            key="nonlinear_5a_elastic_dt0025",
            label="Example 5A nonlinear elastic-halfspace dt=0.0025",
            boundary="elastic_halfspace",
            compare_json=(
                base / "nonlinear_5a_elastic_dt0025_v2" / "compare" / "deepsoil_compare.json"
            ),
            deepsoil_surface_csv=base / "nonlinear_5a" / "deepsoil_ref" / "surface.csv",
            deepsoil_psa_csv=base / "nonlinear_5a" / "deepsoil_ref" / "psa.csv",
        ),
    ]


def _load_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _safe_float(payload: dict[str, Any], key: str) -> float:
    value = payload.get(key)
    return float(value) if value is not None else float("nan")


def _summarize_case(config: CaseConfig) -> CaseSummary | None:
    if not config.compare_json.exists():
        return None
    payload = _load_json(config.compare_json)
    verdict, note = _classify_case(payload)
    run_dir = Path(str(payload["run_dir"]))
    return CaseSummary(
        key=config.key,
        label=config.label,
        boundary=config.boundary,
        run_id=str(payload["run_id"]),
        compare_json=str(config.compare_json),
        run_dir=str(run_dir),
        deepsoil_surface_csv=str(config.deepsoil_surface_csv),
        deepsoil_psa_csv=str(config.deepsoil_psa_csv),
        stratawave_dt_s=_safe_float(payload, "stratawave_dt_s"),
        deepsoil_dt_s=_safe_float(payload, "deepsoil_dt_s"),
        surface_nrmse=_safe_float(payload, "surface_nrmse"),
        surface_corrcoef=_safe_float(payload, "surface_corrcoef"),
        pga_ratio=_safe_float(payload, "pga_ratio"),
        pga_pct_diff=_safe_float(payload, "pga_pct_diff"),
        psa_nrmse=_safe_float(payload, "psa_nrmse"),
        psa_pct_diff_at_peak=_safe_float(payload, "psa_pct_diff_at_peak"),
        psa_peak_period_s=_safe_float(payload, "psa_peak_period_s"),
        warnings=[str(item) for item in payload.get("warnings", [])],
        verdict=verdict,
        note=note,
    )


def _classify_case(payload: dict[str, Any]) -> tuple[str, str]:
    psa_nrmse = _safe_float(payload, "psa_nrmse")
    pga_pct_diff = abs(_safe_float(payload, "pga_pct_diff"))
    surface_corr = abs(_safe_float(payload, "surface_corrcoef"))
    warnings = [str(item).lower() for item in payload.get("warnings", [])]
    timestep_warning = any("time-step mismatch" in item for item in warnings)

    if psa_nrmse <= 0.25 and pga_pct_diff <= 60.0:
        if surface_corr >= 0.15 and not timestep_warning:
            return "good", "PSA ve PGA farklari sinirli, time-history uyumu kabul edilebilir."
        return (
            "partial",
            "PSA seviyesinde kismi uyum var; "
            "time-history uyumu zayif ve/veya zaman adimi uyari var.",
        )
    if psa_nrmse <= 0.40:
        return "partial", "Spektral seviye yaklasimi var, ancak parity henuz guvenli degil."
    return "poor", "Bu vaka parity adayi degil; solver-model farklari baskin."


def _best_case(cases: list[CaseSummary]) -> CaseSummary:
    return min(
        cases,
        key=lambda item: (
            item.psa_nrmse,
            abs(item.pga_pct_diff),
            -abs(item.surface_corrcoef),
        ),
    )


def _register_fonts() -> tuple[str, str]:
    fonts_dir = Path("C:/Windows/Fonts")
    regular = fonts_dir / "arial.ttf"
    bold = fonts_dir / "arialbd.ttf"
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("ArialValidation", str(regular)))
        pdfmetrics.registerFont(TTFont("ArialValidationBold", str(bold)))
        return "ArialValidation", "ArialValidationBold"
    return "Helvetica", "Helvetica-Bold"


def _build_styles(font_name: str, bold_name: str) -> dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "TitleValidation",
            parent=styles["Title"],
            fontName=bold_name,
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1f3340"),
            spaceAfter=12,
        ),
        "h1": ParagraphStyle(
            "Heading1Validation",
            parent=styles["Heading1"],
            fontName=bold_name,
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1f3340"),
            spaceAfter=8,
            spaceBefore=10,
        ),
        "h2": ParagraphStyle(
            "Heading2Validation",
            parent=styles["Heading2"],
            fontName=bold_name,
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#2f4f4f"),
            spaceAfter=6,
            spaceBefore=6,
        ),
        "body": ParagraphStyle(
            "BodyValidation",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=9.5,
            leading=13,
            spaceAfter=6,
        ),
        "small": ParagraphStyle(
            "SmallValidation",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#555555"),
            spaceAfter=4,
        ),
    }


def _load_two_column_csv(path: Path) -> tuple[np.ndarray, np.ndarray]:
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    return np.asarray(data[:, 0], dtype=float), np.asarray(data[:, 1], dtype=float)


def _plot_case_metrics(cases: list[CaseSummary], out_path: Path) -> Path:
    labels = [case.key.replace("_", "\n") for case in cases]
    surface = np.array([case.surface_nrmse for case in cases], dtype=float)
    psa = np.array([case.psa_nrmse for case in cases], dtype=float)
    x = np.arange(len(cases))

    fig, ax = plt.subplots(figsize=(10, 4.6))
    width = 0.38
    ax.bar(x - width / 2, surface, width=width, color="#c47a3d", label="Surface NRMSE")
    ax.bar(x + width / 2, psa, width=width, color="#2c7a7b", label="PSA NRMSE")
    ax.axhline(0.25, color="#1f3340", lw=1.0, ls="--", label="Partial-parity PSA target")
    ax.set_ylabel("NRMSE")
    ax.set_xlabel("Case")
    ax.set_title("DEEPSOIL parity metrics across current example set")
    ax.set_xticks(x, labels, fontsize=8)
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _plot_best_case(best: CaseSummary, out_dir: Path) -> tuple[Path, Path]:
    result = load_result(best.run_dir)
    time_sw = np.asarray(result.time, dtype=float)
    acc_sw = np.asarray(result.acc_surface, dtype=float)
    if time_sw.size == 0:
        time_sw = np.arange(acc_sw.size, dtype=float) * float(best.stratawave_dt_s)

    time_ds, acc_ds = _load_two_column_csv(Path(best.deepsoil_surface_csv))
    periods_ds, psa_ds = _load_two_column_csv(Path(best.deepsoil_psa_csv))
    periods_sw = np.asarray(result.spectra_periods, dtype=float)
    psa_sw = np.asarray(result.spectra_psa, dtype=float)

    surface_png = out_dir / "best_case_surface_overlay.png"
    psa_png = out_dir / "best_case_psa_overlay.png"

    def _activity_start(time_arr: np.ndarray, acc_arr: np.ndarray) -> float:
        threshold = 0.05 * float(np.max(np.abs(acc_arr))) if acc_arr.size else 0.0
        if threshold <= 0.0:
            return float(time_arr[0]) if time_arr.size else 0.0
        idx = np.flatnonzero(np.abs(acc_arr) >= threshold)
        return float(time_arr[int(idx[0])]) if idx.size else float(time_arr[0])

    common_end = min(float(time_sw[-1]), float(time_ds[-1]))
    start_time = max(_activity_start(time_sw, acc_sw), _activity_start(time_ds, acc_ds))
    window_end = min(common_end, start_time + 12.0)
    sw_mask = (time_sw >= start_time) & (time_sw <= window_end)
    ds_mask = (time_ds >= start_time) & (time_ds <= window_end)
    acc_sw_norm = acc_sw / max(float(np.max(np.abs(acc_sw))), 1.0e-12)
    acc_ds_norm = acc_ds / max(float(np.max(np.abs(acc_ds))), 1.0e-12)

    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(time_ds[ds_mask], acc_ds_norm[ds_mask], color="#1f3340", lw=1.0, label="DEEPSOIL")
    ax.plot(time_sw[sw_mask], acc_sw_norm[sw_mask], color="#c47a3d", lw=1.0, label="StrataWave")
    ax.set_title(
        f"{best.label}: normalized surface acceleration "
        f"({start_time:.1f}-{window_end:.1f} s)"
    )
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Normalized acc / PGA")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(surface_png, dpi=160, bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(periods_ds, psa_ds, color="#1f3340", lw=1.2, label="DEEPSOIL")
    ax.plot(periods_sw, psa_sw, color="#2c7a7b", lw=1.2, label="StrataWave")
    ax.set_title(f"{best.label}: PSA overlay")
    ax.set_xlabel("Period (s)")
    ax.set_ylabel("PSA (m/s^2)")
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(psa_png, dpi=160, bbox_inches="tight")
    plt.close(fig)

    return surface_png, psa_png


def _status_matrix(best: CaseSummary) -> list[list[str]]:
    return [
        [
            "Native linear/EQL/nonlinear",
            "Calisiyor",
            "Example pack ve native run artifact'leri var.",
        ],
        [
            "OpenSees effective-stress adapter",
            "Calisiyor",
            "Smoke/reference run artifact'leri mevcut.",
        ],
        [
            "DEEPSOIL parity",
            "Kismi",
            f"En iyi vaka {best.key} ve bu vaka PSA seviyesinde kisimli uyum gosteriyor.",
        ],
        [
            "Native full effective-stress solver",
            "Eksik",
            "OpenSees adaptoru var, native u-p solver yok.",
        ],
    ]


def _write_markdown(
    out_path: Path,
    cases: list[CaseSummary],
    best: CaseSummary,
    generated_utc: str,
) -> Path:
    lines: list[str] = [
        "# StrataWave DEEPSOIL Example Parity Report",
        "",
        f"- Generated UTC: `{generated_utc}`",
        f"- Best current case: `{best.key}`",
        "",
        "## Executive verdict",
        "",
        "- StrataWave ana analiz yollari calisiyor.",
        "- OpenSees destekli effective-stress adapter calisiyor.",
        "- DEEPSOIL parity araci mevcut, ancak tam esdegerlik kapanmadi.",
        f"- En iyi mevcut vaka `{best.key}` ve bu vaka icin `PSA NRMSE={best.psa_nrmse:.4f}`.",
        "",
        "## Case matrix",
        "",
        "| Case | Boundary | dt_sw (s) | Surface NRMSE | "
        "Surface Corr | PGA diff (%) | PSA NRMSE | Verdict |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case in cases:
        lines.append(
            f"| {case.key} | {case.boundary} | {case.stratawave_dt_s:.4f} | "
            f"{case.surface_nrmse:.4f} | {case.surface_corrcoef:.4f} | "
            f"{case.pga_pct_diff:.2f} | {case.psa_nrmse:.4f} | {case.verdict} |"
        )

    lines.extend(
        [
            "",
            "## Key findings",
            "",
            f"- Best case: `{best.key}` ({best.label})",
            f"- Best-case PSA NRMSE: `{best.psa_nrmse:.4f}`",
            f"- Best-case PGA diff: `{best.pga_pct_diff:.2f}%`",
            f"- Best-case surface correlation: `{best.surface_corrcoef:.4f}`",
            "",
            "## Technical caveats",
            "",
            "- Native linear/nonlinear solvers are currently fixed-base oriented, "
            "while some DEEPSOIL examples use elastic halfspace.",
            "- Small-strain damping treatment is not yet closed to DEEPSOIL formulations.",
            "- Current nonlinear MKZ/GQH path is operational, "
            "but not yet published-reference calibrated for full parity.",
            "",
            "## Best-case warnings",
            "",
        ]
    )
    if best.warnings:
        for warning in best.warnings:
            lines.append(f"- {warning}")
    else:
        lines.append("- None")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _write_json(
    out_path: Path,
    cases: list[CaseSummary],
    best: CaseSummary,
    generated_utc: str,
    pdf_path: Path,
    assets: dict[str, str],
) -> Path:
    payload = {
        "generated_utc": generated_utc,
        "report_kind": "deepsoil_example_parity",
        "pdf_path": str(pdf_path),
        "best_case": asdict(best),
        "cases": [asdict(case) for case in cases],
        "assets": assets,
        "summary": {
            "native_solver_status": "working",
            "opensees_adapter_status": "working",
            "deepsoil_parity_status": "partial",
            "native_full_effective_stress_status": "missing",
        },
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path


def _build_pdf(
    pdf_path: Path,
    cases: list[CaseSummary],
    best: CaseSummary,
    generated_utc: str,
    metrics_png: Path,
    surface_png: Path,
    psa_png: Path,
) -> Path:
    font_name, bold_name = _register_fonts()
    styles = _build_styles(font_name, bold_name)
    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=16 * mm,
        bottomMargin=14 * mm,
    )
    story: list[Any] = []

    story.extend(
        [
            Paragraph("StrataWave Uyum Durumu ve DEEPSOIL Example Parity Raporu", styles["title"]),
            Paragraph(f"Generated UTC: {generated_utc}", styles["small"]),
            Paragraph(
                "Bu rapor, mevcut repo uzerindeki native StrataWave run'lari ile "
                "DEEPSOIL 7 batch referans ciktilarinin dogrudan karsilastirilmasini ozetler. "
                "Ama amac tam DEEPSOIL esdegerligi iddia etmek degil; mevcut parity seviyesini "
                "dürüstce gostermektir.",
                styles["body"],
            ),
            Spacer(1, 6),
            Paragraph("Executive verdict", styles["h1"]),
            Paragraph(
                "StrataWave ana analiz yollari ve OpenSees effective-stress adapter'i calisiyor. "
                "DEEPSOIL parity ise su an kismi seviyede. En iyi mevcut vaka, "
                f"<b>{best.key}</b> icin <b>PSA NRMSE={best.psa_nrmse:.4f}</b> veriyor; "
                "buna ragmen time-history korelasyonu zayif kaldigi icin bu sonuc yalnizca "
                "PSA-seviyesinde kisimli uyum olarak yorumlanmalidir.",
                styles["body"],
            ),
        ]
    )

    status_rows = [["Bilesen", "Durum", "Not"], *_status_matrix(best)]
    status_table = Table(status_rows, colWidths=[55 * mm, 26 * mm, 87 * mm])
    status_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbe7e4")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f3340")),
                ("FONTNAME", (0, 0), (-1, 0), bold_name),
                ("FONTNAME", (0, 1), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9ab0aa")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fbfa")]),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend([Spacer(1, 6), status_table, Spacer(1, 8)])

    story.append(Paragraph("Case matrix", styles["h1"]))
    case_rows = [[
        "Case",
        "Boundary",
        "dt_sw",
        "Surf NRMSE",
        "Surf Corr",
        "PGA diff %",
        "PSA NRMSE",
        "Verdict",
    ]]
    for case in cases:
        case_rows.append(
            [
                case.key,
                case.boundary,
                f"{case.stratawave_dt_s:.4f}",
                f"{case.surface_nrmse:.4f}",
                f"{case.surface_corrcoef:.4f}",
                f"{case.pga_pct_diff:.1f}",
                f"{case.psa_nrmse:.4f}",
                case.verdict,
            ]
        )
    case_table = Table(
        case_rows,
        colWidths=[36 * mm, 22 * mm, 16 * mm, 20 * mm, 19 * mm, 18 * mm, 18 * mm, 18 * mm],
    )
    case_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f3340")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), bold_name),
                ("FONTNAME", (0, 1), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 7.6),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#a7b5b5")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fbfa")]),
            ]
        )
    )
    story.extend([case_table, Spacer(1, 8)])

    story.extend(
        [
            Paragraph("Current findings", styles["h1"]),
            Paragraph(
                f"<b>Best current case:</b> {best.label} ({best.key}). "
                f"PSA NRMSE={best.psa_nrmse:.4f}, PGA diff={best.pga_pct_diff:.2f}%, "
                f"surface correlation={best.surface_corrcoef:.4f}.",
                styles["body"],
            ),
            Paragraph(
                "Bu vaka, diger nonlinear ve linear denemelere gore "
                "daha makul bir spektral uyum gosteriyor. "
                "Ancak time-history tarafinda guvenli bir parity iddiasi icin yeterli degil.",
                styles["body"],
            ),
            Paragraph("Technical caveats", styles["h2"]),
            Paragraph(
                "1) Native linear/nonlinear solver su an base-fixed odakli, "
                "oysa DEEPSOIL orneklerinin bir kismi elastic-halfspace kullaniyor.",
                styles["body"],
            ),
            Paragraph(
                "2) Small-strain damping formulasyonu ve complex-modulus davranisi "
                "henuz birebir kapatilmadi.",
                styles["body"],
            ),
            Paragraph(
                "3) Native MKZ/GQH patikasi calisiyor, fakat published-reference seviyesinde "
                "tam konstitutif parity kapanmadi.",
                styles["body"],
            ),
        ]
    )

    story.append(PageBreak())
    story.extend(
        [
            Paragraph("Metrics overview", styles["h1"]),
            Paragraph(
                "Asagidaki grafik, mevcut ornek setinde surface ve PSA NRMSE dagilimini gosterir. "
                "NRMSE dusuk oldukca parity iyilesir. Raporun mevcut yorumu icin PSA NRMSE "
                "daha agirlikli kullanilmistir.",
                styles["body"],
            ),
            Image(str(metrics_png), width=178 * mm, height=82 * mm),
            Spacer(1, 8),
            Paragraph("Best-case overlays", styles["h1"]),
            Paragraph(
                "PSA overlay, en iyi mevcut vakanin DEEPSOIL ile spektral benzerligini; "
                "surface acceleration overlay ise time-domain tarafindaki "
                "zayifligi ayni anda gosterir.",
                styles["body"],
            ),
            Image(str(psa_png), width=178 * mm, height=68 * mm),
            Spacer(1, 4),
            Image(str(surface_png), width=178 * mm, height=68 * mm),
        ]
    )

    story.extend(
        [
            Paragraph("Conclusion", styles["h1"]),
            Paragraph(
                "Mevcut repo, hibrit hedefe uyumludur: "
                "native linear/EQL/nonlinear yollar calisiyor, "
                "OpenSees effective-stress adapter'i calisiyor, DEEPSOIL parity tooling mevcut. "
                "Ancak bu nokta tam DEEPSOIL esdegerligi degildir.",
                styles["body"],
            ),
            Paragraph(
                f"En iyi mevcut parity vakasi <b>{best.key}</b> olup, bu vaka icin "
                f"PSA NRMSE={best.psa_nrmse:.4f} ve PGA farki "
                f"{best.pga_pct_diff:.2f}% seviyesindedir. "
                "Dolayisiyla bugunku dogru teknik ifade: "
                "<b>DEEPSOIL-benzeri is akisi + OpenSees destekli effective-stress dogrulamasi + "
                "native MKZ/GQH cekirdegi olan hibrit analiz platformu</b>.",
                styles["body"],
            ),
            Paragraph("Best-case warnings", styles["h2"]),
        ]
    )
    if best.warnings:
        for warning in best.warnings:
            story.append(Paragraph(f"- {warning}", styles["body"]))
    else:
        story.append(Paragraph("- No warning recorded for best case.", styles["body"]))

    doc.build(story)
    return pdf_path


def build_report(out_dir: Path | None = None) -> dict[str, Any]:
    out_dir = out_dir or _default_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    cases = [
        case
        for item in _default_case_configs()
        if (case := _summarize_case(item)) is not None
    ]
    if not cases:
        raise FileNotFoundError(
            "No DEEPSOIL compare JSON files were found under "
            "output/pdf/validation/deepsoil_examples."
        )

    best = _best_case(cases)
    metrics_png = _plot_case_metrics(cases, assets_dir / "case_metrics_overview.png")
    surface_png, psa_png = _plot_best_case(best, assets_dir)

    generated_utc = datetime.now(UTC).isoformat()
    pdf_path = out_dir / "deepsoil_example_parity_report.pdf"
    md_path = out_dir / "deepsoil_example_parity_report.md"
    json_path = out_dir / "deepsoil_example_parity_report.json"

    _build_pdf(pdf_path, cases, best, generated_utc, metrics_png, surface_png, psa_png)
    _write_markdown(md_path, cases, best, generated_utc)
    _write_json(
        json_path,
        cases,
        best,
        generated_utc,
        pdf_path,
        {
            "case_metrics_overview": str(metrics_png),
            "best_case_surface_overlay": str(surface_png),
            "best_case_psa_overlay": str(psa_png),
        },
    )

    return {
        "generated_utc": generated_utc,
        "pdf": str(pdf_path),
        "markdown": str(md_path),
        "json": str(json_path),
        "best_case": asdict(best),
    }


def main() -> int:
    payload = build_report()
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
