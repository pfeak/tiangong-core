from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, List

from tiangong_core.app import TiangongApp
from tiangong_core.bus.events import InboundMessage
from tiangong_core.bus.queue import InMemoryMessageBus
from tiangong_core.config import AppConfig, AgentConfig, ProviderConfig, ToolConfig
from tiangong_core.providers.base import LLMProvider, LLMResponse
from tiangong_core.session.manager import SessionManager


@dataclass
class _DummyToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


class DummyProvider(LLMProvider):
    """
    简单的假 Provider：忽略历史与 tools，直接返回固定回复。
    """

    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: List[dict[str, Any]] = []

    def chat(self, *, messages, tools=None, model=None, tool_choice=None, reasoning_effort=None, generation=None):
        self.calls.append({"messages": messages, "tools": tools, "model": model})
        return LLMResponse(content=self._content, tool_calls=[])


def test_minimal_e2e_turn_with_dummy_provider(tmp_path: Path, monkeypatch) -> None:
    """
    用 DummyProvider 跑通一轮 inbound→loop→outbound，验证最小闭环。
    """
    ws = tmp_path

    # 构造不依赖真实环境变量的 AppConfig
    cfg = AppConfig(
        provider=ProviderConfig(api_key=None, api_base=None),
        tools=ToolConfig(restrict_to_workspace=True, shell_timeout_s=1),
        agent=AgentConfig(agent_name="test-agent", model="dummy-model", workspace=ws),
    )

    app = TiangongApp(workspace=ws, config=cfg)

    # 注入 DummyProvider，避免 LiteLLM 依赖网络。
    dummy = DummyProvider(content="hello from dummy")
    app.provider = dummy  # type: ignore[attr-defined]

    # 使用 InMemoryMessageBus，便于直接消费 outbound。
    bus = InMemoryMessageBus()
    app.bus = bus  # type: ignore[assignment]
    app.sessions = SessionManager(workspace=ws)  # type: ignore[assignment]

    session_key = app.make_session_key(channel="cli", chat_id="chat1")
    inbound = InboundMessage(
        channel="cli",
        chat_id="chat1",
        content="hi",
        session_key=session_key,
        metadata={"run_id": "r-e2e"},
    )

    app.run_once(inbound)

    out = bus.consume_outbound(timeout_s=0.5)
    assert out is not None
    assert out.content == "hello from dummy"
    assert out.metadata.get("event") == "final"
