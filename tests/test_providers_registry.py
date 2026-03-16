from tiangong_core.providers.registry import DEFAULT_SPECS, ProviderRegistry


def test_find_by_model_and_normalize_openai_prefix():
    registry = ProviderRegistry()

    # 已带 litellm 前缀的 model 应能直接识别 provider
    spec_prefixed = registry.find_by_model("openai/gpt-4.1")
    assert spec_prefixed is not None
    assert spec_prefixed.name == "openai"

    # 未带前缀的 model 应能按关键词识别并补全前缀
    spec_plain = registry.find_by_model("gpt-4.1")
    assert spec_plain is not None
    assert spec_plain.name == "openai"

    normalized = registry.normalize_model("gpt-4.1")
    assert normalized.startswith("openai/")
    assert normalized.endswith("gpt-4.1")


def test_find_by_model_anthropic():
    registry = ProviderRegistry()

    spec = registry.find_by_model("claude-3-opus")
    assert spec is not None
    assert spec.name == "anthropic"

    normalized = registry.normalize_model("anthropic/claude-3-opus")
    # 已带前缀时不应重复添加
    assert normalized == "anthropic/claude-3-opus"


def test_find_gateway_by_api_base_and_key_prefix():
    registry = ProviderRegistry(specs=DEFAULT_SPECS)

    # 同时命中 key 前缀与 api_base 关键词时，应识别为网关 provider
    spec = registry.find_gateway(
        api_base="https://my-gateway.example.com/v1/openai",
        api_key="sk-123456",
    )
    assert spec is not None
    assert spec.is_gateway is True
    assert spec.name == "openai-compatible-gateway"


def test_find_gateway_key_only_or_base_only():
    # 仅依赖 key 前缀也可以识别（当 api_base_keywords 为空时）
    # 这里通过构造一个只配 key 前缀、不配 api_base_keywords 的 spec 来验证逻辑
    from tiangong_core.providers.registry import ProviderSpec

    custom_specs = DEFAULT_SPECS + (
        ProviderSpec(
            name="key-only-gateway",
            detect_by_key_prefix=("key-",),
            api_base_keywords=(),
            is_gateway=True,
            strip_model_prefix=False,
        ),
    )
    reg2 = ProviderRegistry(specs=custom_specs)

    spec_key_only = reg2.find_gateway(api_base=None, api_key="key-xxx")
    assert spec_key_only is not None
    assert spec_key_only.name == "key-only-gateway"

    # 仅依赖 api_base 关键词也可以识别（当 detect_by_key_prefix 为空时）
    custom_specs2 = DEFAULT_SPECS + (
        ProviderSpec(
            name="base-only-gateway",
            detect_by_key_prefix=(),
            api_base_keywords=("my-gw",),
            is_gateway=True,
            strip_model_prefix=False,
        ),
    )
    reg3 = ProviderRegistry(specs=custom_specs2)

    spec_base_only = reg3.find_gateway(api_base="https://my-gw.example.com", api_key=None)
    assert spec_base_only is not None
    assert spec_base_only.name == "base-only-gateway"


def test_find_gateway_returns_none_when_not_matching():
    registry = ProviderRegistry(specs=DEFAULT_SPECS)

    spec = registry.find_gateway(api_base="https://api.other.com/v1", api_key="not-sk-xxx")
    assert spec is None
