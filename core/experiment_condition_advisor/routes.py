"""Built-in Streamlit page for experiment condition review.

The feature is part of the main On-Chip OpeR application and is imported
directly by app.py so page navigation follows the same route pattern as the
other built-in pages.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

from .ai.local_rule_backend import LocalRuleAdvisorBackend
from .domain.input_schema import (
    AVAILABLE_DEVICE_OPTIONS,
    FLOW_BEHAVIOR_OPTIONS,
    POST_PROCESS_OPTIONS,
    PURPOSE_OPTIONS,
    SAMPLE_TYPE_OPTIONS,
)
from .reports.pdf_generator import build_pdf, is_available as pdf_is_available

FEATURE_ID = "experiment_condition_advisor"
FEATURE_VERSION = "0.1.0-prototype"
DATA_SCHEMA_VERSION = 1
REPORT_STATE_KEY = "eca_generated_opinion"


def _load_sources(feature_dir: Path) -> list[dict[str, Any]]:
    path = feature_dir / "data" / "approved_sources.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    sources = data.get("sources", []) if isinstance(data, dict) else []
    return sources if isinstance(sources, list) else []


def _render_advisor_css() -> None:
    st.markdown(
        """
        <style>
        .eca-hero{border:2px solid #1677c8;background:linear-gradient(135deg,#eef7ff,#fff);border-radius:16px;padding:1.1rem 1.25rem;margin:.3rem 0 1rem;line-height:1.65}
                .eca-alert{border-left:6px solid #b5384c;background:#fff7f8;border-radius:9px;padding:.75rem .9rem;margin:.6rem 0 1rem;color:#752235;line-height:1.6}
        .eca-card{border:1px solid #d8e1eb;background:#fff;border-radius:12px;padding:.85rem 1rem;margin:.45rem 0 .75rem;line-height:1.65}
        .eca-risk-high{border-left:6px solid #d64545;background:#fff1f1;border-radius:9px;padding:.75rem .9rem;margin:.45rem 0}
        .eca-risk-medium{border-left:6px solid #e0a800;background:#fff9df;border-radius:9px;padding:.75rem .9rem;margin:.45rem 0}
        .eca-risk-low{border-left:6px solid #1f9d55;background:#effaf3;border-radius:9px;padding:.75rem .9rem;margin:.45rem 0}
        .eca-source{font-size:.88rem;color:#52677b;border-bottom:1px solid #e2e7ec;padding:.55rem 0;line-height:1.55}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _build_case_data() -> dict[str, Any]:
    st.markdown("## 入力")
    tabs = st.tabs(["基本情報・目的", "封入対象", "培地・物性", "液滴・油相", "作製後工程"])

    with tabs[0]:
        c1, c2 = st.columns(2)
        with c1:
            case_name = st.text_input("実験名", key="eca_case_name", placeholder="例：乳酸菌の単一菌封入予備試験")
            experiment_stage = st.selectbox(
                "実験の段階",
                ["アイデア", "予備試験", "条件最適化", "本試験"],
                key="eca_experiment_stage",
            )
        with c2:
            available_devices = st.multiselect(
                "利用可能な装置",
                AVAILABLE_DEVICE_OPTIONS,
                default=["未定"],
                key="eca_available_devices",
            )
            facility_sop = st.selectbox("施設SOP", ["確認中", "あり", "なし"], key="eca_facility_sop")
        purpose = st.selectbox("どのような実験をしたいか", ["未選択", *PURPOSE_OPTIONS], key="eca_purpose")
        purpose_detail = st.text_area(
            "実験目的・比較したいもの・測定したいもの",
            key="eca_purpose_detail",
            placeholder="例：1ドロップレットに菌を1個程度封入し、24時間後の蛍光を比較する",
        )
        success_definition = st.text_area(
            "成功と判断する基準",
            key="eca_success_definition",
            placeholder="例：液滴径の範囲、単一封入率、生存性、蛍光陽性率など",
        )

    with tabs[1]:
        c1, c2 = st.columns(2)
        with c1:
            sample_type = st.selectbox("封入対象の種類", SAMPLE_TYPE_OPTIONS, key="eca_sample_type")
            sample_name = st.text_input("細胞株・菌株・粒子・物質名", key="eca_sample_name")
            sample_avg_size_um = st.number_input(
                "平均サイズ（µm、未測定は0）", min_value=0.0, value=0.0, step=0.1, key="eca_sample_avg_size_um"
            )
            sample_max_size_um = st.number_input(
                "最大サイズ（µm、未測定は0）", min_value=0.0, value=0.0, step=0.1, key="eca_sample_max_size_um"
            )
        with c2:
            sample_concentration_per_ml = st.number_input(
                "濃度（cells、CFU、particles等 / mL）",
                min_value=0.0,
                value=0.0,
                step=1000.0,
                format="%.4g",
                key="eca_sample_concentration",
            )
            aggregation = st.selectbox("凝集の有無", ["不明", "なし", "少ない", "あり", "多い"], key="eca_aggregation")
            sedimentation = st.selectbox("沈降しやすさ", ["不明", "低い", "中程度", "高い"], key="eca_sedimentation")
            viability_required = st.checkbox("作製後の生存性・活性が必要", value=True, key="eca_viability_required")
        sample_notes = st.text_area("封入対象の特徴・懸念", key="eca_sample_notes", placeholder="接着性、形状、せん断への懸念、待機可能時間など")

    with tabs[2]:
        c1, c2 = st.columns(2)
        with c1:
            medium_name = st.text_input("培地・バッファー・水相の名称", key="eca_medium_name")
            medium_composition = st.text_area("組成・添加物・濃度", key="eca_medium_composition", placeholder="血清、塩、糖、抗生物質など分かる範囲")
            generation_temperature_c = st.number_input(
                "ドロップレット作製時の温度（℃）", min_value=0.0, max_value=100.0, value=25.0, step=0.5, key="eca_temperature"
            )
            ph_value = st.text_input("pH（任意）", key="eca_ph")
        with c2:
            contains_thickener = st.checkbox("ガム・増粘剤・ゲル化物質を含む", key="eca_contains_thickener")
            thickener_name = st.text_input("増粘剤・ゲル化物質名", disabled=not contains_thickener, key="eca_thickener_name")
            thickener_concentration = st.text_input("濃度・グレード", disabled=not contains_thickener, key="eca_thickener_concentration")
            gelation_condition = st.text_area("ゲル化条件・開始時間", disabled=not contains_thickener, key="eca_gelation_condition")
        viscosity_status = st.selectbox(
            "粘度情報",
            ["未測定・不明", "メーカー値", "粘度計で測定", "レオメーターで測定"],
            key="eca_viscosity_status",
        )
        viscosity_mpas = st.number_input(
            "作製温度での粘度（mPa·s、未測定は0）", min_value=0.0, value=0.0, step=0.1, key="eca_viscosity_mpas"
        )
        flow_behavior = st.selectbox("流動特性", FLOW_BEHAVIOR_OPTIONS, key="eca_flow_behavior")

    with tabs[3]:
        c1, c2 = st.columns(2)
        with c1:
            droplet_format = st.selectbox("希望する形式", ["W/O", "GMD", "その他"], key="eca_droplet_format")
            target_diameter_um = st.number_input(
                "目標ドロップレット直径（µm）", min_value=1.0, value=60.0, step=1.0, key="eca_target_diameter"
            )
            required_droplet_count = st.number_input(
                "必要なドロップレット数", min_value=0, value=100000, step=10000, key="eca_required_count"
            )
            target_occupancy = st.selectbox("1液滴当たりの目標封入数", ["未定", "0個", "1個程度", "複数"], key="eca_target_occupancy")
        with c2:
            culture_hours = st.number_input("液滴内での培養・保持時間（h）", min_value=0.0, value=0.0, step=1.0, key="eca_culture_hours")
            oil_name = st.text_input("使用予定の油相", key="eca_oil_name")
            surfactant_name = st.text_input("界面活性剤と濃度", key="eca_surfactant_name")
            biocompatibility = st.selectbox("対象サンプルとの適合情報", ["未確認", "不明", "社内実績あり", "文献・メーカー情報あり", "実サンプルで確認済み"], key="eca_biocompatibility")
        droplet_notes = st.text_area("液滴径の許容範囲、CV、安定性、回収方法など", key="eca_droplet_notes")

    with tabs[4]:
        post_processes = st.multiselect("作製後に行うこと", POST_PROCESS_OPTIONS, key="eca_post_processes")
        measurement_detail = st.text_area(
            "測定・培養・選別・分注の詳細",
            key="eca_measurement_detail",
            placeholder="蛍光色素、波長、培養条件、選別基準、プレート形式、回収後の処理など",
        )
        past_conditions = st.text_area("過去の類似条件と結果（任意）", key="eca_past_conditions")

    return {
        "case_name": case_name,
        "experiment_stage": experiment_stage,
        "available_devices": available_devices,
        "facility_sop": facility_sop,
        "purpose": "" if purpose == "未選択" else purpose,
        "purpose_detail": purpose_detail,
        "success_definition": success_definition,
        "sample_type": sample_type,
        "sample_name": sample_name,
        "sample_avg_size_um": sample_avg_size_um,
        "sample_max_size_um": sample_max_size_um,
        "sample_concentration_per_ml": sample_concentration_per_ml,
        "aggregation": aggregation,
        "sedimentation": sedimentation,
        "viability_required": viability_required,
        "sample_notes": sample_notes,
        "medium_name": medium_name,
        "medium_composition": medium_composition,
        "generation_temperature_c": generation_temperature_c,
        "ph": ph_value,
        "contains_thickener": contains_thickener,
        "thickener_name": thickener_name,
        "thickener_concentration": thickener_concentration,
        "gelation_condition": gelation_condition,
        "viscosity_status": viscosity_status,
        "viscosity_mpas": viscosity_mpas,
        "flow_behavior": flow_behavior,
        "droplet_format": droplet_format,
        "target_diameter_um": target_diameter_um,
        "required_droplet_count": required_droplet_count,
        "target_occupancy": target_occupancy,
        "culture_hours": culture_hours,
        "oil_name": oil_name,
        "surfactant_name": surfactant_name,
        "biocompatibility": biocompatibility,
        "droplet_notes": droplet_notes,
        "post_processes": post_processes,
        "measurement_detail": measurement_detail,
        "past_conditions": past_conditions,
    }


def _render_opinion(opinion: dict[str, Any]) -> None:
    st.markdown("## 閉域見解エンジンの出力")
    st.markdown(
        f'<div class="eca-alert"><b>{opinion.get("disclaimer", "")}</b><br>'
        '数値の成功率ではなく、成立見込み、データ充足度、入力不足、技術的リスクを表示しています。</div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("成立見込み", opinion.get("outlook", "判定不能"))
    with c2:
        st.metric("データ充足度", f"{opinion.get('data_completeness_score', 0)} / 100")
    with c3:
        st.metric("適用範囲", opinion.get("applicability", "未確認"))

    calculations = opinion.get("calculations", {})
    if calculations:
        st.markdown("### 透明な計算結果")
        rows = []
        poisson_rows = calculations.get("poisson_loading", {})
        if poisson_rows:
            for label, value in poisson_rows.items():
                rows.append({"項目": label, "計算値": value})
        elif calculations.get("droplet_volume_pl"):
            rows.append({"項目": "液滴体積", "計算値": calculations["droplet_volume_pl"]})
        if rows:
            st.dataframe(rows, use_container_width=True, hide_index=True)
        st.caption("球形液滴とランダム封入を仮定した試作計算です。実測・非ランダム整列・凝集がある場合は一致しません。")

    missing = opinion.get("missing_information", [])
    st.markdown("### 不足情報")
    if missing:
        st.warning("\n".join(f"・{item}" for item in missing))
    else:
        st.success("主要な入力欄は埋まっています。マニュアル・社内検証データとの照合は別途必要です。")

    st.markdown("### 技術的リスク")
    risks = opinion.get("risks", [])
    if not risks:
        st.markdown('<div class="eca-risk-low"><b>明示的な高・中リスクは抽出されませんでした。</b><br>成功を保証するものではありません。</div>', unsafe_allow_html=True)
    for risk in risks:
        css_class = "eca-risk-high" if risk.get("level") == "高" else "eca-risk-medium"
        st.markdown(
            f'<div class="{css_class}"><b>[{risk.get("level", "")}] {risk.get("title", "")}</b><br>'
            f'{risk.get("detail", "")}<br><span style="font-size:.82rem;color:#647588">根拠：{risk.get("basis", "")}</span></div>',
            unsafe_allow_html=True,
        )
    for caution in opinion.get("cautions", []):
        st.info(caution)

    st.markdown("### 公開仕様から抽出した製品候補")
    candidates = opinion.get("product_candidates", [])
    if not candidates:
        st.info("製品候補は表示できません。目標径を確認するか、担当者へ相談してください。")
    else:
        for item in candidates:
            st.markdown(
                f'<div class="eca-card"><b>{item.get("product_name", "")}</b><br>'
                f'製品番号：{item.get("product_number", "")}<br>'
                f'<span style="font-size:.88rem;color:#52677b">{item.get("reason", "")}</span></div>',
                unsafe_allow_html=True,
            )
        st.caption("製品価格表の価格を除外した公開仕様との単純照合です。適合保証・操作条件の指定ではありません。")

    st.markdown("### 推奨する予備試験")
    for index, item in enumerate(opinion.get("preliminary_trials", []), 1):
        st.write(f"{index}. {item}")


def render(
    *,
    navigation_version: str,
    product_catalog: dict[str, Any],
    product_matcher: Any,
) -> None:
    _render_advisor_css()
    feature_dir = Path(__file__).parent
    catalog = product_catalog
    approved_sources = _load_sources(feature_dir)

    st.title("実験条件検討")
    st.markdown(
        """
        <div class="eca-hero">
          <div><b>作製したいドロップレットの目的、封入物、培地、物性、作製後工程を入力してください。</b></div>
          <div>入力値から透明な物理計算、情報不足、リスク、公開仕様上の製品候補、予備実験案を整理します。</div>
        </div>
        <div class="eca-alert"><b>外部AI・外部送信は使用していません。</b><br>
        現在は閉域のルールベース試作です。圧力・流量・成功率など、マニュアルまたは社内検証データにない数値は生成しません。</div>
        """,
        unsafe_allow_html=True,
    )

    case_data = _build_case_data()
    payload = {
        "file_type": "onchip_experiment_condition_advisor_case",
        "feature_id": FEATURE_ID,
        "feature_version": FEATURE_VERSION,
        "data_schema_version": DATA_SCHEMA_VERSION,
        "navigation_version": navigation_version,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "case_data": case_data,
    }
    st.download_button(
        "入力内容をJSONで保存",
        data=json.dumps(payload, ensure_ascii=False, indent=2),
        file_name=f"experiment_condition_case_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True,
        key="eca_download_case_json",
    )

    if st.button("閉域見解を生成・更新", type="primary", use_container_width=True, key="eca_generate_opinion"):
        candidates = []
        if callable(product_matcher):
            candidates = product_matcher(
                catalog,
                target_diameter_um=float(case_data.get("target_diameter_um") or 0),
                droplet_format=str(case_data.get("droplet_format") or ""),
            )
        backend = LocalRuleAdvisorBackend()
        st.session_state[REPORT_STATE_KEY] = {
            "case_data": case_data,
            "opinion": backend.generate_opinion(
                case_data,
                product_candidates=candidates,
                approved_sources=approved_sources,
            ),
        }

    generated = st.session_state.get(REPORT_STATE_KEY)
    if generated:
        opinion = generated.get("opinion", {})
        report_case = generated.get("case_data", case_data)
        _render_opinion(opinion)
        st.markdown("### レポート出力")
        if pdf_is_available():
            try:
                pdf_data = build_pdf(
                    case_data=report_case,
                    opinion=opinion,
                    navigation_version=navigation_version,
                    feature_version=FEATURE_VERSION,
                )
            except Exception as exc:
                st.error(f"PDFを生成できませんでした: {exc}")
            else:
                st.download_button(
                    "実験条件検討レポートをPDFで保存",
                    data=pdf_data,
                    file_name=f"experiment_condition_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="eca_download_pdf",
                )
        else:
            st.warning("PDF出力を利用するには requirements.txt の reportlab をインストールしてください。")

    with st.expander("閉域ナレッジベースに登録した一次研究", expanded=False):
        st.caption("これらは一般的なドロップレット技術の根拠です。On-chip製品の具体的な圧力・流量・適合を定める資料ではありません。")
        for source in approved_sources:
            st.markdown(
                f'<div class="eca-source"><b>{source.get("title", "")}</b><br>'
                f'{source.get("authors", "")}｜{source.get("journal", "")}<br>'
                f'DOI: {source.get("doi", "")}<br>{source.get("approved_summary", "")}</div>',
                unsafe_allow_html=True,
            )
