from __future__ import annotations

import asyncio
from collections import deque
from typing import Any

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.channels.base import BaseChannel, ChannelSendResult
from tiangong_core.channels.config import QQChannelConfig

try:
    import botpy

    QQ_AVAILABLE = True
except Exception:
    botpy = None
    QQ_AVAILABLE = False


class QQChannel(BaseChannel):
    name = "qq"
    display_name = "QQ"

    def __init__(self, *, config: QQChannelConfig, bus: MessageBus | None = None) -> None:
        super().__init__(config=config, bus=bus)
        self.config: QQChannelConfig
        self._client: Any | None = None
        self._msg_seq: int = 1
        self._chat_type_cache: dict[str, str] = {}
        self._loop: asyncio.AbstractEventLoop | None = None
        self._ready = asyncio.Event()
        self._processed_ids: deque[str] = deque(maxlen=1000)

    def send(self, msg: OutboundMessage) -> ChannelSendResult:
        if not self._client:
            self.start()
        if not self._client:
            return ChannelSendResult(ok=False, error="qq client not initialized (qq-botpy not installed?)")

        coro = self._send_async(msg)
        try:
            if self._loop and self._loop.is_running():
                fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
                fut.result(timeout=10.0)
            else:
                asyncio.run(coro)
            return ChannelSendResult(ok=True)
        except Exception as e:
            return ChannelSendResult(ok=False, error=f"{type(e).__name__}: {e}")

    def start(self) -> None:
        if self._client:
            return
        if not QQ_AVAILABLE:
            return
        if not (self.config.app_id and self.config.secret):
            return

        intents = botpy.Intents(public_messages=True, direct_message=True)
        ready_event = self._ready
        channel = self

        class _Bot(botpy.Client):
            async def on_ready(self) -> None:
                ready_event.set()

            async def on_c2c_message_create(self, message: Any) -> None:
                await channel._on_message(message, is_group=False)

            async def on_direct_message_create(self, message: Any) -> None:
                await channel._on_message(message, is_group=False)

            async def on_group_at_message_create(self, message: Any) -> None:
                await channel._on_message(message, is_group=True)

        self._client = _Bot(intents=intents, ext_handlers=False)

        import threading

        def _run() -> None:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def _main() -> None:
                client = self._client
                if client is None:
                    return
                await client.start(appid=self.config.app_id, secret=self.config.secret)

            self._loop.create_task(_main())
            try:
                self._loop.run_forever()
            finally:
                try:
                    self._loop.close()
                except Exception:
                    pass

        threading.Thread(target=_run, name="tiangong-qq-bot", daemon=True).start()

    def stop(self) -> None:
        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(self._loop.stop)
            except Exception:
                pass

    async def _send_async(self, msg: OutboundMessage) -> None:
        chat_id_raw = str(msg.chat_id or "").strip()
        if not chat_id_raw:
            raise ValueError("qq chat_id is empty (use OutboundMessage.chat_id)")

        chat_type = str((msg.metadata or {}).get("chat_type") or "").strip().lower()
        chat_id = chat_id_raw
        if chat_id_raw.startswith("group:"):
            chat_type = "group"
            chat_id = chat_id_raw.split(":", 1)[1]
        elif chat_id_raw.startswith("c2c:"):
            chat_type = "c2c"
            chat_id = chat_id_raw.split(":", 1)[1]
        if not chat_type:
            chat_type = self._chat_type_cache.get(chat_id, "c2c")

        api = getattr(self._client, "api", None)
        if not api:
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=10.0)
            except Exception:
                pass
            api = getattr(self._client, "api", None)
        if not api:
            raise RuntimeError("qq api not ready")

        self._msg_seq += 1
        msg_id = (msg.metadata or {}).get("message_id")
        if chat_type == "group":
            await api.post_group_message(
                group_openid=chat_id,
                msg_type=0,
                content=msg.content,
                msg_id=msg_id,
                msg_seq=self._msg_seq,
            )
        else:
            await api.post_c2c_message(
                openid=chat_id,
                msg_type=0,
                content=msg.content,
                msg_id=msg_id,
                msg_seq=self._msg_seq,
            )

    async def _on_message(self, data: Any, *, is_group: bool) -> None:
        # botpy message object has .id / .content and author fields
        msg_id = str(getattr(data, "id", "") or "")
        if msg_id and msg_id in self._processed_ids:
            return
        if msg_id:
            self._processed_ids.append(msg_id)

        content = str(getattr(data, "content", "") or "").strip()
        if not content:
            return

        if is_group:
            chat_id = str(getattr(data, "group_openid", "") or "")
            author = getattr(data, "author", None)
            sender_id = str(getattr(author, "member_openid", "") or "")
            if chat_id:
                self._chat_type_cache[chat_id] = "group"
        else:
            author = getattr(data, "author", None)
            sender_id = str(getattr(author, "id", "") or getattr(author, "user_openid", "") or "")
            chat_id = sender_id
            if chat_id:
                self._chat_type_cache[chat_id] = "c2c"

        if not (chat_id and sender_id):
            return

        self.publish_inbound(
            chat_id=chat_id,
            sender_id=sender_id,
            content=content,
            metadata={"platform": "qq", "message_id": msg_id, "chat_type": "group" if is_group else "c2c"},
        )

