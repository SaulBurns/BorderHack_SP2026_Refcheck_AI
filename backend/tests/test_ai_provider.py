import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.ai import get_provider, supported_providers
from services.ai.provider import image_part, normalize_content, text_part
from services.ai.providers.anthropic_provider import AnthropicProvider
from services.ai.providers.gemini_provider import GeminiProvider
from services.ai.providers.mock_provider import MockProvider


# ---------------------------------------------------------------------------
# Factory / provider selection
# ---------------------------------------------------------------------------

def test_supported_providers():
    assert supported_providers() == ["anthropic", "gemini", "mock", "router"]

@pytest.mark.parametrize("name,cls,pname", [
    ("mock", MockProvider, "mock"),
    ("anthropic", AnthropicProvider, "anthropic"),
    ("gemini", GeminiProvider, "gemini"),
])
def test_get_provider_by_name(name, cls, pname):
    provider = get_provider(name)
    assert isinstance(provider, cls)
    assert provider.provider_name() == pname
    assert provider.supports_vision() is True

def test_get_provider_is_case_and_space_insensitive():
    assert isinstance(get_provider("  Anthropic "), AnthropicProvider)

def test_get_provider_from_env(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    assert isinstance(get_provider(), GeminiProvider)

def test_get_provider_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    assert isinstance(get_provider(), MockProvider)

def test_invalid_provider_raises_clear_error(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    with pytest.raises(ValueError) as exc:
        get_provider()
    msg = str(exc.value)
    assert "openai" in msg
    assert "anthropic" in msg and "gemini" in msg and "mock" in msg

def test_only_mock_is_mock():
    assert get_provider("mock").is_mock is True
    assert get_provider("anthropic").is_mock is False
    assert get_provider("gemini").is_mock is False


# ---------------------------------------------------------------------------
# Neutral content helpers
# ---------------------------------------------------------------------------

def test_normalize_content_wraps_string():
    assert normalize_content("hi") == [{"type": "text", "text": "hi"}]

def test_normalize_content_passes_list_through():
    parts = [image_part("a.jpg"), text_part("go")]
    assert normalize_content(parts) == [
        {"type": "image", "path": "a.jpg"},
        {"type": "text", "text": "go"},
    ]


# ---------------------------------------------------------------------------
# Anthropic provider — behavior preserved (no network)
# ---------------------------------------------------------------------------

def test_anthropic_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY is not set"):
        AnthropicProvider().send_messages(system_prompt="s", user_content="u", temperature=0.0)

def test_anthropic_blocks_text_only():
    assert AnthropicProvider._blocks("hello") == [{"type": "text", "text": "hello"}]

def test_anthropic_blocks_image_and_text(tmp_path):
    img = tmp_path / "f.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0jpeg")
    blocks = AnthropicProvider._blocks([image_part(img), text_part("describe")])
    assert blocks[0]["type"] == "image"
    assert blocks[0]["source"]["type"] == "base64"
    assert blocks[0]["source"]["media_type"] == "image/jpeg"
    assert blocks[0]["source"]["data"]  # non-empty base64
    assert blocks[1] == {"type": "text", "text": "describe"}

def test_anthropic_send_builds_payload_and_extracts_text(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.delenv("AI_MODEL", raising=False)
    captured = {}

    def fake_post(url, headers, payload):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = payload
        return {"content": [{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}]}

    monkeypatch.setattr(AnthropicProvider, "_post_json", staticmethod(fake_post))
    out = AnthropicProvider().send_messages(
        system_prompt="SYS", user_content="ask", temperature=0.3, max_tokens=555
    )
    assert out == "hello world"
    p = captured["payload"]
    assert p["model"] == "claude-sonnet-4-5"  # default preserved
    assert p["system"] == "SYS"
    assert p["temperature"] == 0.3
    assert p["max_tokens"] == 555
    assert p["messages"] == [{"role": "user", "content": [{"type": "text", "text": "ask"}]}]
    assert captured["headers"]["x-api-key"] == "sk-test"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"

def test_anthropic_ai_model_override(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("AI_MODEL", "claude-custom")
    captured = {}
    monkeypatch.setattr(AnthropicProvider, "_post_json",
                        staticmethod(lambda url, headers, payload: captured.update(payload) or {"content": []}))
    AnthropicProvider().send_messages(system_prompt="s", user_content="u", temperature=0.0)
    assert captured["model"] == "claude-custom"


# ---------------------------------------------------------------------------
# Gemini provider
# ---------------------------------------------------------------------------

def test_gemini_missing_key_raises(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY is not set"):
        GeminiProvider().send_messages(system_prompt="s", user_content="u", temperature=0.0)

def test_gemini_missing_sdk_raises_clear_error(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.setattr(GeminiProvider, "_load_sdk",
                        staticmethod(lambda: (_ for _ in ()).throw(RuntimeError(
                            "The 'google-genai' package is required for AI_PROVIDER=gemini."))))
    with pytest.raises(RuntimeError, match="google-genai"):
        GeminiProvider().send_messages(system_prompt="s", user_content="u", temperature=0.0)

def test_gemini_parts_translation(tmp_path):
    # Fake the SDK `types` module to verify neutral -> Gemini part mapping.
    class FakePart:
        @staticmethod
        def from_text(text):
            return ("text", text)
        @staticmethod
        def from_bytes(data, mime_type):
            return ("image", mime_type, len(data))

    class FakeTypes:
        Part = FakePart

    img = tmp_path / "f.jpg"
    img.write_bytes(b"\xff\xd8imgbytes")
    parts = GeminiProvider._parts(FakeTypes, [image_part(img), text_part("go")])
    assert parts[0][0] == "image" and parts[0][1] == "image/jpeg"
    assert parts[1] == ("text", "go")

def test_gemini_send_uses_sdk(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "g-test")
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    captured = {}

    class FakePart:
        @staticmethod
        def from_text(text):
            return {"text": text}

    class FakeConfig:
        def __init__(self, system_instruction, temperature, max_output_tokens):
            captured["system"] = system_instruction
            captured["temperature"] = temperature
            captured["max_output_tokens"] = max_output_tokens

    class FakeModels:
        def generate_content(self, model, contents, config):
            captured["model"] = model
            captured["contents"] = contents

            class R:
                text = "gemini-reply"
            return R()

    class FakeClient:
        def __init__(self, api_key):
            captured["api_key"] = api_key
            self.models = FakeModels()

    class FakeGenai:
        Client = FakeClient

    class FakeTypes:
        Part = FakePart
        GenerateContentConfig = FakeConfig

    monkeypatch.setattr(GeminiProvider, "_load_sdk", staticmethod(lambda: (FakeGenai, FakeTypes)))
    out = GeminiProvider().send_messages(
        system_prompt="SYS", user_content="ask", temperature=0.4, max_tokens=321
    )
    assert out == "gemini-reply"
    assert captured["api_key"] == "g-test"
    assert captured["model"] == "gemini-2.5-flash"  # default preserved
    assert captured["system"] == "SYS"
    assert captured["temperature"] == 0.4
    assert captured["max_output_tokens"] == 321
    assert captured["contents"] == [{"text": "ask"}]


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

def test_mock_provider_is_mock_and_never_networks():
    p = MockProvider()
    assert p.is_mock is True
    assert p.provider_name() == "mock"
    out = p.send_messages(system_prompt="s", user_content="u", temperature=0.0)
    import json
    parsed = json.loads(out)  # returns valid JSON
    assert "verdict" in parsed
