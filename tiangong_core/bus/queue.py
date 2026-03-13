from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Condition

from .events import InboundMessage, OutboundMessage


@dataclass
class _Queue:
    items: deque
    cv: Condition


class MessageBus:
    def __init__(self) -> None:
        self._inbound = _Queue(deque(), Condition())
        self._outbound = _Queue(deque(), Condition())

    def publish_inbound(self, msg: InboundMessage) -> None:
        with self._inbound.cv:
            self._inbound.items.append(msg)
            self._inbound.cv.notify()

    def consume_inbound(self, timeout_s: float | None = None) -> InboundMessage | None:
        with self._inbound.cv:
            if not self._inbound.items:
                self._inbound.cv.wait(timeout=timeout_s)
            return self._inbound.items.popleft() if self._inbound.items else None

    def publish_outbound(self, msg: OutboundMessage) -> None:
        with self._outbound.cv:
            self._outbound.items.append(msg)
            self._outbound.cv.notify()

    def consume_outbound(self, timeout_s: float | None = None) -> OutboundMessage | None:
        with self._outbound.cv:
            if not self._outbound.items:
                self._outbound.cv.wait(timeout=timeout_s)
            return self._outbound.items.popleft() if self._outbound.items else None
