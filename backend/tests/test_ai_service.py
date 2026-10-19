import json

import httpx
import pytest

from app.config import settings
from app.models import Preset, Song
from app.schemas import PresetCreate
from app.services.ai import (
    AIServiceError,
    build_song_context,
    parse_structured,
    request_completion,
)


@pytest.fixture
def ai_settings(monkeypatch):
    monkeypatch.setattr(settings, "ai_api_key", "test-key")
    monkeypatch.setattr(settings, "ai_base_url", "https://ai.example.test/api/v1")
    monkeypatch.setattr(settings, "ai_model", "test-model")
    monkeypatch.setattr(settings, "ai_timeout_seconds", 5.0)


def completion_response(content: str) -> httpx.Response:
    body = {"choices": [{"message": {"role": "assistant", "content": content}}]}
    return httpx.Response(200, json=body)


def test_request_completion_sends_chat_request_and_returns_content(ai_settings):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["request"] = request
        return completion_response("Variant one")

    transport = httpx.MockTransport(handler)
    result = request_completion("system text", "user text", transport=transport)

    request = captured["request"]
    body = json.loads(request.content)
    assert result == "Variant one"
    assert str(request.url) == "https://ai.example.test/api/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer test-key"
    assert body["model"] == "test-model"
    assert body["messages"] == [
        {"role": "system", "content": "system text"},
        {"role": "user", "content": "user text"},
    ]


def test_request_completion_maps_timeout_to_ai_service_error(ai_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    with pytest.raises(AIServiceError, match="timed out"):
        request_completion("system", "user", transport=httpx.MockTransport(handler))


def test_request_completion_maps_network_error_to_ai_service_error(ai_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(AIServiceError, match="request failed"):
        request_completion("system", "user", transport=httpx.MockTransport(handler))


def test_request_completion_maps_error_status_to_ai_service_error(ai_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "upstream down"})

    with pytest.raises(AIServiceError, match="HTTP 500"):
        request_completion("system", "user", transport=httpx.MockTransport(handler))


def test_request_completion_rejects_unexpected_response_shape(ai_settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"unexpected": True})

    with pytest.raises(AIServiceError, match="unexpected response"):
        request_completion("system", "user", transport=httpx.MockTransport(handler))


def test_request_completion_without_api_key_does_not_send_request(monkeypatch):
    monkeypatch.setattr(settings, "ai_api_key", "")

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("request must not be sent")

    with pytest.raises(AIServiceError, match="not configured"):
        request_completion("system", "user", transport=httpx.MockTransport(handler))


def test_parse_structured_accepts_json_wrapped_in_markdown_fence():
    result = parse_structured(
        '```json\n{"name": "A", "genre": "rap"}\n```', PresetCreate
    )

    assert result.name == "A"
    assert result.genre == "rap"


def test_build_song_context_with_partial_data_omits_empty_fields():
    song = Song(
        idea="rainy city at night",
        title=None,
        lyrics="",
        analysis=None,
        track_settings=None,
    )

    context = build_song_context(song)

    assert context == {"idea": "rainy city at night"}


def test_build_song_context_with_full_data_and_no_preset():
    song = Song(
        idea="rainy city at night",
        title="Night",
        lyrics="[VERSE]\nrain on the glass",
        analysis={"genre": "synth-pop", "emotion": "melancholy", "bpm": 96},
        track_settings={
            "style_prompt": "dark piano",
            "negative_style_prompt": "no distortion",
            "performance": "[DOUBLE] on chorus",
        },
        generation_settings={"bpm": 120},
    )

    context = build_song_context(song)

    assert context == {
        "idea": "rainy city at night",
        "title": "Night",
        "genre": "synth-pop",
        "bpm": 96,
        "emotion": "melancholy",
        "lyrics": "[VERSE]\nrain on the glass",
        "style_prompt": "dark piano",
        "negative_style_prompt": "no distortion",
        "performance": "[DOUBLE] on chorus",
    }
    assert "preset" not in context


def test_build_song_context_uses_generation_bpm_when_analysis_has_none():
    song = Song(
        idea="idea",
        analysis={"genre": "pop"},
        generation_settings={"bpm": 110},
    )

    context = build_song_context(song)

    assert context["bpm"] == 110


def test_build_song_context_with_preset_adds_only_filled_preset_fields():
    song = Song(idea="idea", analysis={"genre": "pop"})
    preset = Preset(
        name="Pop",
        genre="pop",
        bpm_min=100,
        bpm_max=120,
        energy=0.7,
        style_prompt="bright pop",
        negative_style_prompt=None,
        sound_scene="",
        hooks_prompt="short catchy hook",
        effects_prompt=None,
        chorus_vocal_style="layered harmonies",
    )

    context = build_song_context(song, preset)

    assert context["genre"] == "pop"
    assert context["preset"] == {
        "genre": "pop",
        "bpm_min": 100,
        "bpm_max": 120,
        "energy": 0.7,
        "style_prompt": "bright pop",
        "hooks_prompt": "short catchy hook",
        "chorus_vocal_style": "layered harmonies",
    }


def test_build_song_context_with_preset_and_partial_song_data():
    song = Song(idea="idea")
    preset = Preset(name="Rock", genre="rock")

    context = build_song_context(song, preset)

    assert context == {"idea": "idea", "preset": {"genre": "rock"}}
