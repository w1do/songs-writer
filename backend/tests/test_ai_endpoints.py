import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import ai, auth
from app.ai import router as ai_router
from app.config import settings
from app.database import Base, engine
from app.models import Message
from app.services.ai import AIServiceError
from app.songs import router as songs_router

VALID_ANALYSIS = {
    "theme": "rainy city night",
    "emotion": "melancholy",
    "genre": "rap",
    "bpm": 92,
    "energy": 0.4,
    "structure": ["VERSE", "CHORUS", "VERSE", "CHORUS"],
}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "admin_password", "correct-password")
    monkeypatch.setattr(settings, "session_secret", "test-secret")

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("TRUNCATE songs, messages, presets CASCADE"))

    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(songs_router)
    app.include_router(ai_router)
    test_client = TestClient(app)
    response = test_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "correct-password"},
    )
    assert response.status_code == 200
    return test_client


def create_song(client):
    response = client.post("/songs", json={"idea": "rainy city at night"})
    assert response.status_code == 201
    return response.json()


def fake_completion(content):
    def _call(system_prompt, user_prompt, transport=None):
        return content

    return _call


def test_analyze_idea_saves_valid_analysis_and_logs_messages(client, monkeypatch):
    song = create_song(client)
    completion = fake_completion(json.dumps(VALID_ANALYSIS))
    monkeypatch.setattr(ai, "request_completion", completion)

    response = client.post(f"/songs/{song['id']}/analyze-idea")

    assert response.status_code == 200
    assert response.json()["analysis"] == VALID_ANALYSIS
    assert response.json()["lyrics"] is None


def test_analyze_idea_keeps_song_intact_on_invalid_ai_response(client, monkeypatch):
    song = create_song(client)
    client.patch(f"/songs/{song['id']}", json={"lyrics": "[VERSE]\nkeep me"})
    invalid = {**VALID_ANALYSIS, "bpm": 500}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(invalid)))

    response = client.post(f"/songs/{song['id']}/analyze-idea")

    assert response.status_code == 502
    after = client.get(f"/songs/{song['id']}").json()
    assert after["analysis"] is None
    assert after["lyrics"] == "[VERSE]\nkeep me"


def test_analyze_idea_rejects_non_json_response(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion("not json"))

    response = client.post(f"/songs/{song['id']}/analyze-idea")

    assert response.status_code == 502
    assert client.get(f"/songs/{song['id']}").json()["analysis"] is None


def test_analyze_idea_provider_error_returns_502_and_logs_error(client, monkeypatch):
    song = create_song(client)

    def failing(system_prompt, user_prompt, transport=None):
        raise AIServiceError("AI provider timed out")

    monkeypatch.setattr(ai, "request_completion", failing)

    response = client.post(f"/songs/{song['id']}/analyze-idea")

    assert response.status_code == 502
    assert response.json()["detail"] == "AI provider timed out"
    from app.database import SessionLocal

    with SessionLocal() as db:
        messages = db.query(Message).filter(Message.song_id == uuid.UUID(song["id"]))
        roles = [m.role for m in messages.all()]
    assert "error" in roles


def test_analyze_idea_logs_request_and_response_on_success(client, monkeypatch):
    song = create_song(client)
    completion = fake_completion(json.dumps(VALID_ANALYSIS))
    monkeypatch.setattr(ai, "request_completion", completion)

    client.post(f"/songs/{song['id']}/analyze-idea")

    from app.database import SessionLocal

    with SessionLocal() as db:
        messages = db.query(Message).filter(Message.song_id == uuid.UUID(song["id"]))
        roles = [m.role for m in messages.all()]
    assert roles == ["user", "assistant"]


def test_analyze_idea_missing_song_returns_404(client):
    response = client.post(f"/songs/{uuid.uuid4()}/analyze-idea")

    assert response.status_code == 404


def test_analyze_idea_without_session_returns_401(client):
    song = create_song(client)
    client.cookies.clear()

    response = client.post(f"/songs/{song['id']}/analyze-idea")

    assert response.status_code == 401


LINE_ACTION_RESULT = {"variants": ["first variant", "second variant"], "note": None}


