"""Enable PostGIS.

The upstream image creates the extension only in POSTGRES_DB; this makes any
database the migrations run against spatial.

Revision ID: 4d78a0c187a9
Revises:
Create Date: 2026-10-11 16:08:59.573761

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "4d78a0c187a9"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
