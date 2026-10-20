import base64
import json
import logging
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Message, Preset, Song
from app.schemas import PresetCreate, ReferenceAnalysis

ModelT = TypeVar("ModelT", bound=BaseModel)

logger = logging.getLogger(__name__)

AUDIO_INPUT_FORMATS = frozenset({"wav", "mp3", "flac", "m4a"})

REFERENCE_ANALYSIS_SYSTEM_PROMPT = (
    "Ты анализируешь аудио песни-референса. Ответь только JSON-объектом без пояснений "
    "и markdown со следующими полями: theme (строка), emotions (список строк), "
    "genre_context (список строк; жанр — это контекст, а не жёсткое правило), "
    "bpm (целое число или null), energy (строка), structure (список строк, например "
    "[VERSE], [CHORUS]), delivery (строка: речитатив, пение или смешанная), "
    "rhyme_and_flow (строка), transcript (строка с текстом песни; для инструментала пустая строка)."
)
REFERENCE_ANALYSIS_USER_PROMPT = (
    "Проанализируй аудио референса и верни JSON-объект по описанной схеме."
)

PRESET_GENERATE_SYSTEM_PROMPT = (
    "Ты создаёшь пресет жанра для генератора музыки "
    "по короткому описанию пользователя. "
    "Ответь только JSON-объектом с полями: "
    "name (строка, до 200 символов), genre (строка), "
    "bpm_min и bpm_max (целые, bpm_min <= bpm_max), "
    "energy (число 0-1), style_prompt, negative_style_prompt, "
    "sound_scene, hooks_prompt, "
    "effects_prompt, chorus_vocal_style, description (строки или null). "
    "Не пиши текст песни. Суммарная длина полей style (genre, bpm, energy, "
    "style_prompt, sound_scene, hooks_prompt, effects_prompt, chorus_vocal_style, "
    "description) не более 1000 символов; negative_style_prompt не более 1000 символов."
)

GENERATED_PRESET_KEY = "generated_preset"

STYLE_CONTEXT_GUIDANCE = (
    "Ориентир стиля из песни-референса. Это подсказка, а не жёсткие правила: "
    "учитывай подачу, рифмовку, энергию и эмоции как ориентир. "
    "Transcript — текст референса, на него можно опираться, но не копировать его."
)

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


class ReferenceAnalysisError(AIServiceError):
    pass


class ReferenceAnalysisInvalidJSONError(ReferenceAnalysisError):
    pass


class ReferenceAnalysisValidationError(ReferenceAnalysisError):
    pass


def _non_empty(values: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in values.items()
        if value is not None and value != ""
    }


CHAT_PRESET_FIELDS = (
    "name",
    "genre",
    "bpm_min",
    "bpm_max",
    "energy",
    "style_prompt",
    "negative_style_prompt",
    "hooks_prompt",
    "effects_prompt",
    "chorus_vocal_style",
)


def build_chat_context(
    song: Song, preset: Preset | None, history: list[Message]
) -> dict[str, Any]:
    analysis = song.analysis or {}
    context = _non_empty(
        {
            "story": song.story,
            "idea": song.idea,
            "genre": analysis.get("genre"),
            "lyrics": song.lyrics,
        }
    )
    if preset is not None:
        preset_context = _non_empty(
            {field: getattr(preset, field) for field in CHAT_PRESET_FIELDS}
        )
        if preset_context:
            context["preset"] = preset_context
    if history:
        context["messages"] = [
            {"role": message.role, "content": message.content} for message in history
        ]
    return context


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


