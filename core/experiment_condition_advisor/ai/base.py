"""Backend contract for closed experiment-advisor engines."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExperimentAdvisorBackend(ABC):
    @abstractmethod
    def generate_opinion(
        self,
        case_data: dict[str, Any],
        *,
        product_candidates: list[dict[str, str]],
        approved_sources: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Return a structured opinion without sending data outside the app."""
        raise NotImplementedError
