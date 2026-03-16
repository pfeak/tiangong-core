import pytest

from tiangong_core.providers.registry import DEFAULT_SPECS, ProviderRegistry, ProviderSpec


def test_find_gateway_by_api_base_and_key_prefix():
    specs = DEFAULT_SPECS + (
        ProviderSpec(
            name="custom-gateway",
            detect_by_key_prefix=("gw-",),
            api_base_keywords=("gateway.example.com",),
            is_gateway=True,
        ),
    )
    reg = ProviderRegistry(specs=specs)

    spec = reg.find_gateway(api_base="https://gateway.example.com/v1", api_key="gw-123")
    assert spec is not None
    assert spec.name == "custom-gateway"


@pytest.mark.parametrize(
    "api_base,api_key",
    [
        ("https://gateway.example.com/v1", "sk-xxx"),  # key 前缀不匹配
        ("https://other.example.com/v1", "gw-xxx"),  # base 关键词不匹配
        (None, "gw-xxx"),
        ("https://gateway.example.com/v1", None),
    ],
)
def test_find_gateway_mismatch(api_base, api_key):
    specs = (
        ProviderSpec(
            name="custom-gateway",
            detect_by_key_prefix=("gw-",),
            api_base_keywords=("gateway.example.com",),
            is_gateway=True,
        ),
    )
    reg = ProviderRegistry(specs=specs)
    assert reg.find_gateway(api_base=api_base, api_key=api_key) is None
