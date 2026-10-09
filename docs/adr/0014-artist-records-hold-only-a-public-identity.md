# Artist records hold only a public identity, with no User link

An Artist record names an artist only by the names they publicly use as an artist (a legal name appears only when it is itself that name), and its free text never states a legal identity, age or date of birth, residence, physical appearance, or any allegation of an offence. It shows no image of the person, and its external links point only to the artist's own public channels, as Sources. The archive never records whether an Artwork was authorised: there is no legality field or filter, and no Artwork is described or implied to be unauthorised. A documented commission (a festival, a municipal project) may be told as history, in a description or a Series, with a Source. No User is ever linked to an Artist, not even as a verified, read-only claim. We chose this because attributing unauthorised works to an identifiable person may be criminal-offence data under Art. 10 GDPR. A pseudonymous identity with no legality data builds no list of offences per person, and with no User link the Operator never holds the bridge between a pseudonym and a real email address.

## Considered Options

- **An optional authorisation field on Artworks** (authorised, commissioned, unauthorised): useful history, but it turns every Artist page into a filterable list of alleged offences.
- **Banning Attributions on unauthorised works**: unenforceable, since authorisation is usually unknown, and it would empty the archive.
- **A verified User–Artist link without control rights** ("claim your profile"): it needs an identity check that a pseudonym cannot support, and it stores exactly the link between person and pseudonym that Art. 10 makes risky. It may return as a future feature after legal review.

## Consequences

- Moderators check Artist records and Artwork descriptions against these rules before approval, as they already screen files for identifiable people (ADR 0013).
- Artists have no dedicated channel. They correct or unlink through ordinary edit Submissions, which anyone may author, and raise personal-data concerns through a Notice, which can be sent from an Artist page and whose "personal data" reason covers an Attribution that exposes someone. Notices are judged on the content, never on who sends them, so no identity is verified.
- An artist's own public statements enter the archive as a Source (their own publication) or a real-world attribution-change History event. A User writing "I made this" in a Submission is not a citation and cannot make an Attribution confirmed.
- When an Artist is withdrawn, its Attributions and Crew memberships are hidden with it, and the Artworks show no Attribution, exactly as Artworks without Attributions do; a Reinstatement restores them. Past Revisions that still carry the name are handled by Redaction where needed.
- Whether pseudonymous Attributions of unauthorised works are Art. 10 data at all needs legal review.
