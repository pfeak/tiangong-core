from __future__ import annotations

import types
from typing import Any, Dict

import sys

from tiangong_core.providers.litellm_provider import LiteLLMProvider


class _DummyLiteLLMModule:
    def __init__(self) -> None:
        self.last_kwargs: Dict[str, Any] | None = None

    def completion(self, **kwargs: Any) -> Dict[str, Any]:
        self.last_kwargs = dict(kwargs)
        # minimal LiteLLM-like response
        return {
            "choices": [
                {
                    "message": {"role": "assistant", "content": "ok", "tool_calls": []},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }


def test_litellm_provider_drops_configured_params(monkeypatch) -> None:
    dummy = _DummyLiteLLMModule()
    sys.modules["litellm"] = dummy  # type: ignore[assignment]

    # env override：在默认 drop_params 之外再加一个自定义字段
    monkeypatch.setenv("TIANGONG_PROVIDER_DROP_PARAMS_OPENAI", "custom_param")

    provider = LiteLLMProvider(
        api_key="sk-123",
        api_base="https://my-gateway.example.com/v1/openai",
    )

    generation = {"temperature": 0.5, "top_p": 0.9, "max_tokens": 128}

    provider.chat(
        messages=[{"role": "user", "content": "hi"}],
        tools=None,
        model="gpt-4.1-mini",
        tool_choice=None,
        reasoning_effort="medium",
        generation=generation,
    )

    assert isinstance(dummy.last_kwargs, dict)

    # 正常字段应被保留
    assert dummy.last_kwargs["model"].endswith("gpt-4.1-mini")
    assert dummy.last_kwargs["temperature"] == 0.5
    assert dummy.last_kwargs["top_p"] == 0.9
    assert dummy.last_kwargs["max_tokens"] == 128

    # 默认 drop_params + env override 应被剔除
    for k in ("extra_headers", "cache_control", "reasoning_effort", "custom_param"):
        assert k not in dummy.last_kwargs
