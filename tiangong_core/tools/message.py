from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.tools.registry import Tool


@dataclass(frozen=True)
class MessageToolContext:
    bus: MessageBus
    channel: str
    chat_id: str
    session_key: str
    metadata: dict[str, Any]


def make_message_tools(ctx: MessageToolContext) -> list[Tool]:
    def send(args: dict[str, Any]) -> dict[str, Any]:
        content = str(args.get("content") or "")
        ctx.bus.publish_outbound(
            OutboundMessage(
                channel=ctx.channel,
                chat_id=ctx.chat_id,
                session_key=ctx.session_key,
                content=content,
                metadata=dict(ctx.metadata),
            )
        )
        return {"ok": True}

    schema = {
        "type": "object",
        "properties": {"content": {"type": "string"}},
        "required": ["content"],
    }
    return [Tool(name="message.send", description="Send a message to the current channel", parameters=schema, executor=send)]
