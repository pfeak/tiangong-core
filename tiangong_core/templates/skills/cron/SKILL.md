---
name: cron
description: Define cron-like scheduled jobs that trigger the agent using the cron.schedule skill. v0.1 schedules in-process and triggers via the message bus.
homepage: https://github.com/pfeak/tiangong-core
metadata: {"tiangong":{"emoji":"⏰","always":false}}
---

# Cron Skill (`cron.schedule`)

Use this skill to create **in-process scheduled jobs** that run periodically and invoke the agent with a payload.  
In Tiangong v0.1, jobs are scheduled by a lightweight background thread inside the running process (no external service required).

## When to use

- Designing how cron-based workflows should look (for example, periodic repo scans, nightly tests).
- Recording schedule + payload specs for future implementation.

## API: cron.schedule

```json
{
  "cron": "*/5 * * * *",
  "payload": {
    "event": "nightly-tests",
    "workspace": "/path/to/workspace"
  },
  "session_key": "optional: explicit session key or null"
}
```

Parameters:

- `cron` (string, required): a standard 5-field cron expression, such as `"*/5 * * * *"` (every 5 minutes).
- `payload` (object, required): arbitrary JSON payload that will be passed back to the agent when the cron fires.
- `session_key` (string or null, optional): explicit session key to use when triggering; if omitted, a default routing strategy may be applied later.

Result structure:

```json
{
  "ok": true,
  "message": "cron.schedule 已创建任务；由本进程后台调度线程触发执行。",
  "job": {
    "job_id": "uuid",
    "cron": "*/5 * * * *",
    "payload": { "...": "..." },
    "session_key": null
  }
}
```

## Notes

- v0.1 的调度能力为“进程内后台线程”，适合本地/单进程运行场景；未来可替换为更可靠的持久化/分布式调度而保持接口形状兼容。