@pytest.mark.parametrize(
    "action", ["variants", "continue", "rewrite", "rhyme", "flow", "vocal"]
)
def test_line_action_returns_variants_for_each_action(client, monkeypatch, action):
    song = create_song(client)
    lyrics = "[VERSE]\nrain on the glass"
    client.patch(f"/songs/{song['id']}", json={"lyrics": lyrics})
    completion = fake_completion(json.dumps(LINE_ACTION_RESULT))
    monkeypatch.setattr(ai, "request_completion", completion)

    response = client.post(
        f"/songs/{song['id']}/line-action",
        json={"action": action, "line": "rain on the glass"},
    )

    assert response.status_code == 200
    assert response.json() == LINE_ACTION_RESULT
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] == lyrics


def test_continue_section_returns_variants_without_changing_lyrics(client, monkeypatch):
    song = create_song(client)
    lyrics = "[VERSE]\nrain on the glass"
    client.patch(f"/songs/{song['id']}", json={"lyrics": lyrics})
    result = {"variants": ["cold wind in the street\nlights go out"], "note": None}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(result)))

    response = client.post(
        f"/songs/{song['id']}/continue-section", json={"section": lyrics}
    )

    assert response.status_code == 200
    assert response.json() == result
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] == lyrics


def test_continue_section_rejects_empty_section(client):
    song = create_song(client)

    response = client.post(
        f"/songs/{song['id']}/continue-section", json={"section": ""}
    )

    assert response.status_code == 422


def test_line_action_rejects_selection_outside_line(client):
    song = create_song(client)

    response = client.post(
        f"/songs/{song['id']}/line-action",
        json={"action": "rewrite", "line": "rain on the glass", "selection": "snow"},
    )

    assert response.status_code == 422


def test_line_action_rejects_unknown_action(client):
    song = create_song(client)

    response = client.post(
        f"/songs/{song['id']}/line-action", json={"action": "delete", "line": "rain"}
    )

    assert response.status_code == 422


def test_line_action_invalid_ai_response_returns_502(client, monkeypatch):
    song = create_song(client)
    empty = fake_completion(json.dumps({"variants": []}))
    monkeypatch.setattr(ai, "request_completion", empty)

    response = client.post(
        f"/songs/{song['id']}/line-action",
        json={"action": "variants", "line": "rain"},
    )

    assert response.status_code == 502


def test_create_hook_returns_variants(client, monkeypatch):
    song = create_song(client)
    hooks = {"variants": ["hook one", "hook two"]}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(hooks)))

    response = client.post(f"/songs/{song['id']}/create-hook")

    assert response.status_code == 200
    assert response.json() == {"variants": ["hook one", "hook two"]}


def test_create_chorus_returns_multiple_variants(client, monkeypatch):
    song = create_song(client)
    chorus = {"variants": [["line a", "line b"], ["line c", "line d"]]}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(chorus)))

    response = client.post(f"/songs/{song['id']}/create-chorus")

    assert response.status_code == 200
    assert response.json() == chorus


def test_create_hook_provider_error_returns_502_and_logs_error(client, monkeypatch):
    song = create_song(client)

    def failing(system_prompt, user_prompt, transport=None):
        raise AIServiceError("AI provider timed out")

    monkeypatch.setattr(ai, "request_completion", failing)

    response = client.post(f"/songs/{song['id']}/create-hook")

    assert response.status_code == 502
    from app.database import SessionLocal

    with SessionLocal() as db:
        messages = db.query(Message).filter(Message.song_id == uuid.UUID(song["id"]))
        roles = [m.role for m in messages.all()]
    assert roles == ["user", "error"]


def test_structure_suggestion_returns_sections(client, monkeypatch):
    song = create_song(client)
    result = {
        "sections": ["VERSE", "CHORUS", "VERSE", "CHORUS"],
        "reason": "classic form",
    }
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(result)))

    response = client.post(f"/songs/{song['id']}/structure-suggestion")

    assert response.status_code == 200
    assert response.json() == result


def test_finish_song_returns_comments_and_keeps_lyrics(client, monkeypatch):
    song = create_song(client)
    lyrics = "[VERSE]\nkeep the original text"
    client.patch(f"/songs/{song['id']}", json={"lyrics": lyrics})
    comments = {"comments": ["tighten the bridge"]}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(comments)))

    response = client.post(f"/songs/{song['id']}/finish-song")

    assert response.status_code == 200
    assert response.json() == {"comments": ["tighten the bridge"]}
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] == lyrics


