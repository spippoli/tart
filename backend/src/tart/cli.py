"""The `tart` Operator CLI (Foundations spec, 5. Operator CLI).

Each subcommand is a function that takes the parsed arguments and returns an
exit status; `_parser` registers it.
"""

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Awaitable, Callable, Sequence
from datetime import UTC, datetime

from psycopg import Error as PsycopgError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncConnection

from tart import jobs, migrations, tiles
from tart.auth import operator
from tart.auth.operator import OperatorError
from tart.auth.users import display_name_problem
from tart.config import ConfigurationError, Instance, config_dir, load_instance
from tart.config.database import check_database
from tart.config.environment import pmtiles_path
from tart.config.instance import InstanceFile
from tart.config.vocabularies import VocabularyFile
from tart.db import create_engine, database_url
from tart.messages import load_catalogue


def _migrate(_: argparse.Namespace) -> int:
    migrations.upgrade_to_head()
    return 0


def _config_check(args: argparse.Namespace) -> int:
    directory = config_dir(os.environ)
    try:
        instance = load_instance(directory)
        if args.database:
            check = asyncio.run(check_database(instance))
            if check.issues:
                raise ConfigurationError(check.issues)
            for warning in check.warnings:
                print(f"warning: {warning}", file=sys.stderr)
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


def _tiles_update(args: argparse.Namespace) -> int:
    try:
        manifest = tiles.update(
            config_dir(os.environ), pmtiles_path(os.environ), args.build, args.source
        )
    except (ConfigurationError, tiles.TilesError) as error:
        print(f"{error}\nThe current basemap, if any, is unchanged.", file=sys.stderr)
        return 1
    print(
        f"{manifest.file} (Protomaps build {manifest.build}, schema {manifest.schema_version}) "
        "is now the current basemap"
    )
    return 0


def _run_on_database(action: Callable[[AsyncConnection, Instance], Awaitable[str]]) -> int:
    """Run `action` in one transaction against the database at `DATABASE_URL`, with the
    configuration at CONFIG_DIR, and print what it returns."""

    async def run(instance: Instance) -> str:
        engine = create_engine()
        try:
            async with engine.begin() as connection:
                return await action(connection, instance)
        finally:
            await engine.dispose()

    try:
        print(asyncio.run(run(load_instance(config_dir(os.environ)))))
    except (ConfigurationError, OperatorError) as error:
        print(error, file=sys.stderr)
        return 1
    except (OSError, RuntimeError, SQLAlchemyError) as error:
        print(f"cannot reach the database: {error}", file=sys.stderr)
        return 1
    return 0


def _users_grant(args: argparse.Namespace) -> int:
    async def grant(connection: AsyncConnection, instance: Instance) -> str:
        email = operator.address(args.email)
        user = await operator.find(connection, email)
        created = user is None
        if user is None:
            if args.display_name is None:
                raise OperatorError(
                    f"no User has the address {email}; give --display-name to create one"
                )
            ui_languages = instance.settings.languages.ui
            name = args.display_name.strip()
            problem = display_name_problem(name, load_catalogue(), ui_languages)
            if problem is not None:
                raise OperatorError(f"the display name is refused: {problem}")
            user = await operator.create(
                connection, email, name, ui_languages[0], datetime.now(UTC)
            )
        if not await operator.grant_moderator(connection, user):
            return f"#{user.id} {email} already holds the Moderator role"
        note = " (suspended: they cannot act until unsuspended)" if user.suspended_at else ""
        action = "created with" if created else "granted"
        return f"#{user.id} {email} {action} the Moderator role{note}"

    return _run_on_database(grant)


def _users_revoke(args: argparse.Namespace) -> int:
    async def revoke(connection: AsyncConnection, _: Instance) -> str:
        email = operator.address(args.email)
        if not await operator.revoke_moderator(connection, email):
            return f"{email} did not hold the Moderator role"
        return f"{email} no longer holds the Moderator role, from their next request"

    return _run_on_database(revoke)


def _users_list(_: argparse.Namespace) -> int:
    async def list_holders(connection: AsyncConnection, _: Instance) -> str:
        lines = [
            f"#{user.id}\t{user.email}\t{user.display_name}"
            + (f"\tsuspended since {user.suspended_at:%Y-%m-%d}" if user.suspended_at else "")
            for user in await operator.moderators(connection)
        ]
        return "\n".join(lines) if lines else "no User holds the Moderator role"

    return _run_on_database(list_holders)


