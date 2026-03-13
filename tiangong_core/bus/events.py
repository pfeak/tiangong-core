from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InboundMessage:
    channel: str
    chat_id: str
    content: str
    session_key: str
    metadata: dict[str, Any] = field(default_factory=dict)
    media: list[str] | None = None


@dataclass(frozen=True)
class OutboundMessage:
    channel: str
    chat_id: str
    content: str
    session_key: str
    metadata: dict[str, Any] = field(default_factory=dict)
