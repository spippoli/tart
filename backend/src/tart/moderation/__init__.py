"""The moderation domain: the Submission aggregate, its lifecycle (ADR 0002), the content of its
rounds (ADR 0007), Outdated, and derived kind and labels.

Pure rules with no framework or persistence imports; `moderation_persistence` stores
the aggregate and, on approval, calls the archive's write operation.
"""

from tart.moderation.content import (
    Conflict,
    Content,
    decode_content,
    encode_content,
    resolve_conflict,
)
from tart.moderation.errors import ModerationError
from tart.moderation.kind import Intent, Label, SubmissionKind, derive_kind, derive_labels
from tart.moderation.lifecycle import (
    TRANSITIONS,
    Action,
    DecisionRules,
    Verdict,
    add_note,
    decide,
    expire,
    expiry_deadline,
    rebase_working_copy,
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
from tart.moderation.outdated import (
    Reason,
    Rebase,
    RecordChange,
    TargetState,
    merge_outdated_reasons,
    outdated_reasons,
    rebase,
)
from tart.moderation.validation import check_content, materialize

__all__ = [
    "DUPLICATE_REASON",
    "FINAL",
    "TRANSITIONS",
    "Action",
    "Actor",
    "ActorKind",
    "Conflict",
    "Content",
    "Decision",
    "DecisionRules",
    "Event",
    "Intent",
    "Label",
    "LogEntry",
    "ModerationError",
    "ModerationNote",
    "Reason",
    "Rebase",
    "RecordChange",
    "Round",
    "Status",
    "Submission",
    "SubmissionKind",
    "TargetState",
    "Verdict",
    "add_note",
    "check_content",
    "decide",
    "decode_content",
    "derive_kind",
    "derive_labels",
    "encode_content",
    "expire",
    "expiry_deadline",
    "materialize",
    "merge_outdated_reasons",
    "outdated_reasons",
    "rebase",
    "rebase_working_copy",
    "resolve_conflict",
    "retract",
    "save_working_copy",
    "submit",
]
