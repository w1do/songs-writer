import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import auth
from app.config import settings
from app.database import Base, engine
from app.presets import router as presets_router
from app.songs import router as songs_router


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(settings, "admin_email", "admin@example.com")
    monkeypatch.setattr(settings, "admin_password", "correct-password")
    monkeypatch.setattr(settings, "session_secret", "test-secret")

    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE songs ADD COLUMN IF NOT EXISTS story TEXT"))
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
