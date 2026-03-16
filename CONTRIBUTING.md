## 贡献指南

欢迎贡献！请遵循以下约定以保持仓库可维护性。

### 开发环境

- Python：3.10+（建议跟随 `.python-version`；若无该精确补丁版本，使用同一主次版本即可）
- 推荐使用 `uv`

安装依赖（含开发依赖）：

```bash
uv sync --dev
```

### 本地检查

提交前请确保：

```bash
uv run ruff check .
uv run mypy tiangong_core
uv run pytest -q
```

### 代码风格

- 保持改动小步、可回滚
- 避免无意义重排（除非一起引入格式化工具）
- 尽量减少“吞异常”，除非是明确的隔离边界（如第三方依赖、可选能力）

### 提交信息

建议使用清晰的动词开头（如 `fix:` / `feat:` / `refactor:` / `docs:` / `test:`）。
