from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.channels.base import BaseChannel
from tiangong_core.channels.config import ChannelsConfig
from tiangong_core.channels.feishu import FeishuChannel
from tiangong_core.channels.qq import QQChannel
from tiangong_core.channels.telegram import TelegramChannel


@dataclass(frozen=True)
class ChannelManagerStatus:
    enabled: list[str]


class ChannelManager:
    """
    outbound 转发器：监听 MessageBus.publish_outbound 的多播事件，
    将消息转发到对应 channel（slack/telegram/...）。
    """

    def __init__(self, *, bus: MessageBus, config: ChannelsConfig) -> None:
        self._bus = bus
        self._cfg = config
        self._channels: dict[str, BaseChannel] = {}

        self._q: queue.Queue[OutboundMessage] = queue.Queue(maxsize=1000)
        self._worker = threading.Thread(target=self._run, name="tiangong-channels", daemon=True)
        self._stopped = threading.Event()

        self._init_channels()
        self._bus.add_outbound_listener(self._on_outbound)
        self._worker.start()

    def _init_channels(self) -> None:
        if self._cfg.telegram.enabled:
            self._channels["telegram"] = TelegramChannel(config=self._cfg.telegram, bus=self._bus)
        if self._cfg.feishu.enabled:
            self._channels["feishu"] = FeishuChannel(config=self._cfg.feishu, bus=self._bus)
        if self._cfg.qq.enabled:
            self._channels["qq"] = QQChannel(config=self._cfg.qq, bus=self._bus)

        for ch in self._channels.values():
            try:
                ch.start()
            except Exception:
                continue

    def _on_outbound(self, msg: OutboundMessage) -> None:
        # 只处理已启用的 channel；不拦截 CLI/test 的队列消费。
        if msg.channel not in self._channels:
            return
        try:
            self._q.put_nowait(msg)
        except queue.Full:
            # 丢弃以保证不阻塞主流程
            return

    def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                msg = self._q.get(timeout=0.5)
            except queue.Empty:
                continue
            ch = self._channels.get(msg.channel)
            if not ch:
                continue
            try:
                r = ch.send(msg)
                if not getattr(r, "ok", True):
                    try:
                        print(f"[channels] send failed channel={msg.channel} chat_id={msg.chat_id} err={getattr(r, 'error', None)}")
                    except Exception:
                        pass
            except Exception:
                continue

    def stop(self) -> None:
        self._stopped.set()
        for ch in self._channels.values():
            try:
                ch.stop()
            except Exception:
                continue

    @property
    def enabled_channels(self) -> list[str]:
        return list(self._channels.keys())

    def status(self) -> ChannelManagerStatus:
        return ChannelManagerStatus(enabled=self.enabled_channels)

