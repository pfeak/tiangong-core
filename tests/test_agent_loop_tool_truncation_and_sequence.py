from dataclasses import dataclass
from typing import Any, List

from tiangong_core.agent.loop import AgentLoop
from tiangong_core.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from tiangong_core.session.manager import SessionManager
from pathlib import Path
from tiangong_core.skills.runtime import SkillsRuntime


@dataclass
class _DummyToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


class DummyProvider(LLMProvider):
    def __init__(self, responses: List[LLMResponse]) -> None:
        self._responses = responses
        self.calls: List[dict[str, Any]] = []

    def chat(self, *, messages, tools=None, model=None, tool_choice=None, reasoning_effort=None, generation=None):
        self.calls.append({"messages": messages, "tools": tools, "model": model})
        return self._responses.pop(0)


class DummySkills(SkillsRuntime):
    def __init__(self, output: str) -> None:
        super().__init__()
        self.output = output
        self.calls: List[dict[str, Any]] = []

    def get_definitions(self) -> list[dict[str, Any]]:
        return []

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        self.calls.append({"name": name, "arguments": arguments})
        return self.output


def make_session_manager(tmp_path: Path) -> SessionManager:
    return SessionManager(workspace=tmp_path)


def test_tool_result_truncation_and_persistence(tmp_path: Path):
    # 第一轮：模型要求调用单个工具
    tool_call = ToolCallRequest(id="call-1", name="tool-echo", arguments={"x": 1})
    provider = DummyProvider(
        responses=[
            LLMResponse(content=None, tool_calls=[tool_call]),
            # 第二轮：返回最终内容
            LLMResponse(content="final answer", tool_calls=[]),
        ]
    )
    long_output = "x" * 500
    skills = DummySkills(output=long_output)
    sessions = make_session_manager(tmp_path)

    loop = AgentLoop(
        provider=provider,
        skills=skills,
        sessions=sessions,
        model="dummy-model",
        max_iterations=2,
        tool_result_max_chars=100,
    )

    res = loop.process_direct(
        session_key="cli:chat-tool",
        system_prompt="sys",
        user_content="hi",
        runtime_metadata={"run_id": "r1", "agent_id": "a1"},
    )

    assert "final answer" in res.content

    # 会话历史中应存在 tool 消息，且带合法的 tool_call_id
    history = sessions.get_history("cli:chat-tool", max_messages=20)
    tool_msgs = [m for m in history if m.get("role") == "tool"]
    assert tool_msgs, "should persist tool messages"
    assert tool_msgs[0]["tool_call_id"] == "call-1"
    assert len(tool_msgs[0]["content"]) <= 100
    assert "[truncated]" in tool_msgs[0]["content"]


def test_assistant_with_tool_calls_is_persisted(tmp_path: Path):
    tool_call = ToolCallRequest(id="call-2", name="tool-echo", arguments={"x": 1})
    provider = DummyProvider(
        responses=[
            LLMResponse(content=None, tool_calls=[tool_call]),
            LLMResponse(content="done", tool_calls=[]),
        ]
    )
    skills = DummySkills(output="ok")
    sessions = make_session_manager(tmp_path)

    loop = AgentLoop(
        provider=provider,
        skills=skills,
        sessions=sessions,
        model="dummy-model",
        max_iterations=2,
        tool_result_max_chars=100,
    )

    loop.process_direct(
        session_key="cli:chat-assistant-tool",
        system_prompt="sys",
        user_content="hi",
        runtime_metadata={"run_id": "r2", "agent_id": "a2"},
    )

    history = sessions.get_history("cli:chat-assistant-tool", max_messages=20)
    assistant_msgs = [m for m in history if m.get("role") == "assistant"]
    # 至少包含一条带 tool_calls 的 assistant 消息
    assert any(m.get("tool_calls") for m in assistant_msgs)


class ErrorProvider(LLMProvider):
    def chat(self, *, messages, tools=None, model=None, tool_choice=None, reasoning_effort=None, generation=None):
        raise RuntimeError("400 Bad Request: invalid message sequence")


def test_agent_loop_short_circuits_on_provider_error(tmp_path: Path):
    provider = ErrorProvider()
    skills = DummySkills(output="ok")
    sessions = make_session_manager(tmp_path)

    loop = AgentLoop(
        provider=provider,
        skills=skills,
        sessions=sessions,
        model="dummy-model",
        max_iterations=2,
        tool_result_max_chars=100,
    )

    res = loop.process_direct(
        session_key="cli:chat-error",
        system_prompt="sys",
        user_content="hi",
        runtime_metadata={"run_id": "r3", "agent_id": "a3"},
    )

    # 返回可操作的错误提示
    assert "调用模型失败" in res.content
    assert "400 Bad Request" in res.content
    assert "/reset" in res.content

    # 历史中不应新增任何消息（meta 记录不计入 get_history）
    history = sessions.get_history("cli:chat-error", max_messages=20)
    assert history == []


def test_agent_loop_respects_stop_flag_and_persists_partial_turn(tmp_path: Path, monkeypatch) -> None:
    # 第一轮返回 tool_calls，第二轮本应返回最终内容，但在第二轮前触发 stop
    tool_call = ToolCallRequest(id="call-stop", name="tool-echo", arguments={"x": 1})
    provider = DummyProvider(
        responses=[
            LLMResponse(content=None, tool_calls=[tool_call]),
            LLMResponse(content="should-not-be-used", tool_calls=[]),
        ]
    )
    skills = DummySkills(output="ok")
    sessions = make_session_manager(tmp_path)

    loop = AgentLoop(
        provider=provider,
        skills=skills,
        sessions=sessions,
        model="dummy-model",
        max_iterations=2,
        tool_result_max_chars=100,
    )

    # 控制 SessionManager.is_stopped：首次调用返回 False，第二次返回 False，之后返回 True
    call_counts: dict[str, int] = {"n": 0}

    real_is_stopped = sessions.is_stopped

    def _fake_is_stopped(session_key: str) -> bool:
        call_counts["n"] += 1
        if call_counts["n"] <= 2:
            return False
        return True

    monkeypatch.setattr(sessions, "is_stopped", _fake_is_stopped)

    res = loop.process_direct(
        session_key="cli:chat-stop",
        system_prompt="sys",
        user_content="hi",
        runtime_metadata={"run_id": "r4", "agent_id": "a4"},
    )

    # 返回 stop 提示
    assert "已停止（/stop）。" in res.content

    # 恢复 is_stopped 以便后续调用
    monkeypatch.setattr(sessions, "is_stopped", real_is_stopped)

    history = sessions.get_history("cli:chat-stop", max_messages=20)
    roles = [m.get("role") for m in history]
    # 应该包含 user -> assistant(with tool_calls) -> tool 三条消息
    assert roles[0] == "user"
    assert "tool_calls" in history[1]
    assert history[1]["role"] == "assistant"
    assert history[2]["role"] == "tool"
