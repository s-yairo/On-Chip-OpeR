"""Shared data models for JointAI requests and responses."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AIResponse:
    """Provider-independent result returned by :class:`AIConnector`."""

    success: bool
    text: str
    provider: str
    model: str
    error_code: str | None = None
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            object.__setattr__(
                self,
                "created_at",
                datetime.now(timezone.utc).isoformat(timespec="seconds"),
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
