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
from app.services.ai import PRESET_CONTEXT_FIELDS, AIServiceError
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
        connection.execute(text("ALTER TABLE songs ADD COLUMN IF NOT EXISTS story TEXT"))
        connection.execute(
            text(
                "ALTER TABLE songs ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'draft'"
            )
        )
        connection.execute(
            text("ALTER TABLE songs ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20)")
        )
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


REFERENCE_ANALYSIS = {
    "theme": "night drive",
    "emotions": ["calm", "longing"],
    "genre_context": ["synthwave"],
    "bpm": 100,
    "energy": "medium",
    "structure": ["VERSE", "CHORUS"],
    "delivery": "singing",
    "rhyme_and_flow": "long chained rhymes",
    "transcript": "neon lights on the highway",
}
DRAFT_RESULT = {"variants": ["[VERSE]\nrain on the glass"]}


def create_reference_preset(**fields):
    from app.database import SessionLocal
    from app.models import Preset

    with SessionLocal() as db:
        preset = Preset(**{"name": "reference preset", "genre": "synthwave", **fields})
        db.add(preset)
        db.commit()
        return str(preset.id)


def create_analyzed_song(client, monkeypatch):
    song = create_song(client)
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(VALID_ANALYSIS)))
    client.post(f"/songs/{song['id']}/analyze-idea")
    return song


def capture_completion(monkeypatch, content):
    calls = []

    def _call(system_prompt, user_prompt, transport=None):
        calls.append(user_prompt)
        return content

    monkeypatch.setattr(ai, "request_completion", _call)
    return calls


def test_draft_lyrics_adds_preset_as_style_context(client, monkeypatch):
    song = create_analyzed_song(client, monkeypatch)
    preset_id = create_reference_preset(
        genre="synthwave", bpm_min=96, bpm_max=104, style_prompt="warm synth vocal"
    )
    calls = capture_completion(monkeypatch, json.dumps(DRAFT_RESULT))

    response = client.post(
        f"/songs/{song['id']}/draft-lyrics", json={"preset_id": preset_id}
    )

    assert response.status_code == 200
    assert response.json() == DRAFT_RESULT
    prompt = json.loads(calls[0])
    style = prompt["style_context"]
    assert style["guidance"]
    assert style["genre"] == "synthwave"
    assert style["bpm_min"] == 96
    assert style["bpm_max"] == 104
    assert style["style_prompt"] == "warm synth vocal"
    assert "negative_style_prompt" not in style
    assert prompt["song"]["emotion"] == "melancholy"


def test_draft_lyrics_without_preset_id_has_no_style_context(client, monkeypatch):
    song = create_analyzed_song(client, monkeypatch)
    calls = capture_completion(monkeypatch, json.dumps(DRAFT_RESULT))

    assert client.post(f"/songs/{song['id']}/draft-lyrics").status_code == 200
    assert client.post(
        f"/songs/{song['id']}/draft-lyrics", json={}
    ).status_code == 200

    without_body = json.loads(calls[0])
    assert without_body == json.loads(calls[1])
    assert set(without_body) == {"song", "request"}
    assert without_body["request"] == {}


def test_draft_lyrics_unknown_preset_returns_404(client, monkeypatch):
    song = create_analyzed_song(client, monkeypatch)
    calls = capture_completion(monkeypatch, json.dumps(DRAFT_RESULT))

    response = client.post(
        f"/songs/{song['id']}/draft-lyrics", json={"preset_id": str(uuid.uuid4())}
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Preset not found"
    assert calls == []


def test_draft_lyrics_uses_preset_of_reference_song(client, monkeypatch):
    from app.database import SessionLocal
    from app.models import Song

    song = create_analyzed_song(client, monkeypatch)
    preset_id = create_reference_preset(genre="ballad")
    with SessionLocal() as db:
        reference = Song(title="reference.mp3", kind="reference", preset_id=uuid.UUID(preset_id))
        db.add(reference)
        db.commit()
    calls = capture_completion(monkeypatch, json.dumps(DRAFT_RESULT))

    response = client.post(
        f"/songs/{song['id']}/draft-lyrics", json={"preset_id": preset_id}
    )

    assert response.status_code == 200
    assert json.loads(calls[0])["style_context"]["genre"] == "ballad"


def test_draft_lyrics_reference_transcript_stays_out_of_message_journal(
    client, monkeypatch
):
    from app.database import SessionLocal
    from app.models import Song

    song = create_analyzed_song(client, monkeypatch)
    preset_id = create_reference_preset(genre="synthwave", style_prompt="warm synth vocal")
    with SessionLocal() as db:
        reference = Song(
            title="reference.mp3",
            kind="reference",
            analysis_status="done",
            analysis=REFERENCE_ANALYSIS,
            preset_id=uuid.UUID(preset_id),
        )
        db.add(reference)
        db.commit()
    capture_completion(monkeypatch, json.dumps(DRAFT_RESULT))

    response = client.post(
        f"/songs/{song['id']}/draft-lyrics", json={"preset_id": preset_id}
    )

    assert response.status_code == 200
    transcript = REFERENCE_ANALYSIS["transcript"]
    with SessionLocal() as db:
        messages = (
            db.query(Message).filter(Message.song_id == uuid.UUID(song["id"])).all()
        )
    assert messages
    for message in messages:
        assert transcript not in message.content
        assert transcript not in json.dumps(message.message_metadata or {})
    style_logs = [
        m.message_metadata["style_context"]
        for m in messages
        if "style_context" in (m.message_metadata or {})
    ]
    assert len(style_logs) == 1
    assert set(style_logs[0]) <= {"guidance", *PRESET_CONTEXT_FIELDS}


def test_draft_lyrics_rejects_malformed_preset_id(client, monkeypatch):
    song = create_analyzed_song(client, monkeypatch)
    calls = capture_completion(monkeypatch, json.dumps(DRAFT_RESULT))

    response = client.post(
        f"/songs/{song['id']}/draft-lyrics", json={"preset_id": "not-a-uuid"}
    )

    assert response.status_code == 422
    assert calls == []


def test_chat_saves_messages_and_updates_lyrics(client, monkeypatch):
    song = create_song(client)
    reply = {"reply": "Усилил припев", "lyrics": "[CHORUS]\nновый припев"}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(reply)))

    response = client.post(
        f"/songs/{song['id']}/chat", json={"message": "  усиль припев  "}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Усилил припев"
    assert body["lyrics"] == "[CHORUS]\nновый припев"
    assert [m["role"] for m in body["messages"]] == ["user", "assistant"]
    assert body["messages"][0]["content"] == "усиль припев"
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] == (
        "[CHORUS]\nновый припев"
    )


