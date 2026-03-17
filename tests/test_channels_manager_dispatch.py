from __future__ import annotations

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.channels.base import BaseChannel, ChannelSendResult
from tiangong_core.channels.config import ChannelsConfig, TelegramChannelConfig
from tiangong_core.channels.manager import ChannelManager


class _DummyTelegram(BaseChannel):
    name = "telegram"
    display_name = "Telegram"

    def __init__(self, *, config, bus=None) -> None:  # type: ignore[no-untyped-def]
        super().__init__(config=config, bus=bus)
        self.sent: list[str] = []

    def send(self, msg: OutboundMessage) -> ChannelSendResult:
        self.sent.append(msg.content)
        return ChannelSendResult(ok=True)


def test_channel_manager_dispatches_to_enabled_channel(monkeypatch) -> None:
    # 将 manager 内部引用的 TelegramChannel 替换为 dummy，避免真实网络发送。
    import tiangong_core.channels.manager as mgr

    monkeypatch.setattr(mgr, "TelegramChannel", _DummyTelegram)

    bus = MessageBus()
    cfg = ChannelsConfig(telegram=TelegramChannelConfig(enabled=True, token="dummy"))
    cm = ChannelManager(bus=bus, config=cfg)

    bus.publish_outbound(OutboundMessage(channel="telegram", chat_id="c1", session_key="s1", content="ping", metadata={}))

    # 异步 worker 线程处理：简单轮询等待一小会儿
    import time

    t0 = time.time()
    while time.time() - t0 < 1.0:
        ch = getattr(cm, "_channels", {}).get("telegram")
        if ch and getattr(ch, "sent", None) == ["ping"]:
            break
        time.sleep(0.01)

    ch = getattr(cm, "_channels", {}).get("telegram")
    assert ch is not None
    assert getattr(ch, "sent", None) == ["ping"]

