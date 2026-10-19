import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import auth, presets
from app.config import settings
from app.database import Base, engine
from app.presets import router as presets_router
from app.services.ai import AIServiceError

PRESET_PAYLOAD = {
    "name": "Late night rap",
    "genre": "rap",
    "bpm_min": 80,
    "bpm_max": 100,
    "energy": 0.7,
    "style_prompt": "dark piano, heavy 808",
    "negative_style_prompt": "no vocals distortion",
    "sound_scene": "night city",
    "hooks_prompt": "short catchy hook",
    "effects_prompt": "reverb tail",
    "chorus_vocal_style": "melodic and open",
    "description": "for late night verses",
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
    app.include_router(presets_router)
    test_client = TestClient(app)
    response = test_client.post(
        "/auth/login",
        json={"email": "admin@example.com", "password": "correct-password"},
    )
    assert response.status_code == 200
    return test_client


def fake_completion(content):
    def _call(system_prompt, user_prompt, transport=None):
        return content

    return _call


def create_preset(client, **overrides):
    response = client.post("/presets", json={**PRESET_PAYLOAD, **overrides})
    assert response.status_code == 201
    return response.json()


def test_create_preset_returns_201_with_all_fields(client):
    response = client.post("/presets", json=PRESET_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    for field, value in PRESET_PAYLOAD.items():
        assert body[field] == value
    assert uuid.UUID(body["id"])
    assert body["created_at"]
    assert body["updated_at"]


def test_list_presets_returns_all_created_presets(client):
    first = create_preset(client, name="First")
    second = create_preset(client, name="Second")

    response = client.get("/presets")

    assert response.status_code == 200
    ids = [preset["id"] for preset in response.json()]
    assert ids == [first["id"], second["id"]]


def test_get_preset_returns_preset(client):
    created = create_preset(client)

    response = client.get(f"/presets/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_missing_preset_returns_404(client):
    response = client.get(f"/presets/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Preset not found"


def test_update_preset_changes_only_given_fields(client):
    created = create_preset(client)

    response = client.patch(
        f"/presets/{created['id']}", json={"name": "Renamed", "energy": 0.9}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["energy"] == 0.9
    assert body["genre"] == PRESET_PAYLOAD["genre"]
    assert body["style_prompt"] == PRESET_PAYLOAD["style_prompt"]
    assert body["bpm_min"] == PRESET_PAYLOAD["bpm_min"]


def test_update_preset_can_clear_optional_field(client):
    created = create_preset(client)

    response = client.patch(f"/presets/{created['id']}", json={"description": None})

    assert response.status_code == 200
    assert response.json()["description"] is None


def test_update_missing_preset_returns_404(client):
    response = client.patch(f"/presets/{uuid.uuid4()}", json={"name": "Missing"})

    assert response.status_code == 404


def test_update_preset_with_bpm_min_greater_than_bpm_max_returns_422(client):
    created = create_preset(client)

    response = client.patch(
        f"/presets/{created['id']}", json={"bpm_min": 150, "bpm_max": 100}
    )

    assert response.status_code == 422


def test_update_preset_only_bpm_min_above_stored_bpm_max_returns_422(client):
    created = create_preset(client)

    response = client.patch(f"/presets/{created['id']}", json={"bpm_min": 150})

    assert response.status_code == 422
    stored = client.get(f"/presets/{created['id']}").json()
    assert stored["bpm_min"] == PRESET_PAYLOAD["bpm_min"]


def test_update_preset_only_bpm_max_below_stored_bpm_min_returns_422(client):
    created = create_preset(client)

    response = client.patch(f"/presets/{created['id']}", json={"bpm_max": 50})

    assert response.status_code == 422
    stored = client.get(f"/presets/{created['id']}").json()
    assert stored["bpm_max"] == PRESET_PAYLOAD["bpm_max"]


def test_update_preset_bpm_within_stored_range_returns_200(client):
    created = create_preset(client)

    response = client.patch(f"/presets/{created['id']}", json={"bpm_min": 90})

    assert response.status_code == 200
    assert response.json()["bpm_min"] == 90


def test_update_preset_clears_bpm_min_when_bpm_max_stored(client):
    created = create_preset(client)

    response = client.patch(f"/presets/{created['id']}", json={"bpm_min": None})

    assert response.status_code == 200
    assert response.json()["bpm_min"] is None


def test_delete_preset_returns_204_and_removes_it(client):
    created = create_preset(client)

    response = client.delete(f"/presets/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/presets/{created['id']}").status_code == 404


def test_delete_missing_preset_returns_404(client):
    response = client.delete(f"/presets/{uuid.uuid4()}")

    assert response.status_code == 404


def test_create_preset_with_bpm_min_greater_than_bpm_max_returns_422(client):
    payload = {**PRESET_PAYLOAD, "bpm_min": 120, "bpm_max": 100}
    response = client.post("/presets", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["name", "genre"])
def test_create_preset_without_required_field_returns_422(client, field):
    payload = {key: value for key, value in PRESET_PAYLOAD.items() if key != field}

    response = client.post("/presets", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize("field", ["name", "genre"])
def test_create_preset_with_empty_required_field_returns_422(client, field):
    response = client.post("/presets", json={**PRESET_PAYLOAD, field: ""})

    assert response.status_code == 422


def test_create_preset_with_only_required_fields_returns_201(client):
    response = client.post("/presets", json={"name": "Minimal", "genre": "pop"})

    assert response.status_code == 201
    body = response.json()
    assert body["bpm_min"] is None
    assert body["sound_scene"] is None
    assert body["hooks_prompt"] is None
    assert body["effects_prompt"] is None
    assert body["chorus_vocal_style"] is None


def test_generate_preset_creates_preset_from_prompt(client, monkeypatch):
    content = json.dumps(
        {
            "name": "Underground",
            "genre": "underground rap",
            "bpm_min": 88,
            "bpm_max": 92,
        }
    )
    monkeypatch.setattr(presets, "request_completion", lambda system, prompt: content)

    response = client.post(
        "/presets/generate", json={"prompt": "underground, rap 90 bpm"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Underground"
    assert body["bpm_min"] == 88
    assert client.get(f"/presets/{body['id']}").status_code == 200


def test_generate_preset_with_provider_error_returns_502(client, monkeypatch):
    def failing(system, prompt):
        raise AIServiceError("AI provider request failed")

    monkeypatch.setattr(presets, "request_completion", failing)

    response = client.post("/presets/generate", json={"prompt": "rock"})

    assert response.status_code == 502


def test_generate_preset_with_invalid_bpm_returns_502(client, monkeypatch):
    content = json.dumps(
        {"name": "Bad", "genre": "rock", "bpm_min": 150, "bpm_max": 100}
    )
    monkeypatch.setattr(presets, "request_completion", lambda system, prompt: content)

    response = client.post("/presets/generate", json={"prompt": "rock"})

    assert response.status_code == 502


def test_generate_preset_with_empty_prompt_returns_422(client):
    response = client.post("/presets/generate", json={"prompt": ""})

    assert response.status_code == 422


def test_presets_without_session_return_401(client):
    client.cookies.clear()

    response = client.get("/presets")

    assert response.status_code == 401


def test_generate_preset_creates_preset_from_fake_completion(client, monkeypatch):
    generated = {
        **PRESET_PAYLOAD,
        "name": "Underground rap",
        "bpm_min": 88,
        "bpm_max": 92,
    }
    monkeypatch.setattr(
        presets, "request_completion", fake_completion(json.dumps(generated))
    )

    response = client.post(
        "/presets/generate", json={"prompt": "underground, rap 90 bpm"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Underground rap"
    assert body["genre"] == "rap"
    assert body["bpm_min"] == 88
    assert client.get(f"/presets/{body['id']}").status_code == 200


def test_generate_preset_rejects_invalid_ai_response(client, monkeypatch):
    invalid = {**PRESET_PAYLOAD, "bpm_min": 150, "bpm_max": 100}
    monkeypatch.setattr(
        presets, "request_completion", fake_completion(json.dumps(invalid))
    )

    response = client.post("/presets/generate", json={"prompt": "fast rap"})

    assert response.status_code == 502
    assert client.get("/presets").json() == []


def test_generate_preset_provider_error_returns_502(client, monkeypatch):
    def failing(system_prompt, user_prompt, transport=None):
        raise AIServiceError("AI provider timed out")

    monkeypatch.setattr(presets, "request_completion", failing)

    response = client.post("/presets/generate", json={"prompt": "lofi"})

    assert response.status_code == 502


def test_generate_preset_rejects_empty_prompt(client):
    response = client.post("/presets/generate", json={"prompt": ""})

    assert response.status_code == 422
