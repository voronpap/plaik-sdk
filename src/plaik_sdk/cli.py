"""Public CLI for package scaffolding, validation, build and inspect."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .dev import (
    PackageDevError,
    build_package,
    create_package,
    dumps,
    inspect_package,
    run_package_test,
    validate_package,
)


def add_new_command(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("type", choices=("module", "integration", "theme", "pack"))
    parser.add_argument("package_id")
    parser.add_argument("--directory", type=Path)
    parser.set_defaults(handler=_new)


def add_validate_command(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", type=Path)
    parser.set_defaults(handler=_validate)


def add_test_command(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", type=Path)
    parser.set_defaults(handler=_test)


def add_build_command(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--output", type=Path)
    parser.set_defaults(handler=_build)


def add_inspect_command(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", nargs="?", type=Path)
    parser.set_defaults(handler=_inspect)


def _new(args: argparse.Namespace) -> int:
    print(create_package(args.type, args.package_id, directory=args.directory))
    return 0


def _validate(args: argparse.Namespace) -> int:
    sys.stdout.write(dumps(validate_package(args.path)))
    return 0


def _test(args: argparse.Namespace) -> int:
    sys.stdout.write(dumps(run_package_test(args.path)))
    return 0


def _build(args: argparse.Namespace) -> int:
    print(build_package(args.path, output=args.output))
    return 0


def _inspect(args: argparse.Namespace) -> int:
    sys.stdout.write(dumps(inspect_package(args.path)))
    return 0


def sdk_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="plaik-sdk",
        description="Develop PLAIK packages against the public SDK only.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    add_new_command(commands.add_parser("new", help="scaffold a package directory"))
    add_validate_command(commands.add_parser("validate", help="validate a package directory"))
    add_test_command(
        commands.add_parser("test", help="load extension.py against a fake runtime")
    )
    add_build_command(commands.add_parser("build", help="write an unsigned package zip"))
    add_inspect_command(
        commands.add_parser("inspect", help="print package identity and contracts")
    )
    return parser


def run_parser(parser: argparse.ArgumentParser, argv: list[str] | None) -> int:
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except PackageDevError as error:
        print(f"{parser.prog}: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print(f"{parser.prog}: interrupted", file=sys.stderr)
        return 130


def main(argv: list[str] | None = None) -> int:
    return run_parser(sdk_parser(), argv)
