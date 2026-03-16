---
name: mcp
description: Bridge external MCP (Model Context Protocol) servers into Tiangong skills. v0.1 exposes the bridge but does not register concrete MCP-backed skills yet.
homepage: https://github.com/pfeak/tiangong-core
metadata: {"tiangong":{"emoji":"🌉","always":false}}
---

# MCP Skill Bridge (`mcp`)

This skill represents the **integration point with MCP servers** (Model Context Protocol).  
In Tiangong v0.1, the bridge is present but no concrete MCP-backed skills are registered yet.

## Concept

- MCP servers provide structured tools (for example, browsing, databases, external APIs).
- Tiangong will expose those tools to the model as skills, with schemas similar to other function-calling skills.
- This SKILL.md documents the intention and future behavior; the actual skill list will be populated dynamically when MCP servers are connected.

## Current behavior (v0.1)

- The `make_mcp_skills()` adapter returns an empty list.
- No concrete MCP methods are callable yet.
- You **should not** rely on MCP tools being available at this version.

## Future behavior (planned)

- When MCP servers are configured, `make_mcp_skills()` will:
  - Inspect available MCP tools.
  - Wrap them as Tiangong skills with appropriate JSON schemas.
  - Register them into `SkillsRuntime`, making them callable by the agent.

At that point, this SKILL.md should be updated with concrete examples of MCP-backed skills and usage patterns.
