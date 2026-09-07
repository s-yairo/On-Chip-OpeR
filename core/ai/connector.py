"""Single application entry point for all AI requests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .base import AIProvider
from .models import AIResponse
from .providers import DummyAIProvider


class AIConnector:
    """Route every AI request through one provider-independent interface."""

    def __init__(
        self,
        provider: AIProvider | None,
        *,
        enabled: bool = True,
        provider_name: str = "dummy",
        configuration_error: str = "",
    ) -> None:
        self._provider = provider
        self.enabled = enabled
        self.provider_name = provider_name
        self.configuration_error = configuration_error

    @classmethod
    def from_feature_config(
        cls,
        config_path: Path,
        *,
        feature_id: str = "joint_ai",
    ) -> "AIConnector":
        """Build a connector from ``config/features.json`` without raising."""
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            features = raw.get("features", {}) if isinstance(raw, dict) else {}
            settings = features.get(feature_id, {}) if isinstance(features, dict) else {}
            if not isinstance(settings, dict):
                settings = {}
        except (OSError, json.JSONDecodeError) as exc:
            return cls(
                None,
                enabled=False,
                provider_name="",
                configuration_error=f"JointAI設定を読み込めませんでした: {exc}",
            )

        enabled = bool(settings.get("enabled", False))
        provider_name = str(settings.get("provider", "dummy")).strip().lower() or "dummy"
        try:
            provider = cls._build_provider(provider_name)
        except ValueError as exc:
            return cls(
                None,
                enabled=enabled,
                provider_name=provider_name,
                configuration_error=str(exc),
            )
        return cls(provider, enabled=enabled, provider_name=provider_name)

    @staticmethod
    def _build_provider(provider_name: str) -> AIProvider:
        if provider_name == "dummy":
            return DummyAIProvider()
        raise ValueError(f"未対応のJointAI接続先です: {provider_name}")

    def ask(self, question: str, context: Mapping[str, Any]) -> AIResponse:
        """Ask the configured provider and convert failures into safe responses."""
        question_text = str(question).strip()
        if not self.enabled:
            return AIResponse(
                success=False,
                text="JointAI機能は無効です。",
                provider=self.provider_name,
                model="",
                error_code="disabled",
            )
        if self._provider is None:
            return AIResponse(
                success=False,
                text=self.configuration_error or "JointAI接続先を初期化できませんでした。",
                provider=self.provider_name,
                model="",
                error_code="configuration_error",
            )
        if not question_text:
            return AIResponse(
                success=False,
                text="質問を入力してください。",
                provider=self.provider_name,
                model=getattr(self._provider, "model", ""),
                error_code="empty_question",
            )

        try:
            response = self._provider.ask(question_text, dict(context))
        except Exception:
            return AIResponse(
                success=False,
                text="JointAIから回答を取得できませんでした。通常の手順機能はそのまま利用できます。",
                provider=self.provider_name,
                model=getattr(self._provider, "model", ""),
                error_code="provider_error",
            )
        if not isinstance(response, AIResponse):
            return AIResponse(
                success=False,
                text="JointAIから正しい形式の回答を取得できませんでした。",
                provider=self.provider_name,
                model=getattr(self._provider, "model", ""),
                error_code="invalid_response",
            )
        return response
