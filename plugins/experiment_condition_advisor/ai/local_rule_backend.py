"""Closed, deterministic prototype backend.

This is deliberately not a generative model. It performs transparent
calculations and explicit rules, so the paid plugin UI can be designed and
reviewed before a separately approved closed AI model is connected.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import ExperimentAdvisorBackend
from ..domain.calculations import format_calculation_summary, poisson_loading


class LocalRuleAdvisorBackend(ExperimentAdvisorBackend):
    engine_name = "閉域見解エンジン（ルールベース試作）"
    engine_version = "0.1.0"

    def _completeness(self, case: dict[str, Any]) -> tuple[int, list[str]]:
        checks = [
            ("実験目的", bool(case.get("purpose"))),
            ("封入対象の種類", case.get("sample_type") not in {"", "未選択"}),
            ("封入対象名", bool(case.get("sample_name"))),
            ("封入対象の濃度", float(case.get("sample_concentration_per_ml") or 0) > 0),
            ("培地・水相名", bool(case.get("medium_name"))),
            ("作製時温度", case.get("generation_temperature_c") is not None),
            ("粘度または不明の明示", bool(case.get("viscosity_status"))),
            ("目標液滴径", float(case.get("target_diameter_um") or 0) > 0),
            ("ドロップレット形式", bool(case.get("droplet_format"))),
            ("油相", bool(case.get("oil_name"))),
            ("界面活性剤", bool(case.get("surfactant_name"))),
            ("作製後工程", bool(case.get("post_processes"))),
        ]
        missing = [label for label, ok in checks if not ok]
        score = round(100 * (len(checks) - len(missing)) / len(checks))
        return score, missing

    def generate_opinion(
        self,
        case_data: dict[str, Any],
        *,
        product_candidates: list[dict[str, str]],
        approved_sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        score, missing = self._completeness(case_data)
        risks: list[dict[str, str]] = []
        cautions: list[str] = []
        calculations: dict[str, Any] = {}

        diameter = float(case_data.get("target_diameter_um") or 0)
        concentration = float(case_data.get("sample_concentration_per_ml") or 0)
        if diameter > 0:
            calculations["droplet_volume_pl"] = format_calculation_summary(
                poisson_loading(0, diameter)
            )["液滴体積"]
        if diameter > 0 and concentration > 0:
            poisson = poisson_loading(concentration, diameter)
            calculations["poisson_loading"] = format_calculation_summary(poisson)
            if case_data.get("target_occupancy") == "1個程度" and poisson["multiple_fraction"] > poisson["single_fraction"]:
                risks.append(
                    {
                        "level": "高",
                        "title": "複数封入が単一封入を上回る計算です",
                        "detail": "入力濃度と目標径から求めたランダム封入モデルでは、2個以上の割合が1個封入割合を上回ります。濃度の再検討または非ポアソン型の整列技術の検討が必要です。",
                        "basis": "ポアソン分布による試作計算",
                    }
                )

        if case_data.get("aggregation") in {"あり", "多い", "不明"}:
            risks.append(
                {
                    "level": "高" if case_data.get("aggregation") in {"あり", "多い"} else "中",
                    "title": "凝集・多重封入・閉塞の確認が必要です",
                    "detail": "凝集の有無を実サンプルで確認し、必要に応じて分散状態、前処理、待機時間を予備試験で評価してください。",
                    "basis": "入力された封入対象の凝集情報",
                }
            )

        if case_data.get("contains_thickener"):
            risks.append(
                {
                    "level": "高",
                    "title": "増粘剤・ゲル化物質を含む水相です",
                    "detail": "物質名、濃度、作製温度、ゲル化開始条件、流動特性を確認してください。具体的な圧力・流量はマニュアルまたは社内検証データなしに提示しません。",
                    "basis": "入力された培地組成",
                }
            )

        if case_data.get("viscosity_status") == "未測定・不明":
            risks.append(
                {
                    "level": "高",
                    "title": "作製温度での粘度情報が不足しています",
                    "detail": "粘度が不明なため、流量・圧力の具体的な初期値や調整範囲は判定不能です。必要に応じて粘度または粘度曲線を測定してください。",
                    "basis": "入力不足",
                }
            )
        elif case_data.get("flow_behavior") not in {"", "不明", "ニュートン流体として扱える"}:
            risks.append(
                {
                    "level": "高",
                    "title": "非ニュートン性または粘弾性の可能性があります",
                    "detail": "単一の粘度値だけでは流路内挙動を表せない場合があります。測定温度とせん断条件を記録し、段階的な予備試験を行ってください。",
                    "basis": "入力された流動特性",
                }
            )

        max_size = float(case_data.get("sample_max_size_um") or 0)
        if diameter > 0 and max_size > 0:
            if diameter <= max_size:
                risks.append(
                    {
                        "level": "高",
                        "title": "目標液滴径が封入対象の最大寸法以下です",
                        "detail": "入力値のままでは封入対象が液滴内に収まらない可能性があります。サイズ測定と目標径を再確認してください。",
                        "basis": "入力寸法の直接比較",
                    }
                )
            elif diameter < max_size * 2:
                risks.append(
                    {
                        "level": "中",
                        "title": "目標液滴径と封入対象の最大寸法が近いです",
                        "detail": "変形、凝集、流路通過、液滴形成への影響を予備試験で確認してください。この警告は試作ヒューリスティックであり製品仕様ではありません。",
                        "basis": "試作ヒューリスティック",
                    }
                )

        if case_data.get("viability_required") and case_data.get("biocompatibility") in {"不明", "未確認", ""}:
            risks.append(
                {
                    "level": "高",
                    "title": "油相・界面活性剤の生物適合性が未確認です",
                    "detail": "細胞・菌の生存性が必要な場合、使用予定の油相・界面活性剤と培養時間の組合せを実サンプルまたは適切な対照で確認してください。",
                    "basis": "入力された生存性要件と適合情報",
                }
            )

        culture_hours = float(case_data.get("culture_hours") or 0)
        if culture_hours > 0:
            cautions.append("培養後の液滴安定性、蒸発、物質移動、生存性を作製直後と比較してください。")

        if case_data.get("droplet_format") == "GMD":
            if not case_data.get("gelation_condition"):
                missing.append("GMDのゲル化条件")
            cautions.append("GMDでは温度、ゲル化開始時点、回収・オイル除去までの時間を記録してください。")

        if not product_candidates and diameter > 0:
            cautions.append("製品一覧の公開仕様だけでは目標径に一致する候補を確認できませんでした。担当者へ確認してください。")

        high_count = sum(item["level"] == "高" for item in risks)
        medium_count = sum(item["level"] == "中" for item in risks)
        if score < 45:
            outlook = "判定不能"
        elif high_count >= 2:
            outlook = "低"
        elif high_count or medium_count:
            outlook = "中"
        elif score >= 85:
            outlook = "条件検討を進められる"
        else:
            outlook = "中"

        preliminary_trials = [
            "培地・水相だけで液滴形成と流路閉塞の有無を確認する",
            "必要に応じて模擬粒子または低濃度サンプルで分散性と液滴径を確認する",
            "実サンプルを低濃度から段階的に評価する",
            "作製直後と予定処理後で液滴径、安定性、生存性または活性を比較する",
            "空液滴率、単一封入率、多重封入率、液滴径分布、異常発生を記録する",
        ]

        return {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "engine_name": self.engine_name,
            "engine_version": self.engine_version,
            "network_access": "none",
            "outlook": outlook,
            "data_completeness_score": score,
            "applicability": "社内検証データ未接続",
            "missing_information": sorted(set(missing)),
            "calculations": calculations,
            "risks": risks,
            "cautions": cautions,
            "product_candidates": product_candidates,
            "preliminary_trials": preliminary_trials,
            "sources": approved_sources,
            "disclaimer": "本見解は成功率の保証、診断、SOP、製品マニュアルまたは担当者判断の代替ではありません。",
        }
