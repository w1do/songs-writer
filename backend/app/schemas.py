import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def check_bpm_range(bpm_min: int | None, bpm_max: int | None) -> None:
    if bpm_min is not None and bpm_max is not None and bpm_min > bpm_max:
        raise ValueError("bpm_min must be less than or equal to bpm_max")


STYLE_TEXT_LIMIT = 1000
NEGATIVE_STYLE_LIMIT = 1000

_STYLE_PARTS = (
    ("genre", "Genre"),
    ("bpm", "BPM"),
    ("energy", "Energy"),
    ("style_prompt", "Style"),
    ("sound_scene", "Sound scene"),
    ("hooks_prompt", "Hooks"),
    ("effects_prompt", "Effects"),
    ("chorus_vocal_style", "Chorus vocal style"),
    ("description", "Description"),
)
_TRIM_ORDER = (
    "description",
    "chorus_vocal_style",
    "effects_prompt",
    "hooks_prompt",
    "sound_scene",
    "style_prompt",
)


def _style_length(data: dict[str, Any]) -> int:
    bpm_min, bpm_max = data.get("bpm_min"), data.get("bpm_max")
    bpm = ""
    if bpm_min is not None and bpm_max is not None:
        bpm = f"{bpm_min}-{bpm_max}"
    elif bpm_min is not None or bpm_max is not None:
        bpm = str(bpm_min if bpm_min is not None else bpm_max)
    lines = []
    for key, label in _STYLE_PARTS:
        value = bpm if key == "bpm" else data.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            lines.append(f"{label}: {text}")
    return len("\n".join(lines))


def fit_preset_limits(data: Any) -> Any:
    """Trim preset text fields so copied style and negative are <= 1000 chars each."""
    if not isinstance(data, dict):
        return data
    data = dict(data)
    negative = data.get("negative_style_prompt")
    if isinstance(negative, str) and len(negative.strip()) > NEGATIVE_STYLE_LIMIT:
        data["negative_style_prompt"] = negative.strip()[:NEGATIVE_STYLE_LIMIT].rstrip()
    for key in _TRIM_ORDER:
        excess = _style_length(data) - STYLE_TEXT_LIMIT
        if excess <= 0:
            break
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            continue
        value = value.strip()
        data[key] = value[: max(0, len(value) - excess)].rstrip() or None
    return data


class SongCreate(BaseModel):
    idea: str = Field(min_length=1)
    title: str | None = Field(default=None, max_length=300)
    preset_id: uuid.UUID | None = None


class SongUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    idea: str | None = Field(default=None, min_length=1)
    story: str | None = Field(default=None, max_length=10000)
    lyrics: str | None = None
    track_settings: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    generation_settings: dict[str, Any] | None = None
    preset_id: uuid.UUID | None = None


class SongRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    idea: str | None
    story: str | None
    lyrics: str | None
    track_settings: dict[str, Any] | None
    analysis: dict[str, Any] | None
    generation_settings: dict[str, Any] | None
    preset_id: uuid.UUID | None
    kind: str
    analysis_status: str | None
    created_at: datetime
    updated_at: datetime


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    content: str
    created_at: datetime


class SongChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value


class ChatAIResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    reply: str = Field(min_length=1)
    lyrics: str | None = None


class SongChatResponse(BaseModel):
    reply: str
    lyrics: str | None
    messages: list[MessageRead]


class SongListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    idea: str | None
    preset_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


class SongReferenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str | None
    kind: str
    analysis_status: str | None


class SongExport(BaseModel):
    song_id: uuid.UUID
    title: str | None
    lyrics: str | None
    style_prompt: str | None
    negative_style_prompt: str | None
    performance: str | None
    generation_settings: dict[str, Any] | None


class PresetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    genre: str = Field(min_length=1, max_length=100)
    bpm_min: int | None = None
    bpm_max: int | None = None
    energy: float | None = None
    style_prompt: str | None = None
    negative_style_prompt: str | None = None
    sound_scene: str | None = None
    hooks_prompt: str | None = None
    effects_prompt: str | None = None
    chorus_vocal_style: str | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def fit_limits(cls, data: Any) -> Any:
        return fit_preset_limits(data)

    @model_validator(mode="after")
    def validate_bpm(self) -> "PresetCreate":
        check_bpm_range(self.bpm_min, self.bpm_max)
        return self


class PresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    genre: str | None = Field(default=None, min_length=1, max_length=100)
    bpm_min: int | None = None
    bpm_max: int | None = None
    energy: float | None = None
    style_prompt: str | None = None
    negative_style_prompt: str | None = None
    sound_scene: str | None = None
    hooks_prompt: str | None = None
    effects_prompt: str | None = None
    chorus_vocal_style: str | None = None
    description: str | None = None

    @model_validator(mode="before")
    @classmethod
    def fit_limits(cls, data: Any) -> Any:
        return fit_preset_limits(data)

    @model_validator(mode="after")
    def validate_bpm(self) -> "PresetUpdate":
        check_bpm_range(self.bpm_min, self.bpm_max)
        return self


class PresetGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=1000)


class PresetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    genre: str
    bpm_min: int | None
    bpm_max: int | None
    energy: float | None
    style_prompt: str | None
    negative_style_prompt: str | None
    sound_scene: str | None
    hooks_prompt: str | None
    effects_prompt: str | None
    chorus_vocal_style: str | None
    description: str | None
    created_at: datetime
    updated_at: datetime


class AnalyzeIdeaResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str = Field(min_length=1)
    emotion: str = Field(min_length=1)
    genre: str = Field(min_length=1)
    bpm: int = Field(ge=40, le=220)
    energy: float = Field(ge=0, le=1)
    structure: list[str] = Field(min_length=1)


class ReferenceAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: str
    emotions: list[str]
    genre_context: list[str]
    bpm: int | None
    energy: str
    structure: list[str]
    delivery: str
    rhyme_and_flow: str
    transcript: str


class LineActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: Literal["variants", "continue", "rewrite", "rhyme", "flow", "vocal"]
    line: str = Field(min_length=1)
    selection: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_selection(self) -> "LineActionRequest":
        if self.selection is not None and self.selection not in self.line:
            raise ValueError("selection must be a part of line")
        return self


class LineActionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variants: list[str] = Field(min_length=1, max_length=5)
    note: str | None = None


class ContinueSectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: str = Field(min_length=1)


class ContinueSectionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variants: list[str] = Field(min_length=1, max_length=5)
    note: str | None = None


class HookResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variants: list[str] = Field(min_length=1, max_length=5)


class ChorusResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variants: list[list[str]] = Field(min_length=1, max_length=5)


class DraftLyricsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preset_id: uuid.UUID | None = None


class LyricsDraftResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    variants: list[str] = Field(min_length=1)

    @field_validator("variants", mode="before")
    @classmethod
    def join_line_lists(cls, value: Any) -> Any:
        if isinstance(value, list):
            return [
                "\n".join(str(line) for line in item) if isinstance(item, list) else item
                for item in value
            ]
        return value

    @field_validator("variants")
    @classmethod
    def normalize_variants(cls, value: list[str]) -> list[str]:
        variants = [item.strip() for item in value if item.strip()][:3]
        if not variants:
            raise ValueError("variants must contain non-empty text")
        return variants


class StructureResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sections: list[str] = Field(min_length=1)
    reason: str | None = None


class FinishSongResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comments: list[str] = Field(min_length=1)


class PrepareTrackResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    style_prompt: str = Field(min_length=1)
    negative_style_prompt: str | None = None
    performance: str | None = None
    generation_settings: dict[str, Any] = Field(default_factory=dict)
