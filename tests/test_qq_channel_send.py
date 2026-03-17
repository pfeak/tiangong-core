from __future__ import annotations

import pytest

from tiangong_core.bus.events import OutboundMessage
from tiangong_core.channels.config import QQChannelConfig
from tiangong_core.channels.qq import QQChannel


class _FakeApi:
    def __init__(self) -> None:
        self.c2c_calls: list[dict] = []
        self.group_calls: list[dict] = []

    async def post_c2c_message(self, **kwargs) -> None:
        self.c2c_calls.append(kwargs)

    async def post_group_message(self, **kwargs) -> None:
        self.group_calls.append(kwargs)


class _FakeClient:
    def __init__(self) -> None:
        self.api = _FakeApi()


@pytest.mark.parametrize(
    "chat_id,chat_type,expect_group",
    [
        ("user123", "", False),
        ("c2c:user123", "", False),
        ("group:group123", "", True),
        ("group123", "group", True),
    ],
)
def test_qq_send_routes_to_correct_api(chat_id: str, chat_type: str, expect_group: bool) -> None:
    ch = QQChannel(config=QQChannelConfig(enabled=True, app_id="app", secret="secret"))
    ch._client = _FakeClient()  # type: ignore[assignment]

    msg = OutboundMessage(
        channel="qq",
        chat_id=chat_id,
        session_key="s1",
        content="hello",
        metadata={"message_id": "m1", **({"chat_type": chat_type} if chat_type else {})},
    )

    # 使用 asyncio.run 路径（没有后台 loop）
    res = ch.send(msg)
    assert res.ok is True

    api = ch._client.api  # type: ignore[union-attr]
    if expect_group:
        assert len(api.group_calls) == 1
        assert api.group_calls[0]["msg_type"] == 0
        assert api.group_calls[0]["content"] == "hello"
    else:
        assert len(api.c2c_calls) == 1
        assert api.c2c_calls[0]["msg_type"] == 0
        assert api.c2c_calls[0]["content"] == "hello"

