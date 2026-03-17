import pytest

from tiangong_core.bus.queue import InMemoryMessageBus
from tiangong_core.channels.cli import CLIChannel, CLIChannelConfig


class DummyBus(InMemoryMessageBus):
    """简单继承 InMemoryMessageBus，避免引入额外依赖。"""


@pytest.mark.parametrize(
    "allow_from,sender,expected",
    [
        ((), "user1", False),
        (("*",), "user1", True),
        (("user1",), "user1", True),
        (("user1",), "user2", False),
    ],
)
def test_cli_channel_allowlist_is_allowed(allow_from, sender, expected):
    cfg = CLIChannelConfig(allow_from=allow_from)
    ch = CLIChannel(bus=DummyBus(), config=cfg)
    assert ch.is_allowed(sender_id=sender) is expected