def test_chat_without_lyrics_change_keeps_lyrics(client, monkeypatch):
    song = create_song(client)
    client.patch(f"/songs/{song['id']}", json={"lyrics": "[VERSE]\nkeep"})
    reply = {"reply": "Какой бридж нужен?", "lyrics": None}
    monkeypatch.setattr(ai, "request_completion", fake_completion(json.dumps(reply)))

    response = client.post(f"/songs/{song['id']}/chat", json={"message": "хочу"})

    assert response.status_code == 200
    assert response.json()["lyrics"] == "[VERSE]\nkeep"
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] == "[VERSE]\nkeep"


def test_chat_prompt_contains_story_preset_and_history(client, monkeypatch):
    from app.database import SessionLocal
    from app.models import Preset

    with SessionLocal() as db:
        preset = Preset(name="Trap", genre="trap", bpm_min=140)
        db.add(preset)
        db.commit()
        preset_id = str(preset.id)
    song = client.post(
        "/songs", json={"idea": "rainy city at night", "preset_id": preset_id}
    ).json()
    client.patch(
        f"/songs/{song['id']}",
        json={"story": "история про ночной город", "lyrics": "[VERSE]\nold"},
    )
    captured = {}

    def capturing(system_prompt, user_prompt, transport=None):
        captured["user"] = user_prompt
        return json.dumps({"reply": "ок", "lyrics": None})

    monkeypatch.setattr(ai, "request_completion", capturing)

    client.post(f"/songs/{song['id']}/chat", json={"message": "первый"})
    client.post(f"/songs/{song['id']}/chat", json={"message": "второй"})

    prompt = json.loads(captured["user"])
    assert prompt["song"]["story"] == "история про ночной город"
    assert prompt["song"]["lyrics"] == "[VERSE]\nold"
    assert prompt["song"]["preset"]["genre"] == "trap"
    assert prompt["song"]["messages"][-1] == {"role": "assistant", "content": "ок"}
    assert prompt["song"]["messages"][0] == {"role": "user", "content": "первый"}
    assert prompt["message"] == "второй"


def test_chat_missing_song_returns_404(client):
    response = client.post(f"/songs/{uuid.uuid4()}/chat", json={"message": "hi"})

    assert response.status_code == 404


def test_chat_blank_message_returns_422(client):
    song = create_song(client)

    response = client.post(f"/songs/{song['id']}/chat", json={"message": "   "})

    assert response.status_code == 422
    assert client.get(f"/songs/{song['id']}").json() is not None


def test_chat_provider_error_saves_user_message_only(client, monkeypatch):
    song = create_song(client)

    def failing(system_prompt, user_prompt, transport=None):
        raise AIServiceError("AI provider timed out")

    monkeypatch.setattr(ai, "request_completion", failing)

    response = client.post(f"/songs/{song['id']}/chat", json={"message": "hi"})

    assert response.status_code == 502
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] is None
    from app.database import SessionLocal

    with SessionLocal() as db:
        roles = [
            m.role
            for m in db.query(Message)
            .filter(Message.song_id == uuid.UUID(song["id"]))
            .order_by(Message.created_at)
            .all()
        ]
    assert roles == ["user", "error"]


def test_chat_retries_once_on_invalid_json(client, monkeypatch):
    song = create_song(client)
    valid = json.dumps({"reply": "готово", "lyrics": "[CHORUS]\nx"})
    responses = iter(["not json", valid])
    monkeypatch.setattr(ai, "request_completion", lambda s, u, transport=None: next(responses))

    response = client.post(f"/songs/{song['id']}/chat", json={"message": "hi"})

    assert response.status_code == 200
    assert response.json()["reply"] == "готово"


def test_chat_invalid_json_twice_returns_502_and_keeps_lyrics(client, monkeypatch):
    song = create_song(client)
    client.patch(f"/songs/{song['id']}", json={"lyrics": "[VERSE]\nkeep"})
    monkeypatch.setattr(ai, "request_completion", fake_completion("not json"))

    response = client.post(f"/songs/{song['id']}/chat", json={"message": "hi"})

    assert response.status_code == 502
    assert client.get(f"/songs/{song['id']}").json()["lyrics"] == "[VERSE]\nkeep"
