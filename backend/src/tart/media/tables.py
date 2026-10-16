"""The uploads: one row per uploaded file, from quarantine to its stored objects."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Table,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB

from tart.db import Base
from tart.media import Format

PROCESSING = "processing"
READY = "ready"
REJECTED = "rejected"

upload = Table(
    "upload",
    Base.metadata,
    Column("id", Uuid, primary_key=True),
    Column("user_id", BigInteger, ForeignKey("user_account.id"), nullable=False),
    Column("status", Text, nullable=False),
    Column("error", Text),
    Column("size", BigInteger),
    Column("format", Text),
    # {"thumbnail": [width, height], ...} once processed.
    Column("renditions", JSONB(none_as_null=True)),
    # EXIF suggestions for the Submission form, kept 24 hours: {"observed_date", "point"}.
    Column("suggestions", JSONB(none_as_null=True)),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("processed_at", DateTime(timezone=True)),
    # The files of a rejected or retracted Submission are deleted after 30 days; the row stays.
    Column("deleted_at", DateTime(timezone=True)),
    CheckConstraint(f"status IN ('{PROCESSING}', '{READY}', '{REJECTED}')", name="status_allowed"),
    CheckConstraint(
        "format IN ({})".format(", ".join(f"'{f.value}'" for f in Format)), name="format_allowed"
    ),
    CheckConstraint(f"(status = '{REJECTED}') = (error IS NOT NULL)", name="error_when_rejected"),
    Index("ix_upload_created_at", "created_at"),
    Index("ix_upload_user_id", "user_id"),
)
