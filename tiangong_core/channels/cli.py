from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tiangong_core.bus.events import InboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.utils.ids import new_id


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
        print("Tiangong CLI（输入 /exit 退出，/stop 停止该会话）")
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
                    metadata={"run_id": new_id(), "channel": self._cfg.channel_name, "chat_id": chat_id},
                )
            )

            # 等待并打印直到拿到最终消息（解决 progress/tool 输出先于 final 的情况）
            while True:
                out = self._bus.consume_outbound(timeout_s=120.0)
                if not out:
                    print("[timeout] 未收到模型输出（120s）")
                    break
                print(out.content)
                event = (out.metadata or {}).get("event")
                if event in ("final", "error"):
                    break
