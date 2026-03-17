from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from tiangong_core.bus.events import InboundMessage, OutboundMessage
from tiangong_core.bus.queue import MessageBus


@dataclass(frozen=True)
class ChannelSendResult:
    ok: bool
    error: str | None = None


class BaseChannel(ABC):
    """
    tiangong-core 的 channel 抽象：当前版本以“发送 outbound 消息”为主。
    未来如需接入 inbound（webhook/ws 事件），可在各实现里扩展 start()/stop()。
    """

    name: str
    display_name: str

    def __init__(self, *, config: Any, bus: MessageBus | None = None) -> None:
        self.config = config
        self.bus = bus

    def start(self) -> None:
        return

    def stop(self) -> None:
        return

    def is_allowed(self, sender_id: str) -> bool:
        allow_from = getattr(self.config, "allow_from", ()) or ()
        if not allow_from:
            return False
        if "*" in allow_from:
            return True
        return str(sender_id) in set(str(x) for x in allow_from)

    def publish_inbound(
        self,
        *,
        chat_id: str,
        sender_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not self.bus:
            return
        if not self.is_allowed(sender_id):
            return
        self.bus.publish_inbound(
            InboundMessage(
                channel=self.name,
                chat_id=str(chat_id),
                content=str(content),
                session_key=f"{self.name}:{chat_id}",
                metadata=dict(metadata or {}, sender_id=str(sender_id)),
            )
        )

    @abstractmethod
    def send(self, msg: OutboundMessage) -> ChannelSendResult:
        raise NotImplementedError

