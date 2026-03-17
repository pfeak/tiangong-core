from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.bus.queue import MessageBus
from tiangong_core.skills.runtime import SkillFn


@dataclass(frozen=True)
class MessageSkillContext:
    bus: MessageBus
    channel: str
    chat_id: str
    session_key: str
    metadata: dict[str, Any]


def make_message_skills(ctx: MessageSkillContext) -> list[SkillFn]:
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

    def send_to(args: dict[str, Any]) -> dict[str, Any]:
        channel = str(args.get("channel") or "").strip()
        chat_id = str(args.get("chat_id") or "").strip()
        content = str(args.get("content") or "")
        if not channel or not chat_id:
            return {"ok": False, "error": "channel/chat_id required"}
        ctx.bus.publish_outbound(
            OutboundMessage(
                channel=channel,
                chat_id=chat_id,
                session_key=f"{channel}:{chat_id}",
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
    schema_send_to = {
        "type": "object",
        "properties": {
            "channel": {"type": "string", "description": "target channel name (e.g. slack/telegram/feishu)"},
            "chat_id": {"type": "string", "description": "target chat id (platform-specific)"},
            "content": {"type": "string"},
        },
        "required": ["channel", "chat_id", "content"],
    }
    return [
        SkillFn(
            name="message.send",
            description="Send a message to the current channel",
            parameters=schema,
            executor=send,
        ),
        SkillFn(
            name="message.send_to",
            description="Send a message to a specified channel/chat_id",
            parameters=schema_send_to,
            executor=send_to,
        ),
    ]


__all__ = ["MessageSkillContext", "make_message_skills"]

