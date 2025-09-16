"""Command line interface for running conductor flows."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Optional

from .config import FlowConfig, GlobalConfig, load_flow_config, load_global_config
from .execution import FlowExecutor
from .logging_utils import configure_logging


def _load_payload(payload: Optional[str], payload_file: Optional[str]) -> Any:
    if payload and payload_file:
        raise ValueError("Specify either --payload or --payload-file, not both.")
    if payload:
        return json.loads(payload)
    if payload_file:
        text = Path(payload_file).read_text()
        return json.loads(text)
    return None


async def _run_flow(args: argparse.Namespace) -> None:
    global_config = load_global_config(args.global_config) if args.global_config else GlobalConfig.from_mapping({})
    flow_config = load_flow_config(args.flow)

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logger = configure_logging(global_config, level=log_level)

    payload = _load_payload(args.payload, args.payload_file)

    async with FlowExecutor(flow_config, global_config, logger=logger) as executor:
        results = await executor.run(initial_payload=payload)
        if args.print_results:
            print(json.dumps([result.to_dict() for result in results], indent=2))
        if args.print_state:
            print(json.dumps(executor.global_state.to_dict(), indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Execute conductor flows defined in configuration files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Execute a flow")
    run_parser.add_argument("--flow", required=True, help="Path to the flow configuration file (JSON/YAML/TOML).")
    run_parser.add_argument("--global-config", help="Path to the global configuration file (JSON/YAML/TOML).")
    run_parser.add_argument("--payload", help="Inline JSON string to pass as the initial payload for the flow.")
    run_parser.add_argument("--payload-file", help="Path to a JSON file to use as the initial payload.")
    run_parser.add_argument("--log-level", default="INFO", help="Logging level (default: INFO).")
    run_parser.add_argument(
        "--print-results",
        dest="print_results",
        action="store_true",
        default=True,
        help="Print the final results of the flow in JSON format (default: enabled).",
    )
    run_parser.add_argument(
        "--no-print-results",
        dest="print_results",
        action="store_false",
        help="Disable printing the final results.",
    )
    run_parser.add_argument(
        "--print-state",
        action="store_true",
        help="Print the shared global state after flow execution.",
    )
    parser.set_defaults(func=_run_flow)
    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return
    try:
        asyncio.run(args.func(args))
    except KeyboardInterrupt:  # pragma: no cover - CLI convenience
        pass


if __name__ == "__main__":  # pragma: no cover
    main()

