import pytest

from tiangong_core.channels.cli import CLIChannelConfig, CLIChannel
from tiangong_core.bus.queue import InMemoryMessageBus


class DummyBus(InMemoryMessageBus):
    """简单继承 InMemoryMessageBus，避免引入额外依赖。"""


@pytest.mark.parametrize(
    "allow_all,allow_from,sender,expected",
    [
        (True, None, "user1", True),
        (True, (), "user1", True),
        (False, None, "user1", False),
        (False, (), "user1", False),
        (False, ("*",), "user1", True),
        (False, ("user1",), "user1", True),
        (False, ("user1",), "user2", False),
    ],
)
def test_cli_channel_allowlist_is_allowed(allow_all, allow_from, sender, expected):
    cfg = CLIChannelConfig(allow_all=allow_all, allow_from=allow_from)
    ch = CLIChannel(bus=DummyBus(), config=cfg)
    assert ch.is_allowed(sender_id=sender) is expected
