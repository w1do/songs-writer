import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import auth, songs
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Preset, Song
from app.presets import router as presets_router
from app.schemas import PresetCreate, ReferenceAnalysis
from app.services.ai import (
    GENERATED_PRESET_KEY,
    AIServiceError,
    ReferenceAnalysisInvalidJSONError,
    ReferenceAnalysisValidationError,
)
from app.songs import router as songs_router


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
            text(
                "ALTER TABLE songs ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20)"
            )
        )
        connection.execute(text("TRUNCATE songs, messages, presets CASCADE"))

    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(presets_router)
    app.include_router(songs_router)
    test_client = TestClient(app)
    response = test_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "correct-password"},
    )
    assert response.status_code == 200
    return test_client


def create_preset(client):
    response = client.post(
        "/presets",
        json={"name": "Preset", "genre": "pop", "bpm_min": 90, "bpm_max": 110},
    )
    assert response.status_code == 201
    return response.json()


def create_song(client, **overrides):
    response = client.post("/songs", json={"idea": "rainy city at night", **overrides})
    assert response.status_code == 201
    return response.json()


def test_create_song_and_read_it(client):
    created = create_song(client, title="Night")

    response = client.get(f"/songs/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body == created
    assert body["title"] == "Night"
    assert body["idea"] == "rainy city at night"
    assert body["preset_id"] is None


def test_create_song_with_preset_id(client):
    preset = create_preset(client)

    created = create_song(client, preset_id=preset["id"])

    assert created["preset_id"] == preset["id"]


def test_create_song_with_unknown_preset_returns_422(client):
    payload = {"idea": "idea", "preset_id": str(uuid.uuid4())}
    response = client.post("/songs", json=payload)

    assert response.status_code == 422


def test_partial_update_song_changes_only_given_fields(client):
    created = create_song(client, title="Night")

    response = client.patch(
        f"/songs/{created['id']}",
        json={
            "lyrics": "first verse",
            "track_settings": {"style_prompt": "dark piano"},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["lyrics"] == "first verse"
    assert body["track_settings"] == {"style_prompt": "dark piano"}
    assert body["title"] == "Night"
    assert body["idea"] == "rainy city at night"


def test_update_song_with_unknown_preset_returns_422(client):
    created = create_song(client)

    response = client.patch(
        f"/songs/{created['id']}", json={"preset_id": str(uuid.uuid4())}
    )

    assert response.status_code == 422


def test_get_missing_song_returns_404(client):
    response = client.get(f"/songs/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Song not found"


def test_update_missing_song_returns_404(client):
    response = client.patch(f"/songs/{uuid.uuid4()}", json={"title": "Missing"})

    assert response.status_code == 404


def test_deleting_preset_sets_song_preset_id_to_null(client):
    preset = create_preset(client)
    song = create_song(client, preset_id=preset["id"])

    delete_response = client.delete(f"/presets/{preset['id']}")
    response = client.get(f"/songs/{song['id']}")

    assert delete_response.status_code == 204
    assert response.status_code == 200
    assert response.json()["preset_id"] is None


def test_export_song_returns_track_settings(client):
    created = create_song(client, title="Night")
    client.patch(
        f"/songs/{created['id']}",
        json={
            "lyrics": "first verse",
            "track_settings": {
                "style_prompt": "dark piano",
                "negative_style_prompt": "no distortion",
                "performance": "[DOUBLE] on chorus",
            },
            "generation_settings": {"bpm": 96},
        },
    )

    response = client.get(f"/songs/{created['id']}/export")

    assert response.status_code == 200
    assert response.json() == {
        "song_id": created["id"],
        "title": "Night",
        "lyrics": "first verse",
        "style_prompt": "dark piano",
        "negative_style_prompt": "no distortion",
        "performance": "[DOUBLE] on chorus",
        "generation_settings": {"bpm": 96},
    }


def test_export_missing_song_returns_404(client):
    response = client.get(f"/songs/{uuid.uuid4()}/export")

    assert response.status_code == 404


def test_songs_without_session_return_401(client):
    client.cookies.clear()

    response = client.post("/songs", json={"idea": "idea"})

    assert response.status_code == 401


def test_list_songs_returns_empty_list(client):
    response = client.get("/songs")

    assert response.status_code == 200
    assert response.json() == []


def test_list_songs_sorted_by_updated_at_desc(client):
    first = create_song(client, title="First")
    second = create_song(client, title="Second")
    third = create_song(client, title="Third")
    patch_response = client.patch(f"/songs/{first['id']}", json={"title": "Updated"})
    assert patch_response.status_code == 200

    response = client.get("/songs")

    assert response.status_code == 200
    body = response.json()
    assert [song["id"] for song in body] == [first["id"], third["id"], second["id"]]
    updated_at_values = [song["updated_at"] for song in body]
    assert updated_at_values == sorted(updated_at_values, reverse=True)


def test_list_songs_without_session_returns_401(client):
    client.cookies.clear()

    response = client.get("/songs")

    assert response.status_code == 401


def test_list_songs_items_have_only_summary_fields(client):
    preset = create_preset(client)
    create_song(client, title="Night", preset_id=preset["id"])

    response = client.get("/songs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    expected_keys = {"id", "title", "idea", "preset_id", "created_at", "updated_at"}
    assert set(body[0]) == expected_keys
    assert body[0]["title"] == "Night"
    assert body[0]["idea"] == "rainy city at night"
    assert body[0]["preset_id"] == preset["id"]


def test_list_songs_returns_song_with_null_idea(client):
    created = create_song(client, title="Night")
    patch_response = client.patch(f"/songs/{created['id']}", json={"idea": None})
    assert patch_response.status_code == 200

    response = client.get("/songs")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == created["id"]
    assert body[0]["idea"] is None


def test_delete_song_returns_204_and_removes_it(client):
    song = create_song(client)

    response = client.delete(f"/songs/{song['id']}")

    assert response.status_code == 204
    assert client.get(f"/songs/{song['id']}").status_code == 404
    assert client.get("/songs").json() == []


def test_delete_missing_song_returns_404(client):
    response = client.delete(f"/songs/{uuid.uuid4()}")

    assert response.status_code == 404


def test_delete_song_without_session_returns_401(client):
    song = create_song(client)
    client.cookies.clear()

    response = client.delete(f"/songs/{song['id']}")

    assert response.status_code == 401


def test_patch_story_saves_and_returns_it(client):
    created = create_song(client)

    response = client.patch(
        f"/songs/{created['id']}", json={"story": "Про дождь в городе"}
    )

    assert response.status_code == 200
    assert response.json()["story"] == "Про дождь в городе"
    assert client.get(f"/songs/{created['id']}").json()["story"] == (
        "Про дождь в городе"
    )


def test_patch_blank_story_clears_it_to_null(client):
    created = create_song(client)
    client.patch(f"/songs/{created['id']}", json={"story": "text"})

    response = client.patch(f"/songs/{created['id']}", json={"story": "   "})

    assert response.status_code == 200
    assert response.json()["story"] is None


def test_patch_story_longer_than_limit_returns_422(client):
    created = create_song(client)

    response = client.patch(
        f"/songs/{created['id']}", json={"story": "a" * 10001}
    )

    assert response.status_code == 422
    assert client.get(f"/songs/{created['id']}").json()["story"] is None


def test_new_song_has_null_story(client):
    created = create_song(client)

    assert created["story"] is None


def upload_reference(
    client, file_name="night mix.mp3", content=b"fake audio", content_type="audio/mpeg"
):
    return client.post(
        "/songs/reference", files={"file": (file_name, content, content_type)}
    )


def count_reference_rows():
    with engine.connect() as connection:
        return connection.execute(
            text("SELECT count(*) FROM songs WHERE kind = 'reference'")
        ).scalar_one()


def test_upload_reference_creates_pending_row(client):
    response = upload_reference(client)

    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "title", "kind", "analysis_status"}
    assert body["title"] == "night mix.mp3"
    assert body["kind"] == "reference"
    assert body["analysis_status"] == "pending"
    assert count_reference_rows() == 1


def test_upload_reference_keeps_only_file_name(client):
    response = upload_reference(
        client, file_name="folder/night.wav", content_type="audio/wav"
    )

    assert response.status_code == 201
    assert response.json()["title"] == "night.wav"


def test_upload_reference_rejects_unsupported_extension(client):
    response = upload_reference(
        client, file_name="notes.txt", content_type="audio/mpeg"
    )

    assert response.status_code == 415
    assert count_reference_rows() == 0


def test_upload_reference_rejects_unsupported_mime_type(client):
    response = upload_reference(
        client, file_name="night.mp3", content_type="application/pdf"
    )

    assert response.status_code == 415
    assert count_reference_rows() == 0


@pytest.mark.parametrize(
    ("file_name", "content_type"),
    [
        ("night.mp3", "audio/mp3"),
        ("night.m4a", "audio/mp4a-latm"),
        ("night.flac", "audio/x-flac"),
        ("night.mp3", "application/octet-stream"),
    ],
)
def test_upload_reference_accepts_browser_mime_variants(
    client, monkeypatch, file_name, content_type
):
    monkeypatch.setattr(songs, "run_reference_analysis", lambda *args: None)

    response = upload_reference(client, file_name=file_name, content_type=content_type)

    assert response.status_code == 201
    assert count_reference_rows() == 1


def test_upload_reference_rejects_file_over_size_limit(client, monkeypatch):
    monkeypatch.setattr(songs, "MAX_REFERENCE_AUDIO_BYTES", 10)

    at_limit = upload_reference(client, content=b"0123456789")
    over_limit = upload_reference(client, content=b"0123456789A")

    assert at_limit.status_code == 201
    assert over_limit.status_code == 413
    assert count_reference_rows() == 1


PRESET_FIELDS = {
    "name": "night ballad",
    "genre": "ballad",
    "bpm_min": 68,
    "bpm_max": 76,
    "energy": 0.3,
    "style_prompt": "sung ballad, warm vocal",
    "negative_style_prompt": None,
    "sound_scene": None,
    "hooks_prompt": None,
    "effects_prompt": None,
    "chorus_vocal_style": None,
    "description": "from reference",
}


def fake_preset_fields(analysis):
    return PresetCreate(**PRESET_FIELDS)


ANALYSIS = ReferenceAnalysis(
    theme="lost love",
    emotions=["melancholy"],
    genre_context=["ballad"],
    bpm=72,
    energy="low",
    structure=["[VERSE]", "[CHORUS]"],
    delivery="sung",
    rhyme_and_flow="AABB couplets",
    transcript="[VERSE]\nrain on the glass",
)


def read_reference_analysis(song_id):
    with SessionLocal() as db:
        song = db.get(Song, uuid.UUID(song_id))
        return song.analysis_status, song.analysis


def test_reference_analysis_success_stores_result_and_marks_done(client, monkeypatch):
    calls = []

    def fake_analyze(audio, audio_format):
        calls.append((audio, audio_format))
        return ANALYSIS

    monkeypatch.setattr(songs, "analyze_reference_audio", fake_analyze)
    monkeypatch.setattr(songs, "build_reference_preset_fields", fake_preset_fields)

    response = upload_reference(client, content=b"fake audio")

    assert response.status_code == 201
    assert calls == [(b"fake audio", "mp3")]
    status_value, analysis = read_reference_analysis(response.json()["id"])
    assert status_value == "done"
    assert analysis == ANALYSIS.model_dump() | {GENERATED_PRESET_KEY: PRESET_FIELDS}


def test_reference_analysis_success_creates_linked_preset_with_same_fields(
    client, monkeypatch
):
    monkeypatch.setattr(songs, "analyze_reference_audio", lambda audio, audio_format: ANALYSIS)
    monkeypatch.setattr(songs, "build_reference_preset_fields", fake_preset_fields)

    response = upload_reference(client, content=b"fake audio")

    song_id = response.json()["id"]
    with SessionLocal() as db:
        song = db.get(Song, uuid.UUID(song_id))
        preset = db.get(Preset, song.preset_id)
        assert preset is not None
        assert preset.name == PRESET_FIELDS["name"]
        assert preset.genre == PRESET_FIELDS["genre"]
        assert preset.bpm_min == PRESET_FIELDS["bpm_min"]
        assert preset.bpm_max == PRESET_FIELDS["bpm_max"]
        assert preset.style_prompt == PRESET_FIELDS["style_prompt"]
        assert preset.description == PRESET_FIELDS["description"]

    presets_response = client.get("/presets")
    assert any(item["id"] == str(song.preset_id) for item in presets_response.json())


@pytest.mark.parametrize(
    "error",
    [
        ReferenceAnalysisInvalidJSONError("not valid JSON"),
        ReferenceAnalysisValidationError("does not match schema"),
        AIServiceError("AI provider returned HTTP 500"),
    ],
)
def test_reference_analysis_failure_marks_failed_without_partial_analysis(
    client, monkeypatch, error
):
    def failing_analyze(audio, audio_format):
        raise error

    monkeypatch.setattr(songs, "analyze_reference_audio", failing_analyze)
    monkeypatch.setattr(songs, "build_reference_preset_fields", fake_preset_fields)

    response = upload_reference(client)

    assert response.status_code == 201
    status_value, analysis = read_reference_analysis(response.json()["id"])
    assert status_value == "failed"
    assert analysis is None
    assert count_reference_rows() == 1


def test_reference_analysis_save_failure_marks_failed_without_partial_preset(
    client, monkeypatch
):
    def failing_merge(db, song, fields):
        raise RuntimeError("database write failed")

    monkeypatch.setattr(songs, "analyze_reference_audio", lambda audio, audio_format: ANALYSIS)
    monkeypatch.setattr(songs, "build_reference_preset_fields", fake_preset_fields)
    monkeypatch.setattr(songs, "merge_reference_preset", failing_merge)

    response = upload_reference(client)

    assert response.status_code == 201
    song_id = response.json()["id"]
    status_value, analysis = read_reference_analysis(song_id)
    assert status_value == "failed"
    assert analysis is None
    with SessionLocal() as db:
        assert db.get(Song, uuid.UUID(song_id)).preset_id is None


ANALYSIS_AFTER_REANALYSIS = ReferenceAnalysis(
    theme="joy",
    emotions=["hope"],
    genre_context=["pop"],
    bpm=120,
    energy="high",
    structure=["[CHORUS]"],
    delivery="sung",
    rhyme_and_flow="ABAB",
    transcript="",
)


def create_done_reference(client, monkeypatch, analysis=ANALYSIS):
    monkeypatch.setattr(
        songs, "analyze_reference_audio", lambda audio, audio_format: analysis
    )
    monkeypatch.setattr(songs, "build_reference_preset_fields", fake_preset_fields)
    response = upload_reference(client)
    assert response.status_code == 201
    return response.json()["id"]


def insert_reference_row(analysis_status):
    with SessionLocal() as db:
        song = Song(
            title="pending.mp3", kind="reference", analysis_status=analysis_status
        )
        db.add(song)
        db.commit()
        return str(song.id)


def test_reference_preset_is_listed_in_common_presets(client, monkeypatch):
    song_id = create_done_reference(client, monkeypatch)
    with SessionLocal() as db:
        preset_id = str(db.get(Song, uuid.UUID(song_id)).preset_id)

    response = client.get("/presets")

    assert response.status_code == 200
    assert preset_id in [item["id"] for item in response.json()]


def test_reference_preset_is_available_for_song_selection(client, monkeypatch):
    song_id = create_done_reference(client, monkeypatch)
    with SessionLocal() as db:
        preset_id = str(db.get(Song, uuid.UUID(song_id)).preset_id)

    draft = create_song(client, title="Draft", preset_id=preset_id)

    assert draft["preset_id"] == preset_id


def test_reference_preset_is_editable_through_common_presets(client, monkeypatch):
    song_id = create_done_reference(client, monkeypatch)
    with SessionLocal() as db:
        preset_id = str(db.get(Song, uuid.UUID(song_id)).preset_id)

    response = client.patch(f"/presets/{preset_id}", json={"bpm_min": 60})

    assert response.status_code == 200
    assert response.json()["bpm_min"] == 60


def test_reanalysis_keeps_manually_edited_preset_fields(client, monkeypatch):
    song_id = create_done_reference(client, monkeypatch)
    with SessionLocal() as db:
        preset_id = str(db.get(Song, uuid.UUID(song_id)).preset_id)
    client.patch(f"/presets/{preset_id}", json={"bpm_min": 60})
    monkeypatch.setattr(
        songs,
        "analyze_reference_audio",
        lambda audio, audio_format: ANALYSIS_AFTER_REANALYSIS,
    )

    songs.run_reference_analysis(uuid.UUID(song_id), b"new audio", "mp3")

    status_value, _ = read_reference_analysis(song_id)
    assert status_value == "done"
    preset = client.get(f"/presets/{preset_id}").json()
    assert preset["bpm_min"] == 60
    assert preset["bpm_max"] == PRESET_FIELDS["bpm_max"]


def test_failed_reanalysis_keeps_preset_and_marks_failed(client, monkeypatch):
    song_id = create_done_reference(client, monkeypatch)
    with SessionLocal() as db:
        preset_id = str(db.get(Song, uuid.UUID(song_id)).preset_id)
    monkeypatch.setattr(
        songs,
        "analyze_reference_audio",
        lambda audio, audio_format: (_ for _ in ()).throw(AIServiceError("boom")),
    )

    songs.run_reference_analysis(uuid.UUID(song_id), b"new audio", "mp3")

    status_value, _ = read_reference_analysis(song_id)
    assert status_value == "failed"
    assert client.get(f"/presets/{preset_id}").status_code == 200


def test_upload_reference_rejects_ogg_before_provider_call(client, monkeypatch):
    def fail_if_called(audio, audio_format):
        raise AssertionError("provider must not be called")

    monkeypatch.setattr(songs, "analyze_reference_audio", fail_if_called)

    response = upload_reference(client, file_name="night.ogg", content_type="audio/ogg")

    assert response.status_code == 415
    assert count_reference_rows() == 0


@pytest.mark.parametrize(
    "payload", [{"analysis": {"bpm": 90}}, {"lyrics": "new verse"}]
)
def test_patch_reference_analysis_or_lyrics_returns_409(client, monkeypatch, payload):
    song_id = create_done_reference(client, monkeypatch)

    response = client.patch(f"/songs/{song_id}", json=payload)

    assert response.status_code == 409
    _, stored = read_reference_analysis(song_id)
    assert stored == ANALYSIS.model_dump() | {GENERATED_PRESET_KEY: PRESET_FIELDS}


def test_list_songs_excludes_reference_rows(client, monkeypatch):
    create_done_reference(client, monkeypatch)
    draft = create_song(client, title="Draft")

    response = client.get("/songs")

    assert response.status_code == 200
    assert [song["id"] for song in response.json()] == [draft["id"]]


def test_reference_analysis_unexpected_error_marks_failed_and_logs_class_only(
    client, monkeypatch, caplog
):
    def crashing_analyze(audio, audio_format):
        raise RuntimeError("secret-payload")

    monkeypatch.setattr(songs, "analyze_reference_audio", crashing_analyze)

    response = upload_reference(client)

    assert response.status_code == 201
    status_value, analysis = read_reference_analysis(response.json()["id"])
    assert status_value == "failed"
    assert analysis is None
    assert "RuntimeError" in caplog.text
    assert "secret-payload" not in caplog.text
