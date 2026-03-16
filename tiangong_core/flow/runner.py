from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List

from tiangong_core.flow.nodes import BaseNode
from tiangong_core.flow.nodes.chat import ChatNode
from tiangong_core.flow.nodes.tool_exec import ToolExecNode
from tiangong_core.flow.schemas import NodeResult


NodeFactory = Callable[[Dict[str, Any]], BaseNode]


@dataclass(frozen=True)
class FlowNodeSpec:
    """
    一个最小的节点规格描述，供 tiangong-research 以数据形式声明 Flow。
    """

    id: str
    type: str
    config: Dict[str, Any]


class FlowRunner:
    """
    PocketFlow glue：在 tiangong-core 中提供一个轻量级 Flow 执行器。

    v0.1 仅支持按顺序执行一组节点，不做图遍历/条件跳转。
    """

    def __init__(self, registry: Dict[str, NodeFactory] | None = None) -> None:
        builtins: Dict[str, NodeFactory] = {
            "chat": lambda cfg: ChatNode(**cfg),
            "tool_exec": lambda cfg: ToolExecNode(**cfg),
        }
        self._registry: Dict[str, NodeFactory] = {**builtins, **(registry or {})}

    def _make_node(self, type_name: str, config: Dict[str, Any]) -> BaseNode:
        factory = self._registry.get(type_name)
        if not factory:
            raise ValueError(f"unknown node type: {type_name}")
        return factory(config)

    def run(self, specs: Iterable[FlowNodeSpec], shared: Dict[str, Any] | None = None) -> List[NodeResult]:
        """
        顺序执行给定的节点列表。

        shared 作为跨节点的共享状态，节点的 prep/exec/post 都可以读写。
        """
        shared = shared or {}
        results: List[NodeResult] = []
        for spec in specs:
            node = self._make_node(spec.type, spec.config)
            prep_res = node.prep(shared)
            exec_res = node.exec(prep_res)
            results.append(exec_res)
            node.post(shared, prep_res, exec_res)
            if exec_res.status == "error":
                # 简单策略：遇到 error 即停止后续节点，交由上层决定是否重试。
                break
        return results


__all__ = ["FlowRunner", "FlowNodeSpec"]
