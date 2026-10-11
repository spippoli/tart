"""The `tart` Operator CLI (Foundations spec, 5. Operator CLI).

Each subcommand is a function that takes the parsed arguments and returns an
exit status; `_parser` registers it.
"""

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence

from sqlalchemy.exc import SQLAlchemyError

from tart import migrations
from tart.config import ConfigurationError, config_dir, load_instance
from tart.config.database import check_database
from tart.config.instance import InstanceFile
from tart.config.vocabularies import VocabularyFile


def _migrate(_: argparse.Namespace) -> int:
    migrations.upgrade_to_head()
    return 0


def _config_check(args: argparse.Namespace) -> int:
    directory = config_dir(os.environ)
    try:
        instance = load_instance(directory)
        if args.database:
            issues = asyncio.run(check_database(instance))
            if issues:
                raise ConfigurationError(issues)
    except ConfigurationError as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, RuntimeError, SQLAlchemyError) as error:
        # An unreachable database, or no DATABASE_URL.
        print(f"cannot check the database: {error}", file=sys.stderr)
        return 1
    print(f"{directory}: the configuration is valid")
    return 0


_SCHEMAS = {"instance": InstanceFile, "vocabulary": VocabularyFile}


def _config_schema(args: argparse.Namespace) -> int:
    print(json.dumps(_SCHEMAS[args.file].model_json_schema(), indent=2))
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tart", description="TART Operator CLI.")
    commands = parser.add_subparsers(title="commands", metavar="<command>", required=True)

    migrate = commands.add_parser(
        "migrate",
        help="apply the database migrations up to the code's head",
        description=(
            "Apply the pending database migrations, forward only. In production this is "
            "the step `tart upgrade` runs in a one-shot container, with the services stopped."
        ),
    )
    migrate.set_defaults(handler=_migrate)

    config = commands.add_parser("config", help="check the Instance configuration")
    config_commands = config.add_subparsers(title="commands", metavar="<command>", required=True)
    check = config_commands.add_parser(
        "check",
        help="validate the configuration directory and report every error",
        description=(
            "Validate the configuration directory at CONFIG_DIR (default /config) as the "
            "services do at startup, and report every error. Without --database it needs "
            "no database."
        ),
    )
    check.add_argument(
        "--database",
        action="store_true",
        help=(
            "also check against the database at DATABASE_URL: vocabulary keys in use, "
            "and the highest accepted terms version"
        ),
    )
    check.set_defaults(handler=_config_check)
    schema = config_commands.add_parser(
        "schema",
        help="print the JSON Schema of a configuration file, for editors",
    )
    schema.add_argument("file", choices=sorted(_SCHEMAS), help="instance.toml or a vocabulary")
    schema.set_defaults(handler=_config_schema)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.handler(args)
