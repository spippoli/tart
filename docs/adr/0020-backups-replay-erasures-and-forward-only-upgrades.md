# Backups keep erased data until they expire and replay the Erasure log; upgrades are forward-only

An Instance backs up its database with `pg_dump` into a restic repository (7 daily, 4 weekly, 6 monthly snapshots) and its media with an encrypted `rclone sync --backup-dir`, where objects deleted from storage are kept for 30 days before they leave the backup. Backups are never rewritten to honour a Purge or an account deletion. Instead, both write a content-free entry to the **Erasure log**, and `tart backup restore` applies the Erasure log of the most recent dump again after restoring any dump. The processing inventory states that erased data may stay in encrypted backups for up to six months. Upgrades go through `tart upgrade`: a tagged pre-upgrade backup, a configuration check, then Alembic migrations in a one-shot container while the services are stopped. Migrations run only forward, and a rollback is a restore of the pre-upgrade backup with the previous `TART_VERSION`. We chose this because encrypted, deduplicated backups can't be edited selectively, and supervisory authorities accept "beyond use" backups whose erasures are re-applied on restore. We also chose it because a volunteer Operator gains more from one tested restore path than from downgrade scripts that are rarely run.

## Considered Options

- **Rewrite or delete backups on every Purge**: impractical with restic's encryption and deduplication, and it destroys protection against later corruption.
- **Short database retention (30 days) without replay**: a restore inside the window would still bring back a recent Purge, so a replay is needed anyway.
- **Migrations at `api` startup**: `api` and `worker` share the image and can race, and no backup is taken before the schema changes.
- **Alembic `downgrade` scripts as rollback**: they are rarely tested, so they fail exactly when needed.

## Consequences

- A Purge and an account deletion leave a content-free tombstone (kind, target id, date) in the Erasure log; the rest of what a Purge leaves behind is decided by the Rights and legal actions spec.
- `api` and `worker` refuse to start when the database revision differs from the code's Alembic head, in the same fail-fast style as `config_version` (ADR 0009). This replaces "migrations run at `api` startup" in ADR 0004's topology.
- A rollback loses the contributions made after the upgrade, so it only makes sense right after an upgrade.
- Media copied with `rclone` have no snapshots: a legitimate deletion leaves the backup within 30 days, and so does an accidental deletion that goes unnoticed for longer than that.
