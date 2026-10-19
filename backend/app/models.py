import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Preset(Base):
    __tablename__ = "presets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(200))
    genre: Mapped[str] = mapped_column(String(100))
    bpm_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bpm_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy: Mapped[float | None] = mapped_column(Float, nullable=True)
    style_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    negative_style_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    sound_scene: Mapped[str | None] = mapped_column(Text, nullable=True)
    hooks_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    effects_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    chorus_vocal_style: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)
    idea: Mapped[str | None] = mapped_column(Text, nullable=True)
    lyrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    track_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generation_settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    preset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("presets.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    preset: Mapped[Preset | None] = relationship()
    messages: Mapped[list["Message"]] = relationship(
        back_populates="song",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text)
    message_metadata: Mapped[dict | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    song: Mapped[Song] = relationship(back_populates="messages")
