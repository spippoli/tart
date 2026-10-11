"""The tables of Users, roles, sessions, and one-time codes (PostgreSQL).

A User's id is their User number, which Moderators see and which the deleted-account
Pseudonym shows. Email addresses are stored normalised (`normalise_email`), so the
unique constraint compares them without regard to case. Session ids and codes are
stored only as keyed hashes (`tart.auth.tokens`): a copy of the database holds no
usable session or code.
"""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    LargeBinary,
    PrimaryKeyConstraint,
    Table,
    Text,
)

from tart.db import Base

metadata = Base.metadata

MODERATOR = "moderator"
"""The only role of the MVP; the Operator is not a User role."""

user_account = Table(
    "user_account",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("email", Text, nullable=False, unique=True),
    Column("display_name", Text, nullable=False),
    Column("preferred_language", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("suspended_at", DateTime(timezone=True)),
    Column("suspension_reason", Text),
    CheckConstraint(
        "(suspended_at IS NULL) = (suspension_reason IS NULL)", name="suspension_complete"
    ),
)

user_role = Table(
    "user_role",
    metadata,
    Column("user_id", BigInteger, ForeignKey("user_account.id", ondelete="CASCADE")),
    Column("role", Text),
    PrimaryKeyConstraint("user_id", "role"),
    CheckConstraint(f"role IN ('{MODERATOR}')", name="role_allowed"),
)

user_session = Table(
    "user_session",
    metadata,
    Column("id_hash", LargeBinary, primary_key=True),
    Column(
        "user_id",
        BigInteger,
        ForeignKey("user_account.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    ),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
)

sign_in_code = Table(
    "sign_in_code",
    metadata,
    # One live code per address: a new request replaces the row, invalidating the old code.
    Column("email", Text, primary_key=True),
    Column("code_hash", LargeBinary, nullable=False),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("wrong_attempts", Integer, nullable=False, server_default="0"),
)
