"""What `api` and `worker` do before serving: load the configuration and check the database.

Invalid configuration, a database at another revision than the code's head
(ADR 0020), or a database check that fails stops the service; nothing is
migrated here, and the configuration is never reloaded until the next start.
The database checks' warnings are logged and never stop the service.
"""

import logging
import os

from tart.config import Configuration, ConfigurationError, config_dir, load_configuration
from tart.config.database import check_database
from tart.migrations import ensure_database_at_head

logger = logging.getLogger(__name__)


async def start() -> Configuration:
    """The loaded configuration, or `ConfigurationError` / `RevisionMismatchError`."""
    configuration = load_configuration(config_dir(os.environ), os.environ)
    await ensure_database_at_head()
    check = await check_database(configuration.instance)
    if check.issues:
        raise ConfigurationError(check.issues)
    for warning in check.warnings:
        logger.warning("configuration: %s", warning)
    return configuration
