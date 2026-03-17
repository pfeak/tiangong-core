from __future__ import annotations

import json

from tiangong_core.bus.queue import MessageBus
from tiangong_core.channels.config import FeishuChannelConfig
from tiangong_core.channels.feishu import FeishuChannel


def test_feishu_url_verification_challenge() -> None:
    ch = FeishuChannel(config=FeishuChannelConfig(enabled=True), bus=MessageBus())
    resp = ch._handle_event({"type": "url_verification", "challenge": "abc"})  # type: ignore[attr-defined]
    assert resp == {"challenge": "abc"}


def test_feishu_event_callback_text_publishes_inbound() -> None:
    bus = MessageBus()
    cfg = FeishuChannelConfig(enabled=True, allow_from=("u1",), app_id="a", app_secret="s")
    ch = FeishuChannel(config=cfg, bus=bus)
    payload = {
        "type": "event_callback",
        "event": {
            "sender": {"sender_id": {"open_id": "u1"}},
            "message": {
                "chat_id": "c1",
                "message_id": "m1",
                "message_type": "text",
                "content": json.dumps({"text": "hi"}),
            },
        },
    }
    ch._handle_event(payload)  # type: ignore[attr-defined]
    m = bus.consume_inbound(timeout_s=0.1)
    assert m is not None
    assert m.channel == "feishu"
    assert m.chat_id == "c1"
    assert m.content == "hi"
    assert m.metadata.get("feishu_message_id") == "m1"


def test_feishu_socket_mode_p2_message_receive_publishes_inbound() -> None:
    bus = MessageBus()
    cfg = FeishuChannelConfig(enabled=True, mode="socket", allow_from=("u1",), app_id="a", app_secret="s")
    ch = FeishuChannel(config=cfg, bus=bus)
    payload = {
        "event": {
            "sender": {"sender_id": {"open_id": "u1"}},
            "message": {"chat_id": "c1", "message_id": "m2", "message_type": "text", "content": json.dumps({"text": "hello"})},
        }
    }
    ch._handle_p2_im_message_receive_v1(payload)  # type: ignore[attr-defined]
    m = bus.consume_inbound(timeout_s=0.1)
    assert m is not None
    assert m.channel == "feishu"
    assert m.chat_id == "c1"
    assert m.content == "hello"
    assert m.metadata.get("feishu_message_id") == "m2"


def test_feishu_react_emoji_alias_saluting_normalized() -> None:
    # Backward compatibility: "Saluting" is not a valid Feishu emoji_type; normalize it.
    assert FeishuChannel._normalize_react_emoji("Saluting") == "SaluteFace"  # type: ignore[attr-defined]

