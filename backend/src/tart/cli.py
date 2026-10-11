"""The `tart` Operator CLI (Foundations spec, 5. Operator CLI).

Each subcommand is a function that takes the parsed arguments and returns an
exit status; `_parser` registers it.
"""

import argparse
from collections.abc import Sequence

from tart import migrations


def _migrate(_: argparse.Namespace) -> int:
    migrations.upgrade_to_head()
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

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.handler(args)
