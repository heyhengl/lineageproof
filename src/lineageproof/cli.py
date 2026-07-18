"""LineageProof command-line interface."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from pathlib import Path

from .agent import AuditAgent
from .context import FixtureToolSession, StdioMcpToolSession
from .models import AuditManifest
from .output import write_artifacts
from .writeback import execute_writeback


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lineageproof")
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit", help="audit a schema change")
    audit.add_argument("--change", type=Path, required=True)
    provider = audit.add_mutually_exclusive_group(required=True)
    provider.add_argument("--fixture", type=Path)
    provider.add_argument("--mcp-command")
    audit.add_argument("--out", type=Path, required=True)

    writeback = subparsers.add_parser(
        "writeback",
        help="validate or explicitly execute a generated DataHub write-back plan",
    )
    writeback.add_argument("--report", type=Path, required=True)
    writeback.add_argument("--plan", type=Path, required=True)
    provider = writeback.add_mutually_exclusive_group(required=True)
    provider.add_argument("--fixture", type=Path)
    provider.add_argument("--mcp-command")
    writeback.add_argument("--receipt", type=Path, required=True)
    writeback.add_argument("--apply", action="store_true")
    writeback.add_argument("--acknowledge")
    return parser


async def _audit(args: argparse.Namespace) -> dict[str, object]:
    manifest_raw = json.loads(args.change.read_text(encoding="utf-8"))
    manifest = AuditManifest.from_dict(manifest_raw)
    session = (
        FixtureToolSession(args.fixture)
        if args.fixture is not None
        else StdioMcpToolSession(args.mcp_command)
    )
    async with session:
        report = await AuditAgent(session).run(manifest)
    artifacts = write_artifacts(report, args.out)
    return {
        "change_id": report.change_id,
        "decision": report.decision,
        "risk_counts": report.risk_counts,
        "artifacts": artifacts,
    }


async def _writeback(args: argparse.Namespace) -> dict[str, object]:
    report = json.loads(args.report.read_text(encoding="utf-8"))
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    session = (
        FixtureToolSession(args.fixture)
        if args.fixture is not None
        else StdioMcpToolSession(args.mcp_command)
    )
    async with session:
        receipt = await execute_writeback(
            report,
            plan,
            session,
            apply=args.apply,
            acknowledgement=args.acknowledge,
        )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "audit":
        result = asyncio.run(_audit(args))
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.command == "writeback":
        result = asyncio.run(_writeback(args))
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["status"] in {"pass", "preflight_pass"} else 2
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
