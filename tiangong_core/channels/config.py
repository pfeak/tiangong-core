from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelsCommonConfig:
    enabled: bool = False
    allow_from: tuple[str, ...] = ()


@dataclass(frozen=True)
class CLIChannelConfig(ChannelsCommonConfig):
    channel_name: str = "cli"


@dataclass(frozen=True)
class TelegramChannelConfig(ChannelsCommonConfig):
    token: str = ""
    proxy: str | None = None
    reply_to_message: bool = False


@dataclass(frozen=True)
class FeishuChannelConfig(ChannelsCommonConfig):
    # mode:
    # - "webhook": run a local HTTP server to receive Feishu event callbacks
    # - "socket": use Feishu Socket Mode (WebSocket long connection) via lark-oapi SDK
    mode: str = "webhook"
    app_id: str = ""
    app_secret: str = ""
    encrypt_key: str = ""
    verification_token: str = ""
    # Default acknowledgement reaction emoji for inbound messages.
    # Feishu emoji_type examples: "SaluteFace", "SALUTE", "THUMBSUP"
    react_emoji: str = "SaluteFace"
    # When replying to a message_id, whether to reply in thread/topic.
    reply_in_thread: bool = False
    webhook_host: str = "0.0.0.0"
    webhook_port: int = 18791
    webhook_path: str = "/feishu/events"


@dataclass(frozen=True)
class QQChannelConfig(ChannelsCommonConfig):
    app_id: str = ""
    secret: str = ""


@dataclass(frozen=True)
class ChannelsConfig:
    cli: CLIChannelConfig = CLIChannelConfig(enabled=True, allow_from=("*",))
    telegram: TelegramChannelConfig = TelegramChannelConfig()
    feishu: FeishuChannelConfig = FeishuChannelConfig()
    qq: QQChannelConfig = QQChannelConfig()

