import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.database import get_db
from app.models import Preset
from app.schemas import (
    PresetCreate,
    PresetGenerateRequest,
    PresetRead,
    PresetUpdate,
    check_bpm_range,
)
from app.services.ai import AIServiceError, parse_structured, request_completion

router = APIRouter(prefix="/presets", dependencies=[Depends(require_session)])

PRESET_GENERATE_SYSTEM_PROMPT = (
    "Ты создаёшь пресет жанра для генератора музыки "
    "по короткому описанию пользователя. "
    "Ответь только JSON-объектом с полями: "
    "name (строка, до 200 символов), genre (строка), "
    "bpm_min и bpm_max (целые, bpm_min <= bpm_max), "
    "energy (число 0-1), style_prompt, negative_style_prompt, "
    "sound_scene, hooks_prompt, "
    "effects_prompt, chorus_vocal_style, description (строки или null). "
    "Не пиши текст песни."
)


def _get_preset(db: Session, preset_id: uuid.UUID) -> Preset:
    preset = db.get(Preset, preset_id)
    if preset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Preset not found"
        )
    return preset


@router.post("", status_code=status.HTTP_201_CREATED, response_model=PresetRead)
def create_preset(body: PresetCreate, db: Session = Depends(get_db)):
    preset = Preset(**body.model_dump())
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.post(
    "/generate", status_code=status.HTTP_201_CREATED, response_model=PresetRead
)
def generate_preset(body: PresetGenerateRequest, db: Session = Depends(get_db)):
    try:
        content = request_completion(PRESET_GENERATE_SYSTEM_PROMPT, body.prompt)
        draft = parse_structured(content, PresetCreate)
    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    preset = Preset(**draft.model_dump())
    db.add(preset)
    db.commit()
    db.refresh(preset)
    return preset


@router.get("", response_model=list[PresetRead])
def list_presets(db: Session = Depends(get_db)):
    return db.scalars(select(Preset).order_by(Preset.created_at)).all()


@router.get("/{preset_id}", response_model=PresetRead)
def get_preset(preset_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_preset(db, preset_id)


@router.patch("/{preset_id}", response_model=PresetRead)
def update_preset(
    preset_id: uuid.UUID, body: PresetUpdate, db: Session = Depends(get_db)
):
    preset = _get_preset(db, preset_id)
    changes = body.model_dump(exclude_unset=True)
    bpm_min = changes["bpm_min"] if "bpm_min" in changes else preset.bpm_min
    bpm_max = changes["bpm_max"] if "bpm_max" in changes else preset.bpm_max
    try:
        check_bpm_range(bpm_min, bpm_max)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    for field, value in changes.items():
        setattr(preset, field, value)
    db.commit()
    db.refresh(preset)
    return preset


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_preset(preset_id: uuid.UUID, db: Session = Depends(get_db)):
    preset = _get_preset(db, preset_id)
    db.delete(preset)
    db.commit()
