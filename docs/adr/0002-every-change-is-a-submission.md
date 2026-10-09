# Every change to an Archive record is a Submission

All changes to Archive records (Artworks, Artists, Locations, Sites, Series, Areas, Sources, Documentation items), including those made by Moderators, go through a Submission, and an approved Submission produces one Revision for each Archive record it creates or changes. We chose this over letting Moderators edit records directly so that the Revision history is always complete and attributable, and so that proposed data is never mixed with authoritative data. Whether a Moderator may approve their own Submission is a permissions question, not a modelling one.

## Consequences

- There is no "edit in place" path in the data model; a quick correction is still a Submission, possibly auto-approved by policy.
- A Submission is approved or rejected as a whole; partial approval is not supported, so Moderators request changes instead. Moderators never amend a Submitter's content.
- A Merge is a Submission. Undoing an approved change is a new Submission pre-filled from an earlier Revision, never a rollback.
- Withdrawal is the one exception: it changes visibility, not content, so it is a direct Moderator action with its own log and produces no Revision.
