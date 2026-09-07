"""PDF generation isolated inside the optional paid plugin."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:  # Core app must still work without this optional dependency.
    REPORTLAB_AVAILABLE = False


def is_available() -> bool:
    return REPORTLAB_AVAILABLE


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "、".join(str(item) for item in value)
    if isinstance(value, bool):
        return "はい" if value else "いいえ"
    return str(value)


def build_pdf(
    *,
    case_data: dict[str, Any],
    opinion: dict[str, Any],
    navigation_version: str,
    plugin_version: str,
) -> bytes:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("PDF生成にはoptional requirementsのreportlabが必要です。")

    font_name = "HeiseiKakuGo-W5"
    font_candidates = [
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"),
        Path("C:/Windows/Fonts/msgothic.ttc"),
    ]
    embedded_font_loaded = False
    for font_path in font_candidates:
        if not font_path.is_file():
            continue
        try:
            candidate_name = "OnchipReportJapanese"
            if candidate_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(candidate_name, str(font_path), subfontIndex=0))
            font_name = candidate_name
            embedded_font_loaded = True
            break
        except Exception:
            continue
    if not embedded_font_loaded and font_name not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=17 * mm,
        title="実験条件検討レポート",
        author="On-Chip OpeR",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "JPTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=25,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#173d66"),
        spaceAfter=10,
    )
    heading = ParagraphStyle(
        "JPHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=12,
        leading=17,
        textColor=colors.HexColor("#0b5fa5"),
        spaceBefore=10,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "JPBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8.8,
        leading=13.5,
        wordWrap="CJK",
        spaceAfter=4,
    )
    small = ParagraphStyle(
        "JPSmall",
        parent=body,
        fontSize=7.5,
        leading=11,
        textColor=colors.HexColor("#566b80"),
    )
    warning = ParagraphStyle(
        "JPWarning",
        parent=body,
        textColor=colors.HexColor("#8f2334"),
        backColor=colors.HexColor("#fff7f8"),
        borderColor=colors.HexColor("#b5384c"),
        borderWidth=0.7,
        borderPadding=7,
        spaceAfter=8,
    )

    story = [
        Paragraph("実験条件検討レポート", title),
        Paragraph(
            escape(
                f"ナビゲーション：{navigation_version} ／ プラグイン：{plugin_version} ／ "
                f"生成日時：{opinion.get('generated_at', '')}"
            ),
            small,
        ),
        Paragraph(escape(opinion.get("disclaimer", "")), warning),
    ]

    def add_heading(label: str) -> None:
        story.append(Paragraph(escape(label), heading))

    def add_table(rows: list[tuple[str, Any]], widths=(48 * mm, 112 * mm)) -> None:
        data = [
            [Paragraph(escape(_text(label)), body), Paragraph(escape(_text(value)).replace("\n", "<br/>"), body)]
            for label, value in rows
            if _text(value).strip()
        ]
        if not data:
            story.append(Paragraph("記載なし", body))
            return
        table = Table(data, colWidths=list(widths), hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), font_name),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef7ff")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#173d66")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c9d9e8")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.extend([table, Spacer(1, 5)])

    add_heading("1. 総合見解")
    add_table(
        [
            ("成立見込み", opinion.get("outlook")),
            ("データ充足度", f"{opinion.get('data_completeness_score', 0)} / 100"),
            ("適用範囲", opinion.get("applicability")),
            ("見解エンジン", f"{opinion.get('engine_name', '')} {opinion.get('engine_version', '')}"),
            ("外部通信", "なし"),
        ]
    )

    add_heading("2. 実験概要・封入対象")
    add_table(
        [
            ("実験名", case_data.get("case_name")),
            ("実験段階", case_data.get("experiment_stage")),
            ("実験目的", case_data.get("purpose")),
            ("目的の詳細", case_data.get("purpose_detail")),
            ("封入対象", case_data.get("sample_type")),
            ("名称", case_data.get("sample_name")),
            ("平均サイズ", f"{case_data.get('sample_avg_size_um')} µm" if case_data.get("sample_avg_size_um") else ""),
            ("最大サイズ", f"{case_data.get('sample_max_size_um')} µm" if case_data.get("sample_max_size_um") else ""),
            ("濃度", f"{case_data.get('sample_concentration_per_ml')} /mL" if case_data.get("sample_concentration_per_ml") else ""),
            ("凝集", case_data.get("aggregation")),
            ("生存性が必要", case_data.get("viability_required")),
        ]
    )

    add_heading("3. 培地・物性")
    add_table(
        [
            ("培地・水相", case_data.get("medium_name")),
            ("組成メモ", case_data.get("medium_composition")),
            ("増粘剤・ゲル化物質", case_data.get("thickener_name") if case_data.get("contains_thickener") else "なし"),
            ("濃度", case_data.get("thickener_concentration")),
            ("作製温度", f"{case_data.get('generation_temperature_c')} ℃"),
            ("粘度状態", case_data.get("viscosity_status")),
            ("粘度", f"{case_data.get('viscosity_mpas')} mPa·s" if case_data.get("viscosity_mpas") else ""),
            ("流動特性", case_data.get("flow_behavior")),
            ("ゲル化条件", case_data.get("gelation_condition")),
        ]
    )

    add_heading("4. 目標ドロップレット・後工程")
    add_table(
        [
            ("形式", case_data.get("droplet_format")),
            ("目標径", f"{case_data.get('target_diameter_um')} µm"),
            ("必要個数", case_data.get("required_droplet_count")),
            ("目標封入数", case_data.get("target_occupancy")),
            ("培養時間", f"{case_data.get('culture_hours')} h"),
            ("油相", case_data.get("oil_name")),
            ("界面活性剤", case_data.get("surfactant_name")),
            ("生物適合性", case_data.get("biocompatibility")),
            ("作製後工程", case_data.get("post_processes")),
        ]
    )

    add_heading("5. 計算結果")
    calculation_rows: list[tuple[str, Any]] = []
    poisson_rows = opinion.get("calculations", {}).get("poisson_loading", {})
    if poisson_rows:
        for key, value in poisson_rows.items():
            calculation_rows.append((key, value))
    elif opinion.get("calculations", {}).get("droplet_volume_pl"):
        calculation_rows.append(("液滴体積", opinion["calculations"]["droplet_volume_pl"]))
    add_table(calculation_rows)

    add_heading("6. 不足情報")
    missing = opinion.get("missing_information", [])
    story.append(Paragraph("<br/>".join(f"・{escape(str(item))}" for item in missing) or "なし", body))

    add_heading("7. 技術的リスク・注意")
    risks = opinion.get("risks", [])
    if risks:
        for item in risks:
            story.append(
                Paragraph(
                    f"<b>[{escape(item.get('level', ''))}] {escape(item.get('title', ''))}</b><br/>"
                    f"{escape(item.get('detail', ''))}<br/>"
                    f"根拠：{escape(item.get('basis', ''))}",
                    body,
                )
            )
    else:
        story.append(Paragraph("入力から明示的な高・中リスクは抽出されませんでした。", body))
    for item in opinion.get("cautions", []):
        story.append(Paragraph(f"・{escape(str(item))}", body))

    add_heading("8. 公開仕様から抽出した製品候補")
    candidates = opinion.get("product_candidates", [])
    if candidates:
        add_table(
            [
                (
                    f"{item.get('product_number', '')} {item.get('product_name', '')}",
                    item.get("reason", ""),
                )
                for item in candidates
            ],
            widths=(68 * mm, 92 * mm),
        )
    else:
        story.append(Paragraph("候補なし、または目標径が未入力です。", body))

    add_heading("9. 推奨する予備試験")
    for index, item in enumerate(opinion.get("preliminary_trials", []), 1):
        story.append(Paragraph(f"{index}. {escape(str(item))}", body))

    story.append(PageBreak())
    add_heading("10. 参照文献メタデータ")
    story.append(
        Paragraph(
            "以下は閉域ナレッジベースへ登録した一次研究のメタデータです。On-chip製品の具体的な操作条件を定めるものではありません。",
            body,
        )
    )
    for source in opinion.get("sources", []):
        story.append(
            Paragraph(
                f"<b>{escape(source.get('title', ''))}</b><br/>"
                f"{escape(source.get('authors', ''))}<br/>"
                f"{escape(source.get('journal', ''))}<br/>"
                f"DOI: {escape(source.get('doi', ''))}<br/>"
                f"{escape(source.get('approved_summary', ''))}",
                body,
            )
        )
        story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()
