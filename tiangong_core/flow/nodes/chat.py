from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tiangong_core.flow.nodes import BaseNode
from tiangong_core.flow.schemas import NodeResult


@dataclass
class ChatNode(BaseNode):
    """
    最简单的 Chat 节点，占位实现。

    v0.1 中仅把 shared 中指定键的内容原样返回，便于在 tiangong-research 中
    用作“纯对话节点”或 report 节点的基础构件。
    """

    input_key: str = "input"
    output_key: str = "output"

    def prep(self, shared: dict[str, Any]) -> Any:
        return shared.get(self.input_key)

    def exec(self, input_data: Any) -> NodeResult:
        # 目前不直接调用 LLM，仅把输入包裹成 NodeResult
        return NodeResult(status="ok", data={"content": input_data})

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: NodeResult) -> str:
        shared[self.output_key] = exec_res.data
        return exec_res.status


__all__ = ["ChatNode"]