def _post_chat_completion(
    payload: dict[str, Any],
    transport: httpx.BaseTransport | None,
    timeout_seconds: float | None = None,
) -> str:
    if not settings.ai_api_key:
        logger.error("AI provider call skipped: API key is not configured")
        raise AIServiceError("AI provider is not configured")
    headers = {"Authorization": f"Bearer {settings.ai_api_key}"}
    model = payload.get("model")
    timeout = timeout_seconds or settings.ai_timeout_seconds
    try:
        with httpx.Client(
            base_url=settings.ai_base_url,
            timeout=timeout,
            transport=transport,
        ) as client:
            response = client.post("chat/completions", json=payload, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.error(
            "AI provider timed out: model=%s timeout=%ss error=%s",
            model,
            timeout,
            type(exc).__name__,
        )
        raise AIServiceError("AI provider timed out") from exc
    except httpx.HTTPStatusError as exc:
        logger.error(
            "AI provider returned HTTP error: model=%s status=%s",
            model,
            exc.response.status_code,
        )
        raise AIServiceError(
            f"AI provider returned HTTP {exc.response.status_code}"
        ) from exc
    except httpx.HTTPError as exc:
        logger.error(
            "AI provider request failed: model=%s error=%s",
            model,
            type(exc).__name__,
        )
        raise AIServiceError("AI provider request failed") from exc
    try:
        content = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        logger.error(
            "AI provider returned unexpected payload: model=%s error=%s",
            model,
            type(exc).__name__,
        )
        raise AIServiceError("AI provider returned an unexpected response") from exc
    if not isinstance(content, str):
        logger.error(
            "AI provider returned non-text content: model=%s content_type=%s",
            model,
            type(content).__name__,
        )
        raise AIServiceError("AI provider returned an unexpected response")
    return content


def request_completion(
    system_prompt: str, user_prompt: str, transport: httpx.BaseTransport | None = None
) -> str:
    payload = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    return _post_chat_completion(payload, transport)


def request_reference_analysis(
    audio: bytes, audio_format: str, transport: httpx.BaseTransport | None = None
) -> str:
    if audio_format not in AUDIO_INPUT_FORMATS:
        raise AIServiceError("Audio format is not supported for analysis")
    payload = {
        "model": settings.ai_audio_model,
        "messages": [
            {"role": "system", "content": REFERENCE_ANALYSIS_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": REFERENCE_ANALYSIS_USER_PROMPT},
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": base64.b64encode(audio).decode("ascii"),
                            "format": audio_format,
                        },
                    },
                ],
            },
        ],
    }
    return _post_chat_completion(
        payload, transport, timeout_seconds=settings.ai_audio_timeout_seconds
    )


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
        logger.error(
            "AI response does not match expected schema: schema=%s error=%s",
            schema.__name__,
            type(exc).__name__,
        )
        raise AIServiceError("AI response does not match expected schema") from exc


def _normalize_reference_analysis(data: Any) -> Any:
    if not isinstance(data, dict):
        return data
    fields = ReferenceAnalysis.model_fields
    normalized = {key: value for key, value in data.items() if key in fields}
    for key in ("theme", "energy", "delivery", "rhyme_and_flow", "transcript"):
        value = normalized.get(key)
        if value is None and key == "transcript":
            normalized[key] = ""
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            normalized[key] = str(value)
    for key in ("emotions", "genre_context", "structure"):
        value = normalized.get(key)
        if isinstance(value, str):
            normalized[key] = [value]
        elif isinstance(value, list):
            normalized[key] = [
                str(item) for item in value if item is not None
            ]
    bpm = normalized.get("bpm")
    if isinstance(bpm, float):
        normalized["bpm"] = round(bpm)
    elif isinstance(bpm, str) and bpm.strip().isdigit():
        normalized["bpm"] = int(bpm.strip())
    return normalized


def parse_reference_analysis(content: str) -> ReferenceAnalysis:
    try:
        data = json.loads(_extract_json_object(content.strip()), strict=False)
    except ValueError as exc:
        logger.error(
            "Reference analysis response is not valid JSON: error=%s length=%s",
            type(exc).__name__,
            len(content),
        )
        raise ReferenceAnalysisInvalidJSONError(
            "Reference analysis response is not valid JSON"
        ) from exc
    try:
        return ReferenceAnalysis.model_validate(_normalize_reference_analysis(data))
    except ValidationError as exc:
        logger.error(
            "Reference analysis response does not match schema: fields=%s",
            sorted({".".join(str(part) for part in error["loc"]) for error in exc.errors()}),
        )
        raise ReferenceAnalysisValidationError(
            "Reference analysis response does not match expected schema"
        ) from exc


def analyze_reference_audio(
    audio: bytes, audio_format: str, transport: httpx.BaseTransport | None = None
) -> ReferenceAnalysis:
    content = request_reference_analysis(audio, audio_format, transport=transport)
    return parse_reference_analysis(content)


def build_reference_preset_fields(analysis: ReferenceAnalysis) -> PresetCreate:
    content = request_completion(
        PRESET_GENERATE_SYSTEM_PROMPT,
        json.dumps(analysis.model_dump(), ensure_ascii=False),
    )
    return parse_structured(content, PresetCreate)


def build_style_context(preset: Preset) -> dict[str, Any]:
    return {
        "guidance": STYLE_CONTEXT_GUIDANCE,
        **_non_empty({field: getattr(preset, field) for field in PRESET_CONTEXT_FIELDS}),
    }


def merge_reference_preset(db: Session, song: Song, fields: PresetCreate) -> Preset:
    generated = fields.model_dump()
    previous = (song.analysis or {}).get(GENERATED_PRESET_KEY) or {}
    preset = db.get(Preset, song.preset_id) if song.preset_id else None
    if preset is None:
        preset = Preset(**generated)
        db.add(preset)
    else:
        for field, value in generated.items():
            if field in previous and getattr(preset, field) != previous[field]:
                continue
            setattr(preset, field, value)
    db.flush()
    return preset


def log_message(
    db: Session,
    song: Song,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
    commit: bool = True,
) -> Message:
    message = Message(
        song_id=song.id,
        role=role,
        content=content,
        message_metadata=metadata,
    )
    db.add(message)
    if commit:
        db.commit()
    return message
