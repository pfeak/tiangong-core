from __future__ import annotations

from typing import Any, Dict

from tiangong_core.flow.runner import FlowRunner, FlowNodeSpec
from tiangong_core.flow.schemas import NodeResult
from tiangong_core.flow.nodes import BaseNode


class _EchoNode:
    """用于测试自定义节点注册的简单节点。"""

    def __init__(self, prefix: str = "") -> None:
        self._prefix = prefix

    def prep(self, shared: Dict[str, Any]) -> str:
        return str(shared.get("text", ""))

    def exec(self, input_data: str) -> NodeResult:
        return NodeResult(status="ok", data={"echo": f"{self._prefix}{input_data}"})

    def post(self, shared: Dict[str, Any], prep_res: str, exec_res: NodeResult) -> str:
        shared["echo"] = exec_res.data
        return exec_res.status


def test_flow_runner_runs_builtin_nodes_sequentially() -> None:
    shared: Dict[str, Any] = {"input": "hello", "tool_call": {"name": "dummy", "arguments": {}}}

    # 使用默认注册的 chat 和 tool_exec 节点，主要验证 glue 的顺序执行与 shared 传递。
    runner = FlowRunner()
    specs = [
        FlowNodeSpec(id="chat", type="chat", config={"input_key": "input", "output_key": "chat_out"}),
    ]

    results = runner.run(specs, shared=shared)
    assert len(results) == 1
    assert results[0].status == "ok"
    assert "chat_out" in shared


def test_flow_runner_supports_custom_node_registry() -> None:
    shared: Dict[str, Any] = {"text": "world"}

    def make_echo(cfg: Dict[str, Any]) -> BaseNode:  # type: ignore[override]
        return _EchoNode(prefix=cfg.get("prefix", ""))

    runner = FlowRunner(registry={"echo": make_echo})
    specs = [FlowNodeSpec(id="n1", type="echo", config={"prefix": "hi-"})]

    results = runner.run(specs, shared=shared)
    assert len(results) == 1
    assert results[0].status == "ok"
    assert shared["echo"]["echo"] == "hi-world"
