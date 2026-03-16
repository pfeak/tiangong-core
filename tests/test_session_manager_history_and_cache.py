from pathlib import Path

from tiangong_core.session.manager import SessionManager


def test_session_manager_cache_and_history_alignment(tmp_path: Path):
    mgr = SessionManager(workspace=tmp_path)
    key = "cli:chat1"

    # 初次 get_history：无文件，返回空
    assert mgr.get_history(key) == []

    # 写入一轮对话：user -> assistant -> tool
    records = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello", "tool_calls": []},
        {"role": "tool", "tool_call_id": "call-1", "content": "ok"},
    ]
    mgr.append(key, records)

    # get_history 读取到 user 起始的完整序列
    h1 = mgr.get_history(key, max_messages=10)
    assert h1[0]["role"] == "user"
    assert h1[0]["content"] == "hi"

    # 再次调用 get_history 应该命中缓存，结果一致
    h2 = mgr.get_history(key, max_messages=10)
    assert h2 == h1


def test_session_manager_history_drops_orphan_tail(tmp_path: Path):
    mgr = SessionManager(workspace=tmp_path)
    key = "cli:chat2"

    # 构造尾部一个 content 为空且无 tool_calls 的 assistant，应被 get_history 丢弃
    records = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "assistant", "content": "", "tool_calls": []},
    ]
    mgr.append(key, records)

    h = mgr.get_history(key, max_messages=10)
    # 最后一条应为正常 assistant 消息
    assert h[-1]["content"] == "hello"
