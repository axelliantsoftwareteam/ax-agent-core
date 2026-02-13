from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

from .demo import build_demo_agent, run_demo
from .providers import ProviderError


def _load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _validate_config(config: Dict[str, Any]) -> None:
    provider = config.get("provider")
    if provider not in {"mock", "openai"}:
        raise ValueError("Config 'provider' must be one of: mock, openai")
    retries = config.get("tool_retries", 1)
    if not isinstance(retries, int) or retries < 0:
        raise ValueError("Config 'tool_retries' must be a non-negative integer")
    timeout = config.get("tool_timeout_s", 5)
    if not isinstance(timeout, (int, float)) or timeout <= 0:
        raise ValueError("Config 'tool_timeout_s' must be a positive number")


def _cmd_run_demo(_: argparse.Namespace) -> int:
    run_demo()
    return 0


def _cmd_list_tools(_: argparse.Namespace) -> int:
    agent = build_demo_agent()
    for tool in agent.registry.list():
        print(f"{tool.name}: {tool.description}")
    return 0


def _cmd_validate_config(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    _validate_config(config)
    print("Config OK")
    return 0


def main(argv: Any = None) -> int:
    parser = argparse.ArgumentParser(prog="ax-agent")
    subparsers = parser.add_subparsers(dest="command")

    run_demo_parser = subparsers.add_parser("run-demo", help="Run the Ops Assistant demo")
    run_demo_parser.set_defaults(func=_cmd_run_demo)

    list_tools_parser = subparsers.add_parser("list-tools", help="List available tools")
    list_tools_parser.set_defaults(func=_cmd_list_tools)

    validate_parser = subparsers.add_parser(
        "validate-config", help="Validate a JSON config file"
    )
    validate_parser.add_argument(
        "--config",
        default="examples/config.json",
        help="Path to config JSON",
    )
    validate_parser.set_defaults(func=_cmd_validate_config)

    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except (ValueError, ProviderError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
