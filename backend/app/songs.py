import logging
import uuid
from pathlib import Path

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.database import SessionLocal, get_db
from app.models import Preset, Song
from app.schemas import (
    SongCreate,
    SongExport,
    SongListItem,
    SongRead,
    SongReferenceRead,
    SongUpdate,
)
from app.services.ai import (
    GENERATED_PRESET_KEY,
    AIServiceError,
    analyze_reference_audio,
    build_reference_preset_fields,
    merge_reference_preset,
)

router = APIRouter(prefix="/songs", dependencies=[Depends(require_session)])
logger = logging.getLogger(__name__)

ALLOWED_REFERENCE_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac"}
ALLOWED_REFERENCE_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/mp4a-latm",
    "audio/flac",
    "audio/x-flac",
    "application/octet-stream",
    "",
}
MAX_REFERENCE_AUDIO_BYTES = 20 * 1024 * 1024


def _get_song(db: Session, song_id: uuid.UUID) -> Song:
    song = db.get(Song, song_id)
    if song is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Song not found"
        )
    return song


def _ensure_preset_exists(db: Session, preset_id: uuid.UUID | None) -> None:
    if preset_id is not None and db.get(Preset, preset_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Preset not found",
        )


def run_reference_analysis(song_id: uuid.UUID, audio: bytes, audio_format: str) -> None:
    with SessionLocal() as db:
        song = db.get(Song, song_id)
        if song is None:
            return
        stage = "audio analysis"
        try:
            analysis = analyze_reference_audio(audio, audio_format)
            stage = "preset generation"
            preset_fields = build_reference_preset_fields(analysis)
            stage = "preset save"
            preset = merge_reference_preset(db, song, preset_fields)
            song.analysis = {
                **analysis.model_dump(),
                GENERATED_PRESET_KEY: preset_fields.model_dump(),
            }
            song.analysis_status = "done"
            song.preset_id = preset.id
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            logger.error(
                "Reference analysis failed for song %s at stage %s: %s: %s",
                song_id,
                stage,
                type(exc).__name__,
                exc if isinstance(exc, AIServiceError) else "details hidden",
            )
            try:
                song = db.get(Song, song_id)
                if song is not None:
                    song.analysis_status = "failed"
                    db.commit()
            except Exception as status_exc:  # noqa: BLE001
                db.rollback()
                logger.warning(
                    "Reference status update failed for song %s: %s",
                    song_id,
                    type(status_exc).__name__,
                )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SongRead)
def create_song(body: SongCreate, db: Session = Depends(get_db)):
    _ensure_preset_exists(db, body.preset_id)
    song = Song(**body.model_dump())
    db.add(song)
    db.commit()
    db.refresh(song)
    return song


@router.post(
    "/reference", status_code=status.HTTP_201_CREATED, response_model=SongReferenceRead
)
def upload_reference(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    file_name = Path(file.filename or "").name
    if Path(file_name).suffix.lower() not in ALLOWED_REFERENCE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio format",
        )
    if (file.content_type or "") not in ALLOWED_REFERENCE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported audio format",
        )
    content = file.file.read(MAX_REFERENCE_AUDIO_BYTES + 1)
    if len(content) > MAX_REFERENCE_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Audio file is too large",
        )
    audio_format = Path(file_name).suffix.lower().lstrip(".")
    song = Song(title=file_name[:300], kind="reference", analysis_status="pending")
    db.add(song)
    db.commit()
    db.refresh(song)
    background_tasks.add_task(run_reference_analysis, song.id, content, audio_format)
    return song


@router.get("", response_model=list[SongListItem])
def list_songs(db: Session = Depends(get_db)):
    return db.scalars(
        select(Song).where(Song.kind == "draft").order_by(Song.updated_at.desc())
    ).all()


@router.get("/{song_id}", response_model=SongRead)
def get_song(song_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_song(db, song_id)


@router.patch("/{song_id}", response_model=SongRead)
def update_song(song_id: uuid.UUID, body: SongUpdate, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    changes = body.model_dump(exclude_unset=True)
    if song.kind == "reference" and ("analysis" in changes or "lyrics" in changes):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Reference songs do not accept analysis or lyrics updates",
        )
    if "preset_id" in changes:
        _ensure_preset_exists(db, changes["preset_id"])
    if "story" in changes and not (changes["story"] or "").strip():
        changes["story"] = None
    for field, value in changes.items():
        setattr(song, field, value)
    db.commit()
    db.refresh(song)
    return song


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_song(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    db.delete(song)
    db.commit()


@router.get("/{song_id}/export", response_model=SongExport)
def export_song(song_id: uuid.UUID, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    track_settings = song.track_settings or {}
    return SongExport(
        song_id=song.id,
        title=song.title,
        lyrics=song.lyrics,
        style_prompt=track_settings.get("style_prompt"),
        negative_style_prompt=track_settings.get("negative_style_prompt"),
        performance=track_settings.get("performance"),
        generation_settings=song.generation_settings,
    )
