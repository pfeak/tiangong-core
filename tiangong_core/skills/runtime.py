from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Executor = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class SkillFn:
    """
    可被模型 function-calling 调用的“技能函数”。

    v0.1 里它对应一个 function definition + 一个可执行器。
    """

    name: str
    description: str
    parameters: dict[str, Any]
    executor: Executor

    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class SkillsRuntime:
    """
    SkillsRuntime：统一的可调用能力入口（PRD 3.2.3）。

    - get_definitions(): 暴露给 provider 的 function calling schema
    - execute(name, arguments): 执行并返回可序列化字符串（写入 tool/skill_result）
    """

    def __init__(self) -> None:
        self._skills: dict[str, SkillFn] = {}

    def register(self, skill: SkillFn) -> None:
        self._skills[skill.name] = skill

    def get_definitions(self) -> list[dict[str, Any]]:
        return [s.definition() for s in self._skills.values()]

    def execute(self, name: str, arguments: dict[str, Any]) -> str:
        skill = self._skills.get(name)
        if not skill:
            return json.dumps({"ok": False, "error": f"unknown_skill: {name}"}, ensure_ascii=False)
        try:
            res = skill.executor(arguments or {})
            if isinstance(res, str):
                return res
            return json.dumps({"ok": True, "result": res}, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False)
