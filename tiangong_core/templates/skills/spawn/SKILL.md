---
name: spawn
description: Delegate long-running or specialized tasks to subagents using the spawn.subagent and spawn.cancel skills. v0.1 returns placeholder handles without real execution.
homepage: https://github.com/pfeak/tiangong-core
metadata: {"tiangong":{"emoji":"🧩","always":false}}
---

# Spawn Skill (`spawn.*`)

Use this skill family when you need to **conceptually offload a subtask** to a subagent.  
In Tiangong v0.1, these calls return placeholder handles but do **not** actually start background agents.

## Available skills

- `spawn.subagent` — create a subagent handle for a subtask.
- `spawn.cancel` — request cancellation of a subagent by ID.

## spawn.subagent

```json
{
  "parent_agent_id": "string, required",
  "name": "string, required",
  "payload": { "optional": "object" },
  "subtask_id": "optional string or null"
}
```

Parameters:

- `parent_agent_id`: the stable ID of the current agent (for example, from runtime metadata).
- `name`: logical name or description of the subagent (for example, `"repo-scanner"`).
- `payload`: optional free-form JSON describing the subtask inputs.
- `subtask_id`: optional ID to correlate logs/results for this subtask.

Result:

```json
{
  "ok": true,
  "message": "spawn.subagent 接口已注册，但当前版本仅返回占位句柄，不执行真实子任务。",
  "handle": {
    "subagent_id": "uuid",
    "parent_agent_id": "parent-id",
    "subtask_id": "optional-subtask-id"
  }
}
```

Use this when designing multi-agent workflows; store the returned `subagent_id` if you need to reference it later.

## spawn.cancel

```json
{
  "subagent_id": "string, required"
}
```

Result:

```json
{
  "ok": true,
  "message": "spawn.cancel 接口为占位实现，当前版本不会真正取消任务。",
  "subagent_id": "the-id-you-passed"
}
```

In future versions this will be wired to a real subagent manager for cancellation.
