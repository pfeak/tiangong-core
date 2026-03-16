from __future__ import annotations

import logging
import os
import subprocess
import threading
from collections.abc import Callable
from pathlib import Path

import click
import typer
from prompt_toolkit import PromptSession, print_formatted_text
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.patch_stdout import patch_stdout
from rich.console import Console
from rich.markdown import Markdown
from rich.text import Text

from tiangong_core.agent.skills import SkillsLoader
from tiangong_core.app import TiangongApp
from tiangong_core.channels.cli import CLIChannel, CLIChannelConfig
from tiangong_core.config import load_config
from tiangong_core.utils.ids import new_id

app = typer.Typer(
    name="tiangong",
    help="tiangong-core",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
skills_app = typer.Typer(name="skills", help="skills management")
app.add_typer(skills_app, name="skills")

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/exit", "/quit", ":q"}


def _history_path(workspace: Path) -> Path:
    # 放到 workspace/runtime 下，便于跟随 workspace 迁移；不存在则创建目录。
    p = (workspace / "runtime" / "cli_history.txt").resolve()
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _render_ansi(render_fn: Callable[[Console], None]) -> str:
    ansi_console = Console(
        force_terminal=True,
        # 交由 Rich 自行探测，避免类型标注不一致引发的静态检查噪音
        color_system=None,
        width=console.width,
    )
    with ansi_console.capture() as capture:
        render_fn(ansi_console)
    return capture.get()


def _pt_print(render_fn: Callable[[Console], None]) -> None:
    ansi = _render_ansi(render_fn)
    print_formatted_text(ANSI(ansi), end="")


def _is_exit_command(s: str) -> bool:
    return (s or "").strip().lower() in EXIT_COMMANDS


@skills_app.command("list", help="List all available skills in the workspace")
def skills_list(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="workspace path (default: .)"),
) -> None:
    ws = workspace.resolve()
    loader = SkillsLoader(workspace=ws)
    for s in loader.list_skills():
        title = s.title or s.name
        always = " (always)" if s.always else ""
        desc = f" — {s.description}" if s.description else ""
        console.print(f"- [cyan]{s.name}[/cyan]: {title}{always}{desc} [dim][{s.source}][/dim]")


@skills_app.command("summary", help="Show a summary of skills and always-on skills")
def skills_summary(
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="workspace path (default: .)"),
) -> None:
    ws = workspace.resolve()
    loader = SkillsLoader(workspace=ws)
    console.print(loader.build_skills_summary() or "")
    always = loader.load_skills_for_context(loader.get_always_skills())
    if always:
        console.print()
        console.print(always)


@skills_app.command("show", help="Show detailed information for a specific skill")
def skills_show(
    name: str = typer.Argument(..., help="skill name"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="workspace path (default: .)"),
) -> None:
    ws = workspace.resolve()
    loader = SkillsLoader(workspace=ws)
    s_map = {s.name: s for s in loader.list_skills()}
    if name not in s_map:
        raise typer.Exit(code=2)
    console.print(loader.load_skills_for_context([name]) or "")


@skills_app.command("install", help="Install or update skills using clawhub")
def skills_install(
    names: list[str] = typer.Argument(
        None,
        help="optional skill names to install/update (default: interactive or as defined by clawhub)",
    ),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="workspace path (default: .)"),
    update: bool = typer.Option(False, "--update", help="use clawhub update instead of install"),
) -> None:
    """
    Wrap `npx clawhub@latest install/update` so that users can either:
    - run without names (delegating to clawhub's own behavior), or
    - specify one or more skill names, e.g.:
        tiangong skills install self-improving-agent other-skill
    """
    ws = workspace.resolve()
    cmd = "update" if update else "install"
    argv = ["npx", "clawhub@latest", cmd]
    if names:
        argv.extend(names)
    argv.extend(["--workdir", str(ws)])

    def read_output(pipe, is_stderr=False):
        """实时读取并打印输出"""
        try:
            for line in iter(pipe.readline, ''):
                if line:
                    if is_stderr:
                        console.print(f"[yellow]{line.rstrip()}[/yellow]")
                    else:
                        console.print(line.rstrip())
        finally:
            pipe.close()

    try:
        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        # 创建线程实时读取输出
        stdout_thread = threading.Thread(target=read_output, args=(process.stdout, False))
        stderr_thread = threading.Thread(target=read_output, args=(process.stderr, True))

        stdout_thread.start()
        stderr_thread.start()

        # 等待进程完成
        returncode = process.wait()

        # 等待输出线程完成
        stdout_thread.join()
        stderr_thread.join()

        raise typer.Exit(code=int(returncode or 0))
    except FileNotFoundError:
        console.print("[red][error][/red] 未找到 npx。请先安装 Node.js，或手动把技能放入 workspace/skills/<name>/SKILL.md")
        raise typer.Exit(code=127)


