from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    keywords: tuple[str, ...] = ()
    litellm_prefix: str | None = None
    detect_by_key_prefix: tuple[str, ...] = ()
    api_base_keywords: tuple[str, ...] = ()
    is_gateway: bool = False
    strip_model_prefix: bool = True


DEFAULT_SPECS: tuple[ProviderSpec, ...] = (
    ProviderSpec(name="openai", keywords=("openai", "gpt", "o1", "o3"), litellm_prefix="openai/"),
    ProviderSpec(name="anthropic", keywords=("anthropic", "claude"), litellm_prefix="anthropic/"),
    ProviderSpec(
        name="openai-compatible-gateway",
        keywords=("gateway", "openai-compatible"),
        detect_by_key_prefix=("sk-",),
        api_base_keywords=("openai", "v1"),
        is_gateway=True,
        litellm_prefix=None,
        strip_model_prefix=False,
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
