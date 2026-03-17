from __future__ import annotations

import json
import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.channels.base import BaseChannel, ChannelSendResult
from tiangong_core.channels.config import FeishuChannelConfig
from tiangong_core.channels.http import http_post_json

logger = logging.getLogger(__name__)


class FeishuChannel(BaseChannel):
    name = "feishu"
    display_name = "Feishu/Lark"

    def __init__(self, *, config: FeishuChannelConfig, bus: MessageBus | None = None) -> None:
        super().__init__(config=config, bus=bus)
        self.config: FeishuChannelConfig
        self._tenant_token: str | None = None
        self._tenant_token_expire_at: float = 0.0
        self._server: HTTPServer | None = None
        self._server_thread: threading.Thread | None = None
        self._ws_thread: threading.Thread | None = None
        self._ws_client: Any | None = None

    def start(self) -> None:
        if not self.bus:
            return
        if self._server_thread or self._ws_thread:
            return

        mode = (self.config.mode or "webhook").strip().lower()
        if mode == "socket":
            self._start_socket_mode()
            return

        channel = self

        class _Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802
                try:
                    length = int(self.headers.get("Content-Length") or "0")
                except Exception:
                    length = 0
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    obj = json.loads(raw.decode("utf-8", errors="replace"))
                except Exception:
                    obj = {}

                resp: dict[str, Any] = {}
                try:
                    resp = channel._handle_event(obj)
                except Exception:
                    resp = {}

                body = json.dumps(resp or {}, ensure_ascii=False).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                # silence default http.server logs
                return

        def _run() -> None:
            addr = (self.config.webhook_host, int(self.config.webhook_port))
            self._server = HTTPServer(addr, _Handler)
            self._server.serve_forever()

        self._server_thread = threading.Thread(target=_run, name="tiangong-feishu-webhook", daemon=True)
        self._server_thread.start()

    def stop(self) -> None:
        # Stop webhook server if any
        if self._server:
            try:
                self._server.shutdown()
            except Exception:
                pass
            self._server = None

        # Best-effort stop for socket mode client (SDK-dependent)
        if self._ws_client is not None:
            try:
                stopper = getattr(self._ws_client, "stop", None)
                if callable(stopper):
                    stopper()
            except Exception:
                pass
            self._ws_client = None

    def send(self, msg: OutboundMessage) -> ChannelSendResult:
        if not (self.config.app_id and self.config.app_secret):
            return ChannelSendResult(ok=False, error="feishu app_id/app_secret is empty")
        chat_id = str(msg.chat_id or "").strip()
        if not chat_id:
            return ChannelSendResult(ok=False, error="feishu chat_id is empty (use OutboundMessage.chat_id)")

        token = self._get_tenant_access_token()
        if not token:
            return ChannelSendResult(ok=False, error="feishu failed to get tenant_access_token")

        # Prefer replying to the original message (引用/回复) when we have message_id from inbound.
        reply_to = ""
        try:
            reply_to = str((msg.metadata or {}).get("feishu_message_id") or "").strip()
        except Exception:
            reply_to = ""

        headers = {"Authorization": f"Bearer {token}"}
        # Feishu expects "content" as a JSON string for text messages, not an object.
        content = json.dumps({"text": msg.content}, ensure_ascii=False)
        if reply_to:
            # POST /im/v1/messages/:message_id/reply
            url = f"https://open.feishu.cn/open-apis/im/v1/messages/{reply_to}/reply"
            r = http_post_json(
                url=url,
                headers=headers,
                payload={
                    "msg_type": "text",
                    "content": content,
                    "reply_in_thread": bool(self.config.reply_in_thread),
                },
                timeout_s=10.0,
            )
        else:
            # POST /im/v1/messages?receive_id_type=chat_id
            url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
            r = http_post_json(
                url=url,
                headers=headers,
                payload={
                    "receive_id": chat_id,
                    "msg_type": "text",
                    "content": content,
                },
                timeout_s=10.0,
            )
        if not r.ok:
            logger.warning("feishu send failed status=%s err=%s body=%s", r.status, r.error, r.body)
        return ChannelSendResult(ok=r.ok, error=r.error or (None if r.ok else "http error"))

    def _start_socket_mode(self) -> None:
        if not (self.config.app_id and self.config.app_secret):
            logger.warning("feishu socket mode skipped: app_id/app_secret empty")
            return

        def _run() -> None:
            try:
                import lark_oapi as lark
            except Exception:
                logger.exception("feishu socket mode failed: lark-oapi import error")
                return

            logger.info("feishu starting socket mode client...")

            def _on_p2(data: Any) -> None:
                try:
                    raw = lark.JSON.marshal(data)
                    obj = json.loads(raw) if isinstance(raw, str) else {}
                except Exception:
                    obj = {}
                try:
                    self._handle_p2_im_message_receive_v1(obj)
                except Exception:
                    return

            # According to official docs, builder args MUST be empty strings for socket mode.
            handler = (
                lark.EventDispatcherHandler.builder("", "")
                .register_p2_im_message_receive_v1(_on_p2)
                .build()
            )

            kwargs: dict[str, Any] = {"event_handler": handler}
            try:
                # DEBUG is useful to see "connected to wss://..."
                kwargs["log_level"] = lark.LogLevel.DEBUG
            except Exception:
                pass

            try:
                cli = lark.ws.Client(self.config.app_id, self.config.app_secret, **kwargs)
                self._ws_client = cli
                cli.start()
            except Exception:
                logger.exception("feishu socket mode client crashed")
                return

        self._ws_thread = threading.Thread(target=_run, name="tiangong-feishu-socket", daemon=True)
        self._ws_thread.start()

    def _handle_event(self, obj: dict[str, Any]) -> dict[str, Any]:
        # basic verification token check (when configured)
        if self.config.verification_token:
            token = obj.get("token") or obj.get("verification_token")
            if token and token != self.config.verification_token:
                return {}

        t = obj.get("type")
        if t == "url_verification":
            return {"challenge": obj.get("challenge")}

        if t != "event_callback":
            return {}

        event = obj.get("event") or {}
        if not isinstance(event, dict):
            return {}

        sender_id, chat_id, message_id, msg_type, content_raw = self._extract_sender_message(event)
        if not sender_id or not chat_id:
            return {}

        self._process_inbound(
            sender_id=sender_id,
            chat_id=chat_id,
            message_id=message_id,
            msg_type=msg_type,
            content_raw=content_raw,
            metadata_base={"platform": "feishu"},
        )
        return {}

    def _handle_p2_im_message_receive_v1(self, obj: dict[str, Any]) -> None:
        """
        Handle Feishu Socket Mode v2.0 event: im.message.receive_v1.
        The SDK callback passes a typed object; we marshal it into a dict then parse here.
        """
        event = obj.get("event") if isinstance(obj.get("event"), dict) else obj
        if not isinstance(event, dict):
            return

        sender_id, chat_id, message_id, msg_type, content_raw = self._extract_sender_message(event)
        if not sender_id or not chat_id:
            return

        self._process_inbound(
            sender_id=sender_id,
            chat_id=chat_id,
            message_id=message_id,
            msg_type=msg_type,
            content_raw=content_raw,
            metadata_base={"platform": "feishu", "mode": "socket"},
        )

    def _extract_sender_message(self, event: dict[str, Any]) -> tuple[str, str, str, str, Any]:
        sender = (event.get("sender") or {}).get("sender_id") or {}
        if not isinstance(sender, dict):
            sender = {}
        sender_id = str(sender.get("open_id") or sender.get("user_id") or "")

        message = event.get("message") or {}
        if not isinstance(message, dict):
            message = {}
        chat_id = str(message.get("chat_id") or "")
        message_id = str(message.get("message_id") or "")
        msg_type = str(message.get("message_type") or message.get("msg_type") or "")
        content_raw: Any = message.get("content")
        return sender_id, chat_id, message_id, msg_type, content_raw

    def _extract_text(self, *, msg_type: str, content_raw: Any) -> str:
        if msg_type != "text":
            return ""
        if isinstance(content_raw, dict):
            return str(content_raw.get("text") or "")
        if isinstance(content_raw, str):
            try:
                cobj = json.loads(content_raw)
                if isinstance(cobj, dict):
                    return str(cobj.get("text") or "")
            except Exception:
                return ""
        return ""

    def _process_inbound(
        self,
        *,
        sender_id: str,
        chat_id: str,
        message_id: str,
        msg_type: str,
        content_raw: Any,
        metadata_base: dict[str, Any],
    ) -> None:
        text = self._extract_text(msg_type=msg_type, content_raw=content_raw).strip()
        if not text:
            return

        # quick ack: add reaction to the original message (best-effort)
        if message_id:
            try:
                self._react_to_message(message_id)
            except Exception:
                logger.debug("feishu react failed (ignored)", exc_info=True)

        metadata = dict(metadata_base)
        if message_id:
            metadata["feishu_message_id"] = message_id
        self.publish_inbound(chat_id=chat_id, sender_id=sender_id, content=text, metadata=metadata)

    def _react_to_message(self, message_id: str) -> None:
        """
        Add an emoji reaction to a given message_id so that users see
        an immediate acknowledgement when the agent receives a message.
        """
        mid = (message_id or "").strip()
        if not mid:
            return
        emoji = self._normalize_react_emoji(self.config.react_emoji)

        token = self._get_tenant_access_token()
        if not token:
            return

        url = f"https://open.feishu.cn/open-apis/im/v1/messages/{mid}/reactions"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {"reaction_type": {"emoji_type": emoji}}
        r = http_post_json(url=url, headers=headers, payload=payload, timeout_s=5.0)
        if not r.ok:
            logger.warning("feishu react failed status=%s err=%s body=%s", r.status, r.error, r.body)

    @staticmethod
    def _normalize_react_emoji(v: str | None) -> str:
        """
        Normalize user-friendly aliases to Feishu emoji_type.

        Common issue: users set "Saluting" but Feishu expects "SALUTE" or "SaluteFace".
        """
        s = (v or "").strip()
        if not s:
            return "SaluteFace"
        # Backward-compatible alias
        if s.lower() == "saluting":
            return "SaluteFace"
        return s

    def _get_tenant_access_token(self) -> str | None:
        now = time.time()
        if self._tenant_token and now < self._tenant_token_expire_at:
            return self._tenant_token
        r = http_post_json(
            url="https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            payload={"app_id": self.config.app_id, "app_secret": self.config.app_secret},
            timeout_s=10.0,
        )
        if not (r.ok and r.body):
            logger.warning("feishu tenant_access_token failed status=%s err=%s body=%s", r.status, r.error, r.body)
            return None
        try:
            obj = __import__("json").loads(r.body)
        except Exception:
            return None
        if not isinstance(obj, dict):
            return None
        if obj.get("code") not in (None, 0):
            logger.warning(
                "feishu tenant_access_token api error code=%s msg=%s raw=%s",
                obj.get("code"),
                obj.get("msg"),
                r.body,
            )
            return None
        token = obj.get("tenant_access_token")
        expire = obj.get("expire") or 0
        if not isinstance(token, str) or not token:
            return None
        try:
            exp_s = float(expire)
        except Exception:
            exp_s = 3600.0
        # 提前 60s 过期
        self._tenant_token = token
        self._tenant_token_expire_at = time.time() + max(60.0, exp_s - 60.0)
        return token

