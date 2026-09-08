"""Transparent physical calculations used by the built-in advisor."""
from __future__ import annotations

import math
from typing import Any


def droplet_volume_pl(diameter_um: float) -> float:
    """Return spherical droplet volume in pL from diameter in micrometres."""
    if diameter_um <= 0:
        raise ValueError("液滴径は0より大きい値が必要です。")
    volume_um3 = math.pi / 6.0 * diameter_um ** 3
    return volume_um3 * 1e-3  # 1 µm^3 = 0.001 pL


def poisson_loading(concentration_per_ml: float, diameter_um: float) -> dict[str, float]:
    """Calculate random loading probabilities for a spherical droplet."""
    if concentration_per_ml < 0:
        raise ValueError("濃度は0以上の値が必要です。")
    volume_pl = droplet_volume_pl(diameter_um)
    volume_ml = volume_pl * 1e-9
    lam = concentration_per_ml * volume_ml
    p0 = math.exp(-lam)
    p1 = lam * p0
    p2plus = max(0.0, 1.0 - p0 - p1)
    return {
        "droplet_volume_pl": volume_pl,
        "lambda": lam,
        "empty_fraction": p0,
        "single_fraction": p1,
        "multiple_fraction": p2plus,
    }


def format_calculation_summary(values: dict[str, float]) -> dict[str, str]:
    return {
        "液滴体積": f"{values['droplet_volume_pl']:.3g} pL",
        "平均封入数 λ": f"{values['lambda']:.3g}",
        "空液滴": f"{values['empty_fraction'] * 100:.1f}%",
        "1個封入": f"{values['single_fraction'] * 100:.1f}%",
        "2個以上": f"{values['multiple_fraction'] * 100:.1f}%",
    }
