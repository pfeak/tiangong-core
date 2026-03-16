from __future__ import annotations

from typing import Any, Protocol

from tiangong_core.flow.schemas import NodeResult


class BaseNode(Protocol):
    """
    PocketFlow 节点协议（v0.1）。

    仅约束最小接口形状，便于在 tiangong-research 中实现自定义节点。
    """

    def prep(self, shared: dict[str, Any]) -> Any:  # pragma: no cover - 协议本身不执行
        ...

    def exec(self, input_data: Any) -> NodeResult:  # pragma: no cover - 协议本身不执行
        ...

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: NodeResult) -> str:  # pragma: no cover
        ...


__all__ = ["BaseNode"]
