import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import require_session
from app.database import get_db
from app.models import Preset, Song
from app.schemas import SongCreate, SongExport, SongListItem, SongRead, SongUpdate

router = APIRouter(prefix="/songs", dependencies=[Depends(require_session)])


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


@router.post("", status_code=status.HTTP_201_CREATED, response_model=SongRead)
def create_song(body: SongCreate, db: Session = Depends(get_db)):
    _ensure_preset_exists(db, body.preset_id)
    song = Song(**body.model_dump())
    db.add(song)
    db.commit()
    db.refresh(song)
    return song


@router.get("", response_model=list[SongListItem])
def list_songs(db: Session = Depends(get_db)):
    return db.scalars(select(Song).order_by(Song.updated_at.desc())).all()


@router.get("/{song_id}", response_model=SongRead)
def get_song(song_id: uuid.UUID, db: Session = Depends(get_db)):
    return _get_song(db, song_id)


@router.patch("/{song_id}", response_model=SongRead)
def update_song(song_id: uuid.UUID, body: SongUpdate, db: Session = Depends(get_db)):
    song = _get_song(db, song_id)
    changes = body.model_dump(exclude_unset=True)
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
