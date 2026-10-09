# Edit Submissions are field-level changesets against a Base revision

An edit Submission stores the Revision it was written against (its Base revision) and a changeset of operations: set a field, or add, change, or remove an item (Attribution, History event, link to a Source or Documentation item). A create Submission has no Base revision; its changeset is the whole new record. On approval, if the target has moved past the Base revision, the changeset is applied to the current Revision when none of its operations touch a field or item changed since the base; otherwise the Submission is Outdated and cannot be approved until the Submitter revises it against the current Revision. We chose this because Moderators must compare existing and proposed data (Journey E), and because a busy record must not force every concurrent Submission back to its Submitter.

## Considered Options

- **Full snapshot of the proposed record**: simplest to store, but a snapshot silently reverts any change approved in the meantime, and the comparison has to be reconstructed by diffing.
- **Block whenever the record has moved on**: simplest conflict rule, but every unrelated approval would invalidate all other pending Submissions on the record.

## Consequences

- Outdated is computed, not a Submission status; the review queue flags Outdated Submissions and warns when pending Submissions overlap.
- A Submission whose target was merged or withdrawn is Outdated.
- A Submission may create new related records but may only link existing ones; it never edits a second existing record, and it never references a record that exists only in another pending Submission.
