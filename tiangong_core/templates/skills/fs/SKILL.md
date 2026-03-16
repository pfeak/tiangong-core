---
name: fs
description: Read, write, edit, and list files and directories inside the current workspace using the fs.* skills.
homepage: https://github.com/pfeak/tiangong-core
metadata: {"tiangong":{"emoji":"📁"}}
---

# Filesystem Skill (`fs`)

Use this skill family when you need to **inspect or modify files and directories** in the current workspace.

## When to use

- Reading or skimming source files (`.py`, `.md`, `.json`, etc.).
- Writing new files or overwriting existing ones.
- Listing directory contents to understand project structure.
- Performing small, surgical edits inside a single file.

Avoid using shell commands like `cat`, `ls`, or `sed` for tasks that `fs.*` can do more safely and robustly.

## Available skills

- `fs.read` — Read a text file.
- `fs.write` — Write or overwrite a text file.
- `fs.edit` — Replace one occurrence of a string in a file.
- `fs.list` — List entries in a directory.

## fs.read

Read the contents of a text file.

```json
{
  "path": "relative/or/absolute/path"
}
```

The result includes:

- `path`: resolved absolute path.
- `content`: full file text.

Use this before making any edits. Do **not** assume file contents.

## fs.write

Create or overwrite a file with the given text content.

```json
{
  "path": "relative/or/absolute/path",
  "content": "full file contents"
}
```

The result includes:

- `path`: resolved absolute path.
- `bytes`: number of bytes written.

Use this when you want to replace an entire file (for example, when generating a new module or config).

## fs.edit

Perform a **single, surgical replacement** in an existing file.

```json
{
  "path": "relative/or/absolute/path",
  "old": "exact substring to replace (once)",
  "new": "replacement substring"
}
```

Behavior:

- Fails with `old_string_not_found` if `old` does not appear in the file.
- Only replaces the **first occurrence** of `old`.
- Returns a unified diff so you can verify the change.

Use this when you need precise, minimal edits (for example, updating one function call or a single config key).

## fs.list

List directory entries.

```json
{
  "path": "."        // optional; defaults to workspace root
}
```

The result includes:

- `path`: resolved directory path.
- `entries`: array of `{ "name", "is_dir", "size" }`.
Use this to explore project layout before deciding which files to open.
