import json
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Message, Preset, Song

ModelT = TypeVar("ModelT", bound=BaseModel)

PRESET_CONTEXT_FIELDS = (
    "genre",
    "bpm_min",
    "bpm_max",
    "energy",
    "style_prompt",
    "negative_style_prompt",
    "sound_scene",
    "hooks_prompt",
    "effects_prompt",
    "chorus_vocal_style",
)


class AIServiceError(Exception):
    pass


def _non_empty(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if value is not None and value != ""
    }


def build_song_context(song: Song, preset: Preset | None = None) -> dict[str, Any]:
    analysis = song.analysis or {}
    track_settings = song.track_settings or {}
    generation_settings = song.generation_settings or {}
    context = _non_empty(
        {
            "idea": song.idea,
            "title": song.title,
            "genre": analysis.get("genre"),
            "bpm": analysis.get("bpm") or generation_settings.get("bpm"),
            "emotion": analysis.get("emotion"),
            "lyrics": song.lyrics,
            "style_prompt": track_settings.get("style_prompt"),
            "negative_style_prompt": track_settings.get("negative_style_prompt"),
            "performance": track_settings.get("performance"),
        }
    )
    if preset is not None:
        preset_context = _non_empty(
            {field: getattr(preset, field) for field in PRESET_CONTEXT_FIELDS}
        )
        if preset_context:
            context["preset"] = preset_context
    return context


def request_completion(
    system_prompt: str, user_prompt: str, transport: httpx.BaseTransport | None = None
) -> str:
    if not settings.ai_api_key:
        raise AIServiceError("AI provider is not configured")
    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"}
    try:
        with httpx.Client(
            base_url=settings.ai_base_url,
            timeout=settings.ai_timeout_seconds,
            transport=transport,
        ) as client:
            response = client.post("chat/completions", json=payload, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise AIServiceError("AI provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        raise AIServiceError(
            f"AI provider returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        raise AIServiceError("AI provider request failed") from exc
    try:
        return response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise AIServiceError("AI provider returned an unexpected response") from exc


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        return text
    return text[start : end + 1]


def parse_structured(content: str, schema: type[ModelT]) -> ModelT:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        return schema.model_validate(json.loads(text, strict=False))
    except (ValueError, ValidationError):
        pass
    try:
        return schema.model_validate(json.loads(_extract_json_object(text), strict=False))
    except (ValueError, ValidationError) as exc:
        raise AIServiceError("AI response does not match expected schema") from exc


def log_message(
    db: Session,
    song: Song,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        Message(
            song_id=song.id,
            role=role,
            content=content,
            message_metadata=metadata,
        )
    )
    db.commit()
