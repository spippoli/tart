"""Create the job queue: Procrastinate's tables, types, and functions (ADR 0004).

Revision ID: f3d81374dc84
Revises: 4d78a0c187a9
Create Date: 2026-10-11 18:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op
from sqlalchemy.util import await_only

revision: str = "f3d81374dc84"
down_revision: str | Sequence[str] | None = "4d78a0c187a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = Path(__file__).parents[1] / "sql" / "procrastinate-3.10.0.sql"


def upgrade() -> None:
    # Several statements, with dollar-quoted function bodies: asyncpg runs a script
    # given without parameters as is, in the migration's transaction.
    driver = op.get_bind().connection.driver_connection
    await_only(driver.execute(SCHEMA.read_text(encoding="utf-8")))
