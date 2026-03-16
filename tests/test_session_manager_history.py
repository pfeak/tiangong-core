from pathlib import Path

from tiangong_core.session.manager import SessionManager


def make_session_manager(tmp_path: Path) -> SessionManager:
    return SessionManager(workspace=tmp_path)


def test_get_history_aligns_to_first_user_turn(tmp_path: Path):
    sessions = make_session_manager(tmp_path)
    key = "cli:chat-align"

    # 先写入一条 tool 消息，再写入 user/assistant，模拟“历史中以 tool 开头”的情况
    sessions.append(
        key,
        [
            {"role": "tool", "tool_call_id": "call-orphan", "content": "orphan"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "ok"},
        ],
    )

    history = sessions.get_history(key, max_messages=10)

    # 历史不应从 tool 开头，而是从第一条 user 开始
    assert history
    assert history[0]["role"] == "user"
    roles = [m["role"] for m in history]
    assert roles == ["user", "assistant"]


def test_get_history_drops_trailing_empty_assistant_without_tool_calls(tmp_path: Path):
    sessions = make_session_manager(tmp_path)
    key = "cli:chat-tail"

    sessions.append(
        key,
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "ok"},
            # 末尾一条 assistant，但 content 为空且无 tool_calls，应该被丢弃
            {"role": "assistant", "content": "", "tool_calls": []},
        ],
    )

    history = sessions.get_history(key, max_messages=10)

    assert history
    roles = [m["role"] for m in history]
    assert roles == ["user", "assistant"]
    assert history[-1]["content"] == "ok"


def test_get_history_ignores_non_message_meta_records(tmp_path: Path):
    sessions = make_session_manager(tmp_path)
    key = "cli:chat-meta"

    # append_meta 会写入一条无 role 的记录，应在 get_history 中被忽略
    sessions.append_meta(key, {"run_id": "r1", "metadata": {"agent_id": "a1"}})
    sessions.append(
        key,
        [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "ok"},
        ],
    )

    history = sessions.get_history(key, max_messages=10)

    assert history
    roles = [m["role"] for m in history]
    assert roles == ["user", "assistant"]


def test_get_history_returns_empty_when_no_user_turn(tmp_path: Path):
    sessions = make_session_manager(tmp_path)
    key = "cli:chat-nouser"

    # 只有 system 与 assistant，但没有 user，视为“无有效对话”
    sessions.append(
        key,
        [
            {"role": "system", "content": "sys"},
            {"role": "assistant", "content": "hi"},
        ],
    )

    history = sessions.get_history(key, max_messages=10)
    assert history == []
