# Evidence level is derived from citations, not set by hand

Only Claims (Attributions and History events) carry an Evidence level, and it is computed: a Claim is *documented* when it cites at least one Source or Documentation item, otherwise *reported*. Nobody, Moderators included, can set or override it. We chose this over a manual "verified" flag or a Moderator-set level because a flag hides *why* something is trusted, drifts as evidence changes, and makes approval look like verification. With a derived level, every "documented" badge is backed by citations a reader can inspect. Moderators judge whether a cited source is good enough when they review the Submission, not through a separate flag.

## Consequences

- Other record fields (title, description, Expression type, and so on) carry no Evidence level; their provenance is the Revision that introduced them.
- Citations attached to a record as a whole (Artwork, Artist, Site, Area, Series) are background references and do not change any Claim's Evidence level.
- An Attribution with certainty `confirmed` must cite at least one Source or Documentation item; without evidence, the strongest certainty is `probable`.
- A weak source still makes a Claim *documented*; the reader judges it from the citation itself.
