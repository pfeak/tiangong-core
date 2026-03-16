from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class NodeResult:
    """
    PocketFlow 节点执行结果的最小形状。

    参考 PRD 3.11.2：
    - prep(shared) -> input
    - exec(input) -> NodeResult(status, data)
    - post(shared, prep_res, exec_res) -> next_status
    """

    status: str
    data: Dict[str, Any] | None = None
    message: str | None = None
