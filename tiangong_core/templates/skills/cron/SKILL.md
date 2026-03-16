---
name: cron
description: Define cron-like scheduled jobs that trigger the agent using the cron.schedule skill. v0.1 records specs but does not execute real scheduling.
homepage: https://github.com/pfeak/tiangong-core
metadata: {"tiangong":{"emoji":"⏰","always":false}}
---

# Cron Skill (`cron.schedule`)

Use this skill to **describe scheduled jobs** that should run periodically and invoke the agent with a payload.  
In Tiangong v0.1 this API validates and records job specs, but does **not** yet start a real scheduler.

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
  "message": "cron.schedule 接口已注册，但当前版本仅记录参数，不执行实际调度。",
  "job": {
    "cron": "*/5 * * * *",
    "payload": { "...": "..." },
    "session_key": null
  }
}
```

## Notes

- Treat this as a **design-time** API in v0.1: it records and validates specs for future real scheduling.
- When real scheduling is added, the same shape should remain compatible so existing calls continue to work.
