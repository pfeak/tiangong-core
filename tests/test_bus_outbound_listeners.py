from __future__ import annotations

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus


def test_outbound_listener_does_not_consume_queue() -> None:
    bus = MessageBus()
    seen: list[str] = []

    def on_out(msg: OutboundMessage) -> None:
        seen.append(msg.content)

    bus.add_outbound_listener(on_out)

    bus.publish_outbound(
        OutboundMessage(channel="cli", chat_id="c1", session_key="s1", content="hello", metadata={"event": "final"})
    )

    out = bus.consume_outbound(timeout_s=0.1)
    assert out is not None
    assert out.content == "hello"
    assert seen == ["hello"]

