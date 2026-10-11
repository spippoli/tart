"""Allow several Crew memberships of one Artist in one collective, one per period.

Revision ID: 7a0e3c5b9d21
Revises: 1c6eb2d5d72e
Create Date: 2026-10-11 22:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "7a0e3c5b9d21"
down_revision: str | Sequence[str] | None = "1c6eb2d5d72e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("pk_crew_membership", "crew_membership", type_="primary")
    op.create_primary_key("pk_crew_membership", "crew_membership", ["member_id", "position"])
