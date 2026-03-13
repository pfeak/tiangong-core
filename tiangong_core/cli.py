from __future__ import annotations

import argparse
import logging
import threading
from pathlib import Path

from tiangong_core.app import TiangongApp
from tiangong_core.channels.cli import CLIChannel, CLIChannelConfig
from tiangong_core.config import load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="tiangong", description="tiangong-core")
    p.add_argument("-w", "--workspace", default=".", help="workspace path (default: .)")
    p.add_argument("-m", "--message", default=None, help="single message mode")
    p.add_argument("--chat-id", default="default", help="chat id (default: default)")
    return p


def main(argv: list[str] | None = None) -> int:
    # LiteLLM 会在启动/首次调用时尝试拉取远程 model cost map，网络差时会刷 WARNING。
    # 该告警不影响核心功能（会 fallback 到本地 backup），这里默认降噪到 ERROR。
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    args = build_parser().parse_args(argv)
    workspace = Path(args.workspace).resolve()
    cfg = load_config(workspace)
    app = TiangongApp(workspace=workspace, config=cfg)

    # agent loop 消费 inbound 并产出 outbound
    t = threading.Thread(target=app.serve_forever, daemon=True)
    t.start()

    channel = CLIChannel(bus=app.bus, config=CLIChannelConfig())

    if args.message:
        # 复用交互逻辑：投递后取一条 outbound 打印
        from tiangong_core.bus.events import InboundMessage

        session_key = f"cli:{args.chat_id}"
        app.bus.publish_inbound(
            InboundMessage(channel="cli", chat_id=args.chat_id, content=args.message, session_key=session_key, metadata={})
        )
        # 与交互模式一致：消费直到 final/error，避免 progress 消息抢先
        while True:
            out = app.bus.consume_outbound(timeout_s=120.0)
            if not out:
                print("[timeout] 未收到模型输出（120s）")
                break
            print(out.content)
            event = (out.metadata or {}).get("event")
            if event in ("final", "error"):
                break
        return 0

    channel.start_interactive(chat_id=args.chat_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
