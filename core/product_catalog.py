"""Price-free product catalog services shared by the core UI and plugins."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable


def load_product_catalog(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        raise ValueError("製品一覧データの形式が正しくありません。")
    if data.get("price_fields_included") is not False:
        raise ValueError("製品一覧データに価格項目が含まれている可能性があります。")
    return data


def iter_products(catalog: dict[str, Any]) -> Iterable[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    for group in catalog.get("groups", []):
        for category in group.get("categories", []):
            for product in category.get("products", []):
                yield group, category, product



def build_product_name_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return an exact-name lookup enriched with group/category labels.

    Product names are normalized only by collapsing whitespace so names split
    across lines in the source catalog can still be matched in guide text.
    """
    index: dict[str, dict[str, Any]] = {}
    for group, category, product in iter_products(catalog):
        name = " ".join(str(product.get("product_name", "")).split())
        if not name:
            continue
        index[name] = {
            "group": str(group.get("label", "")),
            "category": str(category.get("label", "")),
            **product,
            "product_name": name,
        }
    return index


def find_product_name_spans(
    text: str,
    product_name_index: dict[str, dict[str, Any]],
) -> list[tuple[int, int, dict[str, Any]]]:
    """Find non-overlapping exact product names, preferring longer names."""
    source = str(text)
    if not source or not product_name_index:
        return []
    names = sorted(product_name_index, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(name) for name in names))
    return [
        (match.start(), match.end(), product_name_index[match.group(0)])
        for match in pattern.finditer(source)
    ]

def product_count(catalog: dict[str, Any]) -> int:
    return sum(1 for _ in iter_products(catalog))



def device_compatibility_categories(catalog: dict[str, Any]) -> list[str]:
    labels = {"OS": "On-chip Sort/Flow", "DG": "On-chip Droplet Generator", "DS": "On-chip Droplet Selector", "SP": "On-chip SPiS"}
    found = []
    for _, _, product in iter_products(catalog):
        attrs = _attribute_map(product)
        if "適応製品" not in attrs:
            continue
        for key, label in labels.items():
            if key in attrs["適応製品"] and label not in found:
                found.append(label)
    return found


def filter_products(
    catalog: dict[str, Any],
    *,
    query: str = "",
    group_label: str = "すべて",
    category_label: str = "すべて",
    device_compatibility: str = "",
) -> list[dict[str, Any]]:
    normalized_query = query.strip().lower()
    results: list[dict[str, Any]] = []
    for group, category, product in iter_products(catalog):
        if group_label != "すべて" and group.get("label") != group_label:
            continue
        if device_compatibility:
            compatibility = str(_attribute_map(product).get("適応製品", ""))
            compatibility_tokens = {
                token.strip()
                for token in re.split(r"[,、・/\n]+", compatibility)
                if token.strip()
            }
            if device_compatibility not in compatibility_tokens:
                continue
        if category_label != "すべて":
            if group.get("label") == "試薬・消耗品":
                compatibility = str(_attribute_map(product).get("適応製品", ""))
                mapped = {"On-chip Sort/Flow": "OS", "On-chip Droplet Generator": "DG", "On-chip Droplet Selector": "DS", "On-chip SPiS": "SP"}
                if mapped.get(category_label, category_label) not in compatibility:
                    continue
            elif category.get("label") != category_label:
                continue
        searchable = "\n".join(
            [
                str(product.get("product_number", "")),
                str(product.get("product_name", "")),
                *[
                    f"{attribute.get('label', '')} {attribute.get('value', '')}"
                    for attribute in product.get("attributes", [])
                ],
            ]
        ).lower()
        if normalized_query and normalized_query not in searchable:
            continue
        results.append(
            {
                "group": group.get("label", ""),
                "category": category.get("label", ""),
                **product,
            }
        )
    return results


def _attribute_map(product: dict[str, Any]) -> dict[str, str]:
    return {
        str(item.get("label", "")): str(item.get("value", ""))
        for item in product.get("attributes", [])
    }


def _diameter_range(text: str) -> tuple[float | None, float | None]:
    normalized = text.replace("μ", "µ").replace("ー", "-").replace("–", "-")
    matches = re.findall(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", normalized)
    if matches:
        lows = [float(a) for a, _ in matches]
        highs = [float(b) for _, b in matches]
        return min(lows), max(highs)
    open_match = re.search(r"(\d+(?:\.\d+)?)\s*-\s*\[?\s*µ?m", normalized, re.IGNORECASE)
    if open_match:
        return float(open_match.group(1)), None
    numbers = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", normalized)]
    if len(numbers) >= 2:
        return min(numbers), max(numbers)
    return (numbers[0], numbers[0]) if numbers else (None, None)


def _range_contains(text: str, target: float) -> bool:
    low, high = _diameter_range(text)
    if low is None:
        return False
    return target >= low and (high is None or target <= high)


def find_droplet_product_candidates(
    catalog: dict[str, Any],
    *,
    target_diameter_um: float | None,
    droplet_format: str,
) -> list[dict[str, str]]:
    """Return candidates supported only by the published product fields.

    This function does not create operating conditions, pressure values, or a
    guarantee of compatibility. It only matches target diameter and published
    W/O/GMD labels found in the price-free catalog.
    """
    if not target_diameter_um or target_diameter_um <= 0:
        return []
    candidates: list[dict[str, str]] = []
    requested_format = droplet_format.upper()
    for group, category, product in iter_products(catalog):
        name = str(product.get("product_name", "")).replace("\n", " ")
        attrs = _attribute_map(product)
        reason = ""
        if "Droplet Generator" in name:
            size_text = attrs.get("液滴サイズ", "")
            format_text = attrs.get("作製可能ドロップレット", "")
            if not _range_contains(size_text, target_diameter_um):
                continue
            if requested_format == "GMD" and "GMD" not in format_text:
                continue
            if requested_format == "W/O" and format_text and "W/O" not in format_text:
                continue
            reason = f"掲載液滴サイズ「{size_text.replace(chr(10), ' / ')}」に目標径が含まれます。"
            if format_text:
                reason += f" 掲載形式：{format_text}。"
        elif name.startswith("2D Chip-") and "DG" in name:
            usage_text = attrs.get("用途", "")
            if not _range_contains(usage_text, target_diameter_um):
                continue
            reason = f"用途欄の作製径「{usage_text.replace(chr(10), ' / ')}」に目標径が含まれます。"
        else:
            continue
        candidates.append(
            {
                "product_number": str(product.get("product_number", "")),
                "product_name": name,
                "category": str(category.get("label", "")),
                "reason": reason,
            }
        )
    return candidates[:12]