def test_prepare_track_saves_all_fields_and_keeps_lyrics(client, monkeypatch):
    song = create_song(client)
    lyrics = "[VERSE]\nkeep the original text"
    client.patch(f"/songs/{song['id']}", json={"lyrics": lyrics})
    prepared = {
        "style_prompt": "melancholic rap, soft piano",
        "negative_style_prompt": "heavy distortion",
        "performance": "low, slow delivery",
        "generation_settings": {"bpm": 92, "duration": 180},
    }
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(prepared)))

    response = client.post(f"/songs/{song['id']}/prepare-track")

    assert response.status_code == 200
    body = response.json()
    assert body["track_settings"] == {
        "style_prompt": "melancholic rap, soft piano",
        "negative_style_prompt": "heavy distortion",
        "performance": "low, slow delivery",
    }
    assert body["generation_settings"] == {"bpm": 92, "duration": 180}
    assert body["lyrics"] == lyrics


def test_prepare_track_invalid_response_keeps_song_intact(client, monkeypatch):
    song = create_song(client)
    invalid = {"style_prompt": ""}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(invalid)))

    response = client.post(f"/songs/{song['id']}/prepare-track")

    assert response.status_code == 502
    after = client.get(f"/songs/{song['id']}").json()
    assert after["track_settings"] is None
    assert after["generation_settings"] is None


def test_ai_action_missing_song_returns_404(client):
    response = client.post(f"/songs/{uuid.uuid4()}/create-hook")

    assert response.status_code == 404


def test_draft_lyrics_uses_analysis_and_keeps_lyrics(client, monkeypatch):
    song = create_song(client)
    lyrics = "[VERSE]\nkeep the original text"
    client.patch(f"/songs/{song['id']}", json={"lyrics": lyrics})
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    result = {"variants": ["[VERSE]\nrain on the glass\n\n[CHORUS]\nhold on"]}
    captured = {}

    def capturing(system_prompt, user_prompt, transport=None):
        captured["user_prompt"] = user_prompt
        return json.dumps(result)

    monkeypatch.setattr(ai, "request_completion", capturing)

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 200
    assert response.json() == result
    assert "melancholy" in captured["user_prompt"]
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] == lyrics


def test_draft_lyrics_requires_analysis(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(
        ai, "request_completion", fake_completion(json.dumps({"variants": ["x"]}))
    )

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 409


def test_draft_lyrics_rejects_invalid_ai_response(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    monkeypatch.setattr(
        ai, "request_completion", fake_completion(json.dumps({"variants": []}))
    )

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 502


def test_draft_lyrics_accepts_json_wrapped_in_text(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    content = 'Вот вариант:\n{"variants": ["[VERSE]\\nrain on the glass"]}'
    monkeypatch.setattr(ai, "request_completion", fake_completion(content))

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 200
    assert response.json() == {"variants": ["[VERSE]\nrain on the glass"]}


def test_draft_lyrics_keeps_at_most_three_variants(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    content = json.dumps({"variants": ["a", "b", "c", "d"]})
    monkeypatch.setattr(ai, "request_completion", fake_completion(content))

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 200
    assert response.json() == {"variants": ["a", "b", "c"]}


def test_draft_lyrics_accepts_raw_newlines_inside_json_strings(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    content = '{"variants": ["[VERSE]\nrain on the glass\n\n[CHORUS]\nhold on"]}'
    monkeypatch.setattr(ai, "request_completion", fake_completion(content))

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 200
    assert response.json() == {"variants": ["[VERSE]\nrain on the glass\n\n[CHORUS]\nhold on"]}


def test_draft_lyrics_ignores_extra_fields_and_line_lists(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    content = json.dumps(
        {"variants": [["[VERSE]", "rain on the glass"]], "note": "ok"}
    )
    monkeypatch.setattr(ai, "request_completion", fake_completion(content))

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 200
    assert response.json() == {"variants": ["[VERSE]\nrain on the glass"]}


def test_draft_lyrics_error_log_keeps_raw_response(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    monkeypatch.setattr(ai, "request_completion", fake_completion("не JSON вообще"))

    response = client.post(f"/songs/{song['id']}/draft-lyrics")

    assert response.status_code == 502
    from app.database import SessionLocal

    with SessionLocal() as db:
        errors = (
            db.query(Message)
            .filter(Message.song_id == uuid.UUID(song["id"]), Message.role == "error")
            .all()
        )
    assert any(
        (m.message_metadata or {}).get("raw_response") == "не JSON вообще" for m in errors
    )
