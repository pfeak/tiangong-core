from __future__ import annotations

import json
import threading
import time
import urllib.parse
import urllib.request
from typing import Any

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.channels.base import BaseChannel, ChannelSendResult
from tiangong_core.channels.config import TelegramChannelConfig
from tiangong_core.channels.http import http_post_json


class TelegramChannel(BaseChannel):
    name = "telegram"
    display_name = "Telegram"

    def __init__(self, *, config: TelegramChannelConfig, bus: MessageBus | None = None) -> None:
        super().__init__(config=config, bus=bus)
        self.config: TelegramChannelConfig
        self._poller: threading.Thread | None = None
        self._stopped = threading.Event()
        self._offset: int = 0

    def start(self) -> None:
        if self._poller or not self.bus:
            return
        if not self.config.token:
            return
        self._stopped.clear()
        self._poller = threading.Thread(target=self._poll_loop, name="tiangong-telegram", daemon=True)
        self._poller.start()

    def stop(self) -> None:
        self._stopped.set()

    def send(self, msg: OutboundMessage) -> ChannelSendResult:
        if not self.config.token:
            return ChannelSendResult(ok=False, error="telegram token is empty")
        chat_id = str(msg.chat_id or "").strip()
        if not chat_id:
            return ChannelSendResult(ok=False, error="telegram chat_id is empty (use OutboundMessage.chat_id)")
        url = f"https://api.telegram.org/bot{self.config.token}/sendMessage"
        r = http_post_json(
            url=url,
            payload={"chat_id": chat_id, "text": msg.content},
            timeout_s=10.0,
        )
        return ChannelSendResult(ok=r.ok, error=r.error or (None if r.ok else "http error"))

    def _poll_loop(self) -> None:
        # long polling: getUpdates?timeout=50&offset=...
        while not self._stopped.is_set():
            try:
                updates = self._get_updates(timeout_s=50)
                for u in updates:
                    try:
                        update_id = int(u.get("update_id") or 0)
                        if update_id >= self._offset:
                            self._offset = update_id + 1
                    except Exception:
                        pass
                    msg = u.get("message") or u.get("edited_message") or u.get("channel_post") or {}
                    if not isinstance(msg, dict):
                        continue
                    from_ = msg.get("from") or {}
                    chat = msg.get("chat") or {}
                    text = msg.get("text") or ""
                    if not isinstance(text, str) or not text.strip():
                        continue
                    sender_id = str(from_.get("id") or "")
                    chat_id = str(chat.get("id") or "")
                    if not sender_id or not chat_id:
                        continue
                    self.publish_inbound(chat_id=chat_id, sender_id=sender_id, content=text.strip(), metadata={"platform": "telegram"})
            except Exception:
                # avoid hot loop on transient errors
                time.sleep(1.0)

    def _get_updates(self, *, timeout_s: int) -> list[dict[str, Any]]:
        qs = {"timeout": str(timeout_s), "offset": str(self._offset)}
        url = f"https://api.telegram.org/bot{self.config.token}/getUpdates?{urllib.parse.urlencode(qs)}"
        req = urllib.request.Request(url=url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s + 5) as resp:  # noqa: S310
            body = resp.read().decode("utf-8", errors="replace")
        obj = json.loads(body)
        if not isinstance(obj, dict) or not obj.get("ok"):
            return []
        res = obj.get("result") or []
        return res if isinstance(res, list) else []

