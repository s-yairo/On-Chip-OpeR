"""Offline fixed-response provider used for the first JointAI implementation."""
from __future__ import annotations

from typing import Any, Mapping

from ..base import AIProvider
from ..models import AIResponse


class DummyAIProvider(AIProvider):
    """Return a fixed response without network access or external dependencies."""

    name = "dummy"
    model = "fixed-response"
    FIXED_RESPONSE = "これはテストです"

    def ask(self, question: str, context: Mapping[str, Any]) -> AIResponse:
        del question, context
        return AIResponse(
            success=True,
            text=self.FIXED_RESPONSE,
            provider=self.name,
            model=self.model,
        )
