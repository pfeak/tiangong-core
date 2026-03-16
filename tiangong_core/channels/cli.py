from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Tuple

from tiangong_core.bus.events import InboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.utils.ids import new_id


@dataclass(frozen=True)
class CLIChannelConfig:
    channel_name: str = "cli"
    allow_all: bool = True
    # 显式 allowlist：空/None 表示默认策略（由 allow_all 决定）；包含 "*" 表示放通所有 sender。
    allow_from: Tuple[str, ...] | None = None


class CLIChannel:
    def __init__(self, *, bus: MessageBus, config: CLIChannelConfig) -> None:
        self._bus = bus
        self._cfg = config

    def is_allowed(self, *, sender_id: str | None) -> bool:
        """
        基于 CLIChannelConfig 的简单 allowlist 判断：

        - allow_all=True：始终允许（兼容本地 CLI 的默认体验）
        - allow_all=False 且 allow_from 未配置/为空：全部拒绝
        - allow_from 包含 "*"：允许所有 sender
        - 否则仅允许 sender_id 在 allow_from 中的请求
        """
        if self._cfg.allow_all:
            return True

        allow_from = self._cfg.allow_from or ()
        if not allow_from:
            return False
        if "*" in allow_from:
            return True
        if sender_id is None:
            return False
        return sender_id in allow_from

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
