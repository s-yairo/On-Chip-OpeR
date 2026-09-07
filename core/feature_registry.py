"""Optional feature discovery.

The core application knows only a plugin ID and a manifest entry point. Optional
plugin packages can therefore be removed without importing plugin-specific code.
"""
from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class FeatureStatus:
    plugin_id: str
    display_name: str
    installed: bool
    enabled: bool
    available: bool
    mode: str
    state: str
    message: str
    manifest: dict[str, Any] = field(default_factory=dict)

    @property
    def badge(self) -> str:
        if self.mode == "development_preview" and self.available:
            return "開発プレビュー"
        if self.available:
            return "有効"
        if self.installed and self.state == "license_required":
            return "ライセンスが必要"
        return "未搭載"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def get_feature_status(base_dir: Path, plugin_id: str) -> FeatureStatus:
    """Return the current state without importing plugin code."""
    plugin_dir = base_dir / "plugins" / plugin_id
    manifest_path = plugin_dir / "plugin_manifest.json"
    config_path = base_dir / "config" / "features.json"

    if not manifest_path.is_file():
        return FeatureStatus(
            plugin_id=plugin_id,
            display_name=plugin_id,
            installed=False,
            enabled=False,
            available=False,
            mode="not_installed",
            state="not_installed",
            message="有料プラグインはこの配布物に含まれていません。",
        )

    manifest = _read_json(manifest_path)
    display_name = str(manifest.get("display_name") or plugin_id)
    config = _read_json(config_path).get("features", {})
    feature_config = config.get(plugin_id, {}) if isinstance(config, dict) else {}
    if not isinstance(feature_config, dict):
        feature_config = {}

    enabled = bool(feature_config.get("enabled", manifest.get("enabled_by_default", False)))
    mode = str(feature_config.get("mode", "disabled"))
    env_key = "ONCHIP_" + plugin_id.upper() + "_MODE"
    env_mode = os.getenv(env_key)
    if env_mode:
        mode = env_mode.strip().lower()

    if not enabled or mode == "disabled":
        return FeatureStatus(
            plugin_id=plugin_id,
            display_name=display_name,
            installed=True,
            enabled=False,
            available=False,
            mode=mode,
            state="disabled",
            message="有料プラグインは無効です。",
            manifest=manifest,
        )

    if mode in {"development_preview", "licensed"}:
        return FeatureStatus(
            plugin_id=plugin_id,
            display_name=display_name,
            installed=True,
            enabled=True,
            available=True,
            mode=mode,
            state="available",
            message=(
                "有料プラグインの開発プレビューです。"
                if mode == "development_preview"
                else "有料プラグインが有効です。"
            ),
            manifest=manifest,
        )

    return FeatureStatus(
        plugin_id=plugin_id,
        display_name=display_name,
        installed=True,
        enabled=True,
        available=False,
        mode=mode,
        state="license_required",
        message="有料プラグインの利用には有効なライセンスが必要です。",
        manifest=manifest,
    )


def render_feature(status: FeatureStatus, context: dict[str, Any]) -> None:
    """Load and render an available plugin through its manifest entry point."""
    if not status.available:
        raise RuntimeError(status.message)
    entrypoint = str(status.manifest.get("entrypoint", ""))
    if ":" not in entrypoint:
        raise RuntimeError("プラグインの entrypoint が正しくありません。")
    module_name, function_name = entrypoint.split(":", 1)
    importlib.invalidate_caches()
    module = importlib.import_module(module_name)
    renderer: Callable[..., Any] = getattr(module, function_name)
    renderer(context=context, feature_status=status)