def _users_suspend(args: argparse.Namespace) -> int:
    suspended: list[tuple[operator.User, str]] = []

    async def suspend(connection: AsyncConnection, instance: Instance) -> str:
        user = await operator.suspend(
            connection, operator.address(args.email), args.reason, datetime.now(UTC)
        )
        suspended.append((user, instance.settings.contacts.dsa))
        return f"#{user.id} {user.email} is suspended; their sessions are revoked"

    status = _run_on_database(suspend)
    if suspended:
        # After the commit, as the api does: the worker sends it.
        user, dsa = suspended[0]
        try:
            asyncio.run(_defer_suspension_email(user, args.reason.strip(), dsa))
        except (OSError, RuntimeError, PsycopgError) as error:
            print(
                f"the Suspension is recorded, but its email could not be queued: {error}; "
                "tell the User the reason and that they can contest it by writing to "
                f"{dsa}",
                file=sys.stderr,
            )
            return 1
        print("the Suspension email is queued")
    return status


async def _defer_suspension_email(user: operator.User, reason: str, dsa: str) -> None:
    app = jobs.create_app(jobs.connector_for(database_url()))
    async with app.open_async():
        await app.configure_task(jobs.SEND_EMAIL).defer_async(
            kind=operator.SUSPENSION_EMAIL,
            to=user.email,
            language=user.preferred_language,
            params={"reason": reason},
            reply_to=dsa,
        )


def _users_unsuspend(args: argparse.Namespace) -> int:
    async def unsuspend(connection: AsyncConnection, _: Instance) -> str:
        user = await operator.unsuspend(connection, operator.address(args.email))
        return f"#{user.id} {user.email} may sign in again"

    return _run_on_database(unsuspend)


def _build(value: str) -> str:
    if not tiles.is_build(value):
        raise argparse.ArgumentTypeError(f"{value!r} is not a date YYYYMMDD")
    return value


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

    users = commands.add_parser("users", help="manage roles and Suspensions")
    users_commands = users.add_subparsers(title="commands", metavar="<command>", required=True)
    grant = users_commands.add_parser(
        "grant",
        help="grant a role, creating the User if needed",
        description=(
            "Grant the Moderator role to the User with this email address. A User that "
            "does not exist yet is created, with --display-name and the Instance's default "
            "UI language."
        ),
    )
    grant.add_argument("role", choices=["moderator"])
    grant.add_argument("email")
    grant.add_argument(
        "--display-name",
        metavar="NAME",
        help="the display name of a User created by this command (1 to 40 characters)",
    )
    grant.set_defaults(handler=_users_grant)
    revoke = users_commands.add_parser(
        "revoke",
        help="revoke a role, effective on the User's next request",
        description=(
            "Remove the Moderator role; open sessions lose it on their next request. "
            "Past decisions, Moderation notes, and Invitations stay attributed to the User."
        ),
    )
    revoke.add_argument("role", choices=["moderator"])
    revoke.add_argument("email")
    revoke.set_defaults(handler=_users_revoke)
    list_users = users_commands.add_parser("list", help="list the Users holding a role")
    list_users.add_argument("--role", choices=["moderator"], required=True)
    list_users.set_defaults(handler=_users_list)
    suspend = users_commands.add_parser(
        "suspend",
        help="suspend a User: sessions revoked, sign-in refused, email with the reason",
        description=(
            "Suspend the User: every session is revoked, sign-in is refused, and the User "
            "receives an email with the reason and contacts.dsa as Reply-To, to contest it. "
            "Drafts, open Submissions, and approved contributions are left as they are."
        ),
    )
    suspend.add_argument("email")
    suspend.add_argument("--reason", required=True, help="the reason, sent to the User")
    suspend.set_defaults(handler=_users_suspend)
    unsuspend = users_commands.add_parser("unsuspend", help="lift a Suspension; no email is sent")
    unsuspend.add_argument("email")
    unsuspend.set_defaults(handler=_users_unsuspend)

    tiles_command = commands.add_parser("tiles", help="manage the basemap tiles")
    tiles_commands = tiles_command.add_subparsers(
        title="commands", metavar="<command>", required=True
    )
    update = tiles_commands.add_parser(
        "update",
        help="extract the basemap for the boundary plus 2 km and swap it in",
        description=(
            "Extract the Instance boundary plus 2 km from a Protomaps daily build into "
            "PMTILES_PATH (default /data/tiles) with go-pmtiles, refuse an extract whose "
            "schema major differs from the map styles' metadata.tart:basemap-schema, and "
            "swap it in atomically. The previous extract is kept for open pages; older "
            "ones are deleted. On any failure the current extract stays in place."
        ),
    )
    update.add_argument(
        "--build",
        type=_build,
        metavar="YYYYMMDD",
        help="the Protomaps daily build to extract (default: the latest)",
    )
    update.add_argument(
        "--source",
        metavar="URL",
        help=(
            f"a mirror laid out like {tiles.DEFAULT_SOURCE}, holding YYYYMMDD.pmtiles; "
            "needs --build"
        ),
    )
    update.set_defaults(handler=_tiles_update)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.handler(args)
