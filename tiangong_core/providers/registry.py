from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    keywords: tuple[str, ...] = ()
    litellm_prefix: str | None = None
    # 依据 API key 前缀识别网关，例如 "sk-"
    detect_by_key_prefix: tuple[str, ...] = ()
    # 依据 api_base URL 关键词识别网关，例如 "openai", "v1"
    api_base_keywords: tuple[str, ...] = ()
    is_gateway: bool = False
    strip_model_prefix: bool = True
    # 针对该 provider/gateway 建议默认剔除的参数（避免拒参），例如 "reasoning_effort"、"extra_headers" 等。
    drop_params: tuple[str, ...] = ()


DEFAULT_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(
        name="openai",
        keywords=("openai", "gpt", "o1", "o3"),
        litellm_prefix="openai/",
        drop_params=("reasoning_effort", "extra_headers", "cache_control"),
    ),
    ProviderSpec(
        name="anthropic",
        keywords=("anthropic", "claude"),
        litellm_prefix="anthropic/",
        drop_params=("reasoning_effort", "extra_headers", "cache_control"),
    ),
    ProviderSpec(
        name="openai-compatible-gateway",
        keywords=("gateway", "openai-compatible"),
        detect_by_key_prefix=("sk-",),
        api_base_keywords=("openai", "v1"),
        is_gateway=True,
        litellm_prefix=None,
        strip_model_prefix=False,
        drop_params=("reasoning_effort", "extra_headers", "cache_control"),
    ),
)


class ProviderRegistry:
    def __init__(self, specs: tuple[ProviderSpec, ...] = DEFAULT_SPECS) -> None:
        self._specs = specs

    def find_by_model(self, model: str) -> ProviderSpec | None:
        m = (model or "").lower().strip()
        if not m:
            return None
        for s in self._specs:
            if s.litellm_prefix and m.startswith(s.litellm_prefix):
                return s
        for s in self._specs:
            if any(k in m for k in s.keywords):
                return s
        return None

    def normalize_model(self, model: str) -> str:
        spec = self.find_by_model(model)
        if not spec:
            return model
        if spec.litellm_prefix and not model.lower().startswith(spec.litellm_prefix):
            return f"{spec.litellm_prefix}{model}"
        return model

    def find_gateway(self, *, api_base: str | None, api_key: str | None) -> ProviderSpec | None:
        """
        基于 api_base + key 前缀/特征识别“网关”Provider。

        设计目标：
        - 只返回标记了 is_gateway=True 的 ProviderSpec
        - detect_by_key_prefix 命中其一即可（为空则忽略 key 维度）
        - api_base_keywords 只要有一个出现在 api_base 中即可（为空则忽略 api_base 维度）
        - 二者都配置时需同时命中，避免误判
        """
        base = (api_base or "").lower()
        key = api_key or ""

        for spec in self._specs:
            if not spec.is_gateway:
                continue

            # key 前缀匹配
            key_ok: bool
            if spec.detect_by_key_prefix:
                key_ok = any(key.startswith(prefix) for prefix in spec.detect_by_key_prefix if prefix)
            else:
                key_ok = True

            # api_base 关键词匹配
            base_ok: bool
            if spec.api_base_keywords:
                base_ok = any(k in base for k in spec.api_base_keywords if k)
            else:
                base_ok = True

            if key_ok and base_ok:
                return spec

        return None
