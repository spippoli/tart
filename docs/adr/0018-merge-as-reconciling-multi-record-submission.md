# Merge is a reconciling Submission that rewrites references with Revisions

A Merge folds a duplicate Archive record X into a surviving record Y of the same kind (Artwork, Artist, Location, Site, Series, Area, Source). It is a Submission whose changeset says "X into Y" plus item-level operations on Y's merged items, so that contradictions (two Creation events, competing Attributions to the same Artist) are resolved before approval and the validation rules apply to the merged result. It has two Base revisions, X and Y, and is Outdated when either moves on. On approval, every record that referenced X is changed to reference Y and gets its own Revision attributed to the Merge, and redirects are flattened so that no id redirects through a chain. Documentation items are never merged: a duplicate one is set aside by a **Duplicate retirement**, which moves its links and citations to the kept item without reconciling file, licence, or credits. A wrong Merge or Duplicate retirement is undone by an **Unmerge** Submission that brings the folded record back under its own id. We chose this because proximity-based duplicate detection makes mistaken Merges plausible, and the archive must never lose a record's identity or any part of either history by accident.

## Considered Options

- **Pure fold, reconcile later**: simplest, but the public record is inconsistent (or fails validation) until follow-up edits are approved.
- **Reconcile before merging**: forces several moderation rounds for one duplicate.
- **Rewrite references without Revisions, or resolve them through the redirect at read time**: the first leaves changed fields with no audit entry, the second makes every query follow redirect chains.
- **No Unmerge**: a wrong Merge would permanently redirect a real record's citations to another record.

## Consequences

- This is the one exception to ADR 0007's rule that a Submission never edits a second existing record. Merge, Duplicate retirement, and Unmerge may change X, Y, and every record that referenced X; field values stay Y's unless the changeset sets them.
- Merging Artists adds X's name and Aliases to Y as Aliases, pre-filled and editable in the changeset (ADR 0014 still applies: never a legal name).
- After a Merge, X's page answers 301 to Y, but X's `/revisions` subpage answers 200 and shows X's own Revisions read-only with a "merged into Y" notice; Y's Merge Revision links to it (ADR 0010 amended).
- Merge, Duplicate retirement, and Unmerge are allowed only when both records are public and neither has an open Notice; otherwise the Submission is Outdated. Redacted Revisions of X stay redacted.
- Any User may propose these Submissions and a Moderator approves them; finer role tiers belong to the roles ticket.
