---
name: spawn
description: Delegate long-running or specialized tasks to subagents using the spawn.subagent and spawn.cancel skills. v0.1 runs subagents asynchronously in-process.
homepage: https://github.com/pfeak/tiangong-core
metadata: {"tiangong":{"emoji":"🧩","always":false}}
---

# Spawn Skill (`spawn.*`)

Use this skill family when you need to **offload a subtask** to a subagent.  
In Tiangong v0.1, subagents are executed asynchronously inside the same process (background queue + agent loop).

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
  "message": "spawn.subagent 已创建子任务并投递到队列（异步执行）。",
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
  "message": "spawn.cancel 已请求取消（v0.1：若任务已开始执行，可能无法中断；未开始的任务会被跳过）。",
  "subagent_id": "the-id-you-passed"
}
```

In future versions this will be wired to a real subagent manager for cancellation.
