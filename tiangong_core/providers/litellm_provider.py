from __future__ import annotations

import json
from typing import Any

from .base import LLMProvider, LLMResponse, ToolCallRequest
from .registry import ProviderRegistry


def _truncate(s: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(s) <= max_chars:
        return s
    return s[: max(0, max_chars - 20)] + "\n…[truncated]\n"


def _sanitize_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = {"role", "content", "name", "tool_call_id", "tool_calls"}
    out: list[dict[str, Any]] = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        mm = {k: v for k, v in m.items() if k in allowed}
        # 某些 provider 不接受 assistant content=None
        if mm.get("role") == "assistant" and mm.get("content") is None and not mm.get("tool_calls"):
            mm["content"] = ""
        out.append(mm)
    return out


def _coerce_mapping(obj: Any) -> dict[str, Any]:
    """
    LiteLLM 可能返回 pydantic/typed object（非 dict）作为 message/tool_calls。
    这里尽量把它们转成 dict，避免 tool_calls 被静默丢弃。
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    # pydantic v2
    if hasattr(obj, "model_dump"):
        try:
            d = obj.model_dump()  # type: ignore[attr-defined]
            return d if isinstance(d, dict) else {}
        except Exception:
            pass
    # pydantic v1
    if hasattr(obj, "dict"):
        try:
            d = obj.dict()  # type: ignore[attr-defined]
            return d if isinstance(d, dict) else {}
        except Exception:
            pass
    # generic objects
    try:
        d = dict(obj)  # type: ignore[arg-type]
        return d if isinstance(d, dict) else {}
    except Exception:
        pass
    try:
        d = vars(obj)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _parse_tool_calls(resp_message: dict[str, Any]) -> list[ToolCallRequest]:
    calls = resp_message.get("tool_calls") or []
    out: list[ToolCallRequest] = []
    for c in calls:
        cc = _coerce_mapping(c)
        fn = _coerce_mapping(cc.get("function"))
        name = fn.get("name") or cc.get("name")
        args_raw = fn.get("arguments") if "arguments" in fn else cc.get("arguments")
        if not name:
            continue
        try:
            if isinstance(args_raw, dict):
                args = args_raw
            else:
                args = json.loads(args_raw) if isinstance(args_raw, str) and args_raw.strip() else {}
        except Exception:
            args = {}
        out.append(ToolCallRequest(id=str(cc.get("id") or ""), name=str(name), arguments=args))
    return out


class LiteLLMProvider(LLMProvider):
    def __init__(self, *, api_key: str | None = None, api_base: str | None = None) -> None:
        self._api_key = api_key
        self._api_base = api_base
        self._registry = ProviderRegistry()

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
        try:
            from litellm import completion  # type: ignore
        except Exception as e:  # pragma: no cover
            raise ModuleNotFoundError(
                "缺少依赖 litellm。请在本项目环境中安装依赖后再运行："
                "例如 `uv sync` 或 `pip install -e .`"
            ) from e

        model_norm = self._registry.normalize_model(model or "")
        payload: dict[str, Any] = {
            "model": model_norm,
            "messages": _sanitize_messages(messages),
        }
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice

        # v0.1: 尽量少传参，避免拒参；generation 仅透传温度等常见字段
        if generation:
            for k in ("temperature", "top_p", "max_tokens"):
                if k in generation:
                    payload[k] = generation[k]

        if self._api_key:
            payload["api_key"] = self._api_key
        if self._api_base:
            payload["api_base"] = self._api_base

        # LiteLLM 对 reasoning_effort 支持因 provider 而异，v0.1 默认丢弃避免拒参
        _ = reasoning_effort

        resp = completion(**payload)
        choice0 = (resp.get("choices") or [{}])[0]
        msg = choice0.get("message") or {}
        content = msg.get("content")
        tool_calls = _parse_tool_calls(msg)
        finish_reason = choice0.get("finish_reason")
        usage = resp.get("usage") if isinstance(resp, dict) else None

        # 某些 provider 会返回思考块；v0.1 透传但不强依赖
        thinking_blocks = msg.get("thinking_blocks") if isinstance(msg, dict) else None
        reasoning_content = msg.get("reasoning_content") if isinstance(msg, dict) else None

        if isinstance(content, str):
            content = _truncate(content, 200_000)

        return LLMResponse(
            content=content if isinstance(content, str) else None,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage if isinstance(usage, dict) else None,
            reasoning_content=reasoning_content if isinstance(reasoning_content, str) else None,
            thinking_blocks=thinking_blocks if isinstance(thinking_blocks, list) else None,
        )
