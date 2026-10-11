"""What `api` and `worker` do before serving: load the configuration and check the database.

Invalid configuration, a database at another revision than the code's head
(ADR 0020), or a database check that fails stops the service; nothing is
migrated here, and the configuration is never reloaded until the next start.
"""

import os

from tart.config import Configuration, ConfigurationError, config_dir, load_configuration
from tart.config.database import check_database
from tart.migrations import ensure_database_at_head


async def start() -> Configuration:
    """The loaded configuration, or `ConfigurationError` / `RevisionMismatchError`."""
    configuration = load_configuration(config_dir(os.environ), os.environ)
    await ensure_database_at_head()
    issues = await check_database(configuration.instance)
    if issues:
        raise ConfigurationError(issues)
    return configuration
