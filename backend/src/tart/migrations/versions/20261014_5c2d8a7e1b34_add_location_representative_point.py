"""Add the Location's representative point.

Revision ID: 5c2d8a7e1b34
Revises: 8e4b1f6c2d90
Create Date: 2026-10-14 12:00:00.000000

Forward only (ADR 0020): add no reverse function.
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op

revision: str = "5c2d8a7e1b34"
down_revision: str | Sequence[str] | None = "8e4b1f6c2d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REPRESENTATIVE_POINT = (
    "CASE GeometryType(geometry) "
    "WHEN 'POINT' THEN geometry "
    "WHEN 'LINESTRING' THEN ST_LineInterpolatePoint(geometry, 0.5) "
    "ELSE ST_PointOnSurface(geometry) END"
)


def upgrade() -> None:
    op.add_column(
        "location",
        sa.Column(
            "representative_point",
            geoalchemy2.Geometry("POINT", srid=4326, spatial_index=False),
            sa.Computed(REPRESENTATIVE_POINT, persisted=True),
            nullable=True,
        ),
    )
