"""Input option definitions for the experiment condition advisor."""
from __future__ import annotations

PURPOSE_OPTIONS = [
    "単一細胞・単一菌の封入",
    "複数細胞・複数対象の共封入",
    "ドロップレット内培養・増殖",
    "蛍光・産生物・酵素活性のスクリーニング",
    "GMD作製",
    "化学反応・試薬混合",
    "粒子・ビーズ封入",
    "その他",
]

SAMPLE_TYPE_OPTIONS = [
    "未選択",
    "哺乳類細胞",
    "細菌",
    "酵母・真菌",
    "藻類",
    "細胞塊・スフェロイド",
    "ビーズ・粒子",
    "DNA／RNA",
    "タンパク質・酵素",
    "化学物質",
    "複数種類の混合物",
    "その他",
]

FLOW_BEHAVIOR_OPTIONS = [
    "不明",
    "ニュートン流体として扱える",
    "シアシニングの可能性",
    "シアシックニングの可能性",
    "粘弾性・糸引きがある",
]

POST_PROCESS_OPTIONS = [
    "そのまま観察",
    "一定時間培養",
    "蛍光測定",
    "画像解析",
    "ドロップレット選別",
    "プレート分注",
    "破乳・内容物回収",
    "PCR・シーケンス",
    "酵素活性測定",
]

AVAILABLE_DEVICE_OPTIONS = [
    "On-chip Droplet Generator",
    "On-chip Droplet Generator S",
    "On-chip Droplet Selector",
    "On-chip Sort",
    "未定",
]