@app.command("agent", help="Chat with Tiangong agent in CLI")
def agent(
    message: str | None = typer.Option(None, "--message", "-m", help="single message mode"),
    workspace: Path = typer.Option(Path("."), "--workspace", "-w", help="workspace path (default: .)"),
    chat_id: str = typer.Option("default", "--chat-id", help="chat id (default: default)"),
    markdown: bool = typer.Option(True, "--markdown/--no-markdown", help="render assistant output as Markdown"),
) -> None:
    # LiteLLM 会在启动/首次调用时尝试拉取远程 model cost map，网络差时会刷 WARNING。
    # 该告警不影响核心功能（会 fallback 到本地 backup），这里默认降噪到 ERROR。
    logging.getLogger("LiteLLM").setLevel(logging.ERROR)

    ws = workspace.resolve()
    cfg = load_config(ws)
    core = TiangongApp(workspace=ws, config=cfg)

    # 将本地 CLI 封装为 CLIChannel，并在入口做 sender 级 ACL 校验。
    # 默认 allow_all=True，保证开箱即用；用户可通过配置/环境变量自定义 allow_from。
    cli_cfg = CLIChannelConfig()
    cli_channel = CLIChannel(bus=core.bus, config=cli_cfg)

    # agent loop 消费 inbound 并产出 outbound
    t = threading.Thread(target=core.serve_forever, daemon=True)
    t.start()

    from tiangong_core.bus.events import InboundMessage

    # session_key 由 TiangongApp 统一生成，支持 A/B 方案切换。
    session_key = core.make_session_key(channel="cli", chat_id=chat_id)

    # sender_id：本地 CLI 默认使用当前登录用户或 "local-cli"
    sender_id = os.getenv("TIANGONG_CLI_SENDER") or os.getenv("USER") or "local-cli"

    def _print_response_block(content: str) -> None:
        def _render(c: Console) -> None:
            body = Markdown(content or "") if markdown else Text(content or "")
            c.print()
            c.print("[cyan]tiangong[/cyan]")
            c.print(body)
            c.print()

        _pt_print(_render)

    def _print_progress_line(content: str) -> None:
        _pt_print(lambda c: c.print(f"  [dim]↳ {content}[/dim]"))

    def _run_one_turn(user_text: str) -> None:
        if not cli_channel.is_allowed(sender_id=sender_id):
            _print_progress_line(f"[denied] sender '{sender_id}' is not allowed by CLIChannel allowlist")
            return
        run_id = new_id()
        core.bus.publish_inbound(
            InboundMessage(
                channel="cli",
                chat_id=chat_id,
                content=user_text,
                session_key=session_key,
                metadata={"run_id": run_id, "channel": "cli", "chat_id": chat_id, "sender_id": sender_id},
            )
        )
        # 消费直到 final/error；progress 直接行输出
        while True:
            out = core.bus.consume_outbound(timeout_s=120.0)
            if not out:
                _print_progress_line("[timeout] 未收到模型输出（120s）")
                break
            event = (out.metadata or {}).get("event")
            if event == "progress":
                if out.content:
                    _print_progress_line(out.content)
                continue
            _print_response_block(out.content)
            if event in ("final", "error"):
                break

    if message is not None:
        with patch_stdout():
            _run_one_turn(message)
        return

    # interactive
    hist = FileHistory(str(_history_path(ws)))
    session: PromptSession[str] = PromptSession(history=hist, multiline=False, enable_open_in_editor=False)
    console.print("tiangong CLI（输入 exit 退出；/stop 停止该会话）")
    with patch_stdout():
        while True:
            try:
                with patch_stdout():
                    s = session.prompt(HTML("<b fg='ansiblue'>You:</b> "))
            except (EOFError, KeyboardInterrupt):
                console.print("\nGoodbye!")
                break
            text = (s or "").strip()
            if not text:
                continue
            if _is_exit_command(text):
                console.print("Goodbye!")
                break
            _run_one_turn(text)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        import sys

        argv = sys.argv[1:]
    try:
        app(standalone_mode=False, prog_name="tiangong", args=argv)
    except typer.Exit as e:
        return int(e.exit_code or 0)
    except click.ClickException as e:
        # Click/Typer usage errors (e.g. NoArgsIsHelp, NoSuchOption).
        # When using standalone_mode=False，需要手动输出错误/帮助信息，
        # 否则用户只能看到非零退出码而没有任何提示。
        try:
            e.show()  # 打印 usage + 错误信息到 stderr
        except Exception:
            # show() 理论上很少失败，兜底打印一行错误文案
            console.print(f"[red]{e.format_message() if hasattr(e, 'format_message') else str(e)}[/red]")
        # 仍然只返回 exit code，避免 traceback。
        return int(getattr(e, "exit_code", 1) or 1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
