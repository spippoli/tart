# One Instance per deployment, no multi-tenancy

Each TART Instance (a local archive such as Rome) runs as its own deployment with its own database; there is no shared multi-tenant database and no account shared across Instances. Users, Artists, and Artworks are local to their Instance. We chose this because local communities must be independent (separate governance, data licensing, moderation, and hosting budgets, with Rome targeting at most €20/month), and isolation is simpler to self-host and reason about than tenant scoping in every query.

## Consequences

- Cross-instance features (federated search, a shared Artist across cities) would require a new integration layer rather than a query change.
- An artist active in Rome and Milan has a separate Artist record in each Instance.
