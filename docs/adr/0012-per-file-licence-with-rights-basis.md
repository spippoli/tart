# Documentation item files carry a per-file licence from an allowlist and a declared Rights basis

Every uploaded Documentation item file carries its own licence, chosen by the Submitter from an allowlist in the Instance configuration (Rome: CC BY 4.0, CC BY-SA 4.0, CC0 1.0; default CC BY-SA 4.0), a mandatory Creator credit, and a Rights basis: either the Submitter's own work, or a third party's work already under an allowlisted licence, with its creator and origin URL. Material that fits neither is linked (a link Documentation item or a Source), never uploaded. Structured archive data is published separately under the Instance's Data licence, chosen from CC0 1.0, CC BY 4.0, CC BY-SA 4.0, or ODbL 1.0 (Rome: CC BY-SA 4.0). We chose this because a Documentation item stacks four rights layers (the depicted Artwork, the file's creator, people shown in it, and the Instance's database right) and a contributor can only license the one they hold. The per-file licence and Rights basis record exactly which layer is cleared, and the allowlist keeps everything uploaded reusable.

## Considered Options

- **One mandatory free licence for every file** (the Street Art Cities model): simpler, but forces CC0 contributors and CC BY-SA contributors into one choice, and gives no route for third-party material already under another free licence.
- **A display-only licence to the Instance**: easiest for contributors, but nothing would be reusable, which defeats preservation beyond the Instance.
- **Non-commercial licences for data or files**: match TART's ethos, but cut the archive off from Wikidata, OpenStreetMap, and Wikimedia Commons, and Creative Commons advises against them for data.

## Consequences

- The Creator credit is not the User: it may be a pseudonym, it defaults to the User's display name only for own work, and it can be anonymised on request (CC 4.0 attribution removal). *Amended by [Redaction, current-value removal and Purge](https://github.com/spippoli/tart/issues/95):* a file's licence and Rights basis never change after approval (a file under another licence is a new Documentation item); its Creator credit can be corrected by an ordinary edit Submission, and anonymisation, run by the Operator, replaces it everywhere with a translated "anonymous creator" label.
- Italy has no freedom of panorama, so a file's licence never covers the depicted Artwork. Every licence notice says it covers the file only, and public image renditions are capped at a resolution set in the Instance configuration while the original stays private. The lawfulness of publishing photos of in-copyright works needs legal review.
- The Submitter accepts the Instance's versioned terms, which hold the contributor warranty and licence grant, before their first Submission and again when the terms change; the per-file Rights basis is the specific warranty.
- Capture date and GPS are read from EXIF only to suggest an Observed date and a map pin in the form. GPS and device identifiers are stripped from the stored original, and public renditions carry no EXIF, because GPS is the photographer's position, not the Artwork's Location.
