from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from typing import Any

from .config import load_config
from .demo import build_demo_agent, run_demo
from .providers import ProviderError


def _cmd_run_demo(args: argparse.Namespace) -> int:
    run_demo(scripted=args.scripted)
    return 0


def _cmd_list_tools(args: argparse.Namespace) -> int:
    agent = build_demo_agent(config_path=args.config)
    for descriptor in agent.mcp_bridge.list_tools():
        print(f"{descriptor.name}: {descriptor.description}")
    return 0


def _cmd_validate_config(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    print("Config OK")
    print(json.dumps(asdict(config), indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ax-agent",
        description="Axelliant agent runtime CLI for tool-augmented workflows.",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_demo_parser = subparsers.add_parser("run-demo", help="Run the Ops Assistant demo")
    run_demo_parser.add_argument(
        "--scripted",
        action="store_true",
        help="Run non-interactive scripted prompts and exit.",
    )
    run_demo_parser.set_defaults(func=_cmd_run_demo)

    list_tools_parser = subparsers.add_parser("list-tools", help="List registered tools")
    list_tools_parser.add_argument(
        "--config",
        default="examples/config.json",
        help="Path to JSON config file",
    )
    list_tools_parser.set_defaults(func=_cmd_list_tools)

    validate_parser = subparsers.add_parser("validate-config", help="Validate JSON config")
    validate_parser.add_argument(
        "--config",
        default="examples/config.json",
        help="Path to JSON config file",
    )
    validate_parser.set_defaults(func=_cmd_validate_config)

    return parser


def main(argv: Any = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        return int(args.func(args))
    except (ValueError, ProviderError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
