"""songs: story, kind, analysis_status

Revision ID: 0002_song_kind_analysis
Revises: 0001_baseline_schema
Create Date: 2026-10-20

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_song_kind_analysis"
down_revision: str | None = "0001_baseline_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE songs ADD COLUMN IF NOT EXISTS story TEXT")
    op.execute(
        "ALTER TABLE songs ADD COLUMN IF NOT EXISTS kind VARCHAR(20) NOT NULL DEFAULT 'draft'"
    )
    op.execute("ALTER TABLE songs ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20)")


def downgrade() -> None:
    op.execute("ALTER TABLE songs DROP COLUMN IF EXISTS analysis_status")
    op.execute("ALTER TABLE songs DROP COLUMN IF EXISTS kind")
    op.execute("ALTER TABLE songs DROP COLUMN IF EXISTS story")
