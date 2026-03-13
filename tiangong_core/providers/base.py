from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCallRequest:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCallRequest]
    finish_reason: str | None = None
    usage: dict[str, Any] | None = None
    reasoning_content: str | None = None
    thinking_blocks: list[dict[str, Any]] | None = None


class LLMProvider:
    def chat(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        tool_choice: Any = None,
        reasoning_effort: str | None = None,
        generation: dict[str, Any] | None = None,
    ) -> LLMResponse:
        raise NotImplementedError

    def chat_with_retry(self, **kwargs: Any) -> LLMResponse:
        # v0.1: 简单直通；后续可加重试/退避/错误分类
        return self.chat(**kwargs)
