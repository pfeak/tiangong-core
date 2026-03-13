from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tiangong_core.bus.events import InboundMessage
from tiangong_core.bus.queue import MessageBus


@dataclass(frozen=True)
class CLIChannelConfig:
    channel_name: str = "cli"
    allow_all: bool = True


class CLIChannel:
    def __init__(self, *, bus: MessageBus, config: CLIChannelConfig) -> None:
        self._bus = bus
        self._cfg = config

    def start_interactive(self, *, chat_id: str = "default") -> None:
        session_key = f"{self._cfg.channel_name}:{chat_id}"
        print("Tiangong CLI（输入 /exit 退出）")
        while True:
            try:
                s = input("> ").strip()
            except EOFError:
                break
            if not s:
                continue
            if s in ("/exit", "/quit"):
                break
            self._bus.publish_inbound(
                InboundMessage(
                    channel=self._cfg.channel_name,
                    chat_id=chat_id,
                    content=s,
                    session_key=session_key,
                    metadata={},
                )
            )

            # 等待一条输出并打印（v0.1 简化：1 in -> 1 out）
            out = self._bus.consume_outbound(timeout_s=120.0)
            if out:
                print(out.content)
