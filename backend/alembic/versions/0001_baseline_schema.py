"""baseline schema: presets, songs, messages

Revision ID: 0001_baseline_schema
Revises:
Create Date: 2026-10-20

Таблицы создаются только если их ещё нет: базы, поднятые через прежний
create_all, получают тот же набор таблиц без ошибок.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_baseline_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table("presets"):
        op.create_table(
            "presets",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("genre", sa.String(length=100), nullable=False),
            sa.Column("bpm_min", sa.Integer(), nullable=True),
            sa.Column("bpm_max", sa.Integer(), nullable=True),
            sa.Column("energy", sa.Float(), nullable=True),
            sa.Column("style_prompt", sa.Text(), nullable=True),
            sa.Column("negative_style_prompt", sa.Text(), nullable=True),
            sa.Column("sound_scene", sa.Text(), nullable=True),
            sa.Column("hooks_prompt", sa.Text(), nullable=True),
            sa.Column("effects_prompt", sa.Text(), nullable=True),
            sa.Column("chorus_vocal_style", sa.Text(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _has_table("songs"):
        op.create_table(
            "songs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("title", sa.String(length=300), nullable=True),
            sa.Column("idea", sa.Text(), nullable=True),
            sa.Column("lyrics", sa.Text(), nullable=True),
            sa.Column("track_settings", postgresql.JSONB(), nullable=True),
            sa.Column("analysis", postgresql.JSONB(), nullable=True),
            sa.Column("generation_settings", postgresql.JSONB(), nullable=True),
            sa.Column(
                "preset_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("presets.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

    if not _has_table("messages"):
        op.create_table(
            "messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "song_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("songs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(length=50), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )
        op.create_index("ix_messages_song_id", "messages", ["song_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_song_id", table_name="messages")
    op.drop_table("messages")
    op.drop_table("songs")
    op.drop_table("presets")
