"""The moderation domain: the Submission aggregate and its lifecycle (ADR 0002).

Pure rules with no framework or persistence imports; `moderation_persistence` stores
the aggregate. Approval calls the archive's write operation (ticket C02).
"""

from tart.moderation.errors import ModerationError
from tart.moderation.lifecycle import (
    TRANSITIONS,
    Action,
    DecisionRules,
    Verdict,
    add_note,
    decide,
    expire,
    expiry_deadline,
    retract,
    save_working_copy,
    submit,
)
from tart.moderation.model import (
    DUPLICATE_REASON,
    FINAL,
    Actor,
    ActorKind,
    Decision,
    Event,
    LogEntry,
    ModerationNote,
    Round,
    Status,
    Submission,
)

__all__ = [
    "DUPLICATE_REASON",
    "FINAL",
    "TRANSITIONS",
    "Action",
    "Actor",
    "ActorKind",
    "Decision",
    "DecisionRules",
    "Event",
    "LogEntry",
    "ModerationError",
    "ModerationNote",
    "Round",
    "Status",
    "Submission",
    "Verdict",
    "add_note",
    "decide",
    "expire",
    "expiry_deadline",
    "retract",
    "save_working_copy",
    "submit",
]
