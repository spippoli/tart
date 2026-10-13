"""What Health reads besides the services themselves, and what Alerting remembers."""

from sqlalchemy import CheckConstraint, Column, DateTime, Table, Text

from tart.db import Base

BACKUP = "backup"
VERIFY = "verify"

operation_success = Table(
    "operation_success",
    Base.metadata,
    # The last success of each Operator operation that a check watches; the `backup`
    # service records them.
    Column("operation", Text, primary_key=True),
    Column("succeeded_at", DateTime(timezone=True), nullable=False),
    CheckConstraint(f"operation IN ('{BACKUP}', '{VERIFY}')", name="operation_allowed"),
)

operator_alert = Table(
    "operator_alert",
    Base.metadata,
    # When the Operator was last emailed about each check: at most once per check per day.
    Column("check_key", Text, primary_key=True),
    Column("sent_at", DateTime(timezone=True), nullable=False),
)
