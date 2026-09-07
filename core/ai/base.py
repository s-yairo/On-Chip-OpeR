"""Provider contract used by the JointAI connector."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Mapping

from .models import AIResponse


class AIProvider(ABC):
    """Common interface implemented by every AI connection provider."""

    name: str
    model: str

    @abstractmethod
    def ask(self, question: str, context: Mapping[str, Any]) -> AIResponse:
        """Return an answer without changing application state."""
