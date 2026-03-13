from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from tiangong_core.providers.base import LLMProvider
from tiangong_core.session.manager import SessionManager
from tiangong_core.tools.registry import ToolRegistry


def _truncate(s: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(s) <= max_chars:
        return s
    return s[: max(0, max_chars - 20)] + "\n…[truncated]\n"


ProgressCb = Callable[[str], None]


@dataclass(frozen=True)
class LoopResult:
    content: str
    run_id: str


class AgentLoop:
    def __init__(
        self,
        *,
        provider: LLMProvider,
        tools: ToolRegistry,
        sessions: SessionManager,
        model: str,
        max_iterations: int,
        tool_result_max_chars: int,
    ) -> None:
        self._provider = provider
        self._tools = tools
        self._sessions = sessions
        self._model = model
        self._max_iter = max_iterations
        self._tool_max = tool_result_max_chars

    def process_direct(
        self,
        *,
        session_key: str,
        system_prompt: str,
        user_content: str,
        runtime_metadata: dict[str, Any],
        progress: ProgressCb | None = None,
    ) -> LoopResult:
        history = self._sessions.get_history(session_key, max_messages=80)
        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(history)

        # runtime metadata 合并到单条 user message（metadata only）
        meta_blob = json.dumps(runtime_metadata, ensure_ascii=False)
        messages.append(
            {
                "role": "user",
                "content": f"<runtime_metadata>\n{meta_blob}\n</runtime_metadata>\n\n{user_content}",
            }
        )

        tool_defs = self._tools.get_definitions()
        run_id = str(runtime_metadata.get("run_id") or "")

        turn_records: list[dict[str, Any]] = []
        turn_records.append({"role": "user", "content": messages[-1]["content"], "metadata": runtime_metadata})

        for _i in range(max(1, self._max_iter)):
            resp = self._provider.chat_with_retry(messages=messages, tools=tool_defs, model=self._model)
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": resp.content or "",
            }
            if resp.tool_calls:
                assistant_msg["tool_calls"] = [
                    {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": json.dumps(c.arguments)}}
                    for c in resp.tool_calls
                ]
            messages.append(assistant_msg)
            # 重要：当返回 tool_calls 且 content 为空时，也必须把该 assistant 消息持久化，
            # 否则下一轮 history 会出现“tool 消息无对应 tool_calls”的非法序列，导致 provider 400。
            turn_records.append(assistant_msg)

            if not resp.tool_calls:
                # 某些 provider 可能返回 content=None 且无 tool_calls，避免 CLI 打印空行造成“无返回”的错觉
                if not resp.content:
                    final = "（未收到模型输出内容：content 为空，且无 tool_calls；请检查模型/Provider 配置或网络状态）"
                else:
                    final = resp.content
                self._sessions.append(session_key, turn_records)
                return LoopResult(content=final, run_id=run_id)

            for c in resp.tool_calls:
                if progress:
                    progress(f"[tool] {c.name}")
                out = self._tools.execute(c.name, c.arguments)
                out = _truncate(out, self._tool_max)
                tool_msg = {"role": "tool", "tool_call_id": c.id, "content": out}
                messages.append(tool_msg)
                turn_records.append(tool_msg)

        self._sessions.append(session_key, turn_records)
        return LoopResult(content="达到最大工具迭代次数，已停止。", run_id=run_id)
