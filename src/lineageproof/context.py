"""DataHub MCP tool sessions with privacy-safe receipts."""

from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path
from typing import Any, Protocol

from .models import ToolReceipt


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def response_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class ToolSession(Protocol):
    receipts: list[ToolReceipt]
    provider_kind: str

    async def __aenter__(self) -> ToolSession: ...

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None: ...

    async def list_tools(self) -> set[str]: ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


class ReceiptMixin:
    receipts: list[ToolReceipt]

    def _record(self, name: str, arguments: dict[str, Any], result: dict[str, Any]) -> None:
        self.receipts.append(
            ToolReceipt(
                sequence=len(self.receipts) + 1,
                tool=name,
                arguments=arguments,
                response_sha256=response_hash(result),
            )
        )


class FixtureToolSession(ReceiptMixin):
    """Match recorded synthetic responses against DataHub MCP tool calls."""

    provider_kind = "synthetic_fixture"

    def __init__(self, fixture_path: Path):
        raw = json.loads(fixture_path.read_text(encoding="utf-8"))
        if raw.get("fixture_type") != "synthetic-datahub-mcp":
            raise ValueError("fixture_type must be synthetic-datahub-mcp")
        responses = raw.get("responses")
        if not isinstance(responses, list) or not responses:
            raise ValueError("fixture responses must be a non-empty array")
        self.responses = responses
        self.receipts = []

    async def __aenter__(self) -> FixtureToolSession:
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        return None

    async def list_tools(self) -> set[str]:
        return {str(entry["tool"]) for entry in self.responses if entry.get("tool")}

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        for entry in self.responses:
            if entry.get("tool") != name:
                continue
            match = entry.get("match") or {}
            if all(arguments.get(key) == value for key, value in match.items()):
                result = entry.get("result")
                if not isinstance(result, dict):
                    raise ValueError(f"fixture result for {name} must be an object")
                self._record(name, arguments, result)
                return result
        raise LookupError(f"fixture has no response for {name} with {canonical_json(arguments)}")


class StdioMcpToolSession(ReceiptMixin):
    """Live stdio client for the official DataHub MCP server."""

    provider_kind = "live_mcp"

    def __init__(self, command: str):
        parts = shlex.split(command)
        if not parts:
            raise ValueError("MCP command must not be empty")
        self.command = parts[0]
        self.args = parts[1:]
        self.receipts = []
        self._stdio_context: Any = None
        self._session_context: Any = None
        self._session: Any = None

    async def __aenter__(self) -> StdioMcpToolSession:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
        except ImportError as exc:
            raise RuntimeError("install the 'mcp' extra to use --mcp-command") from exc

        parameters = StdioServerParameters(command=self.command, args=self.args)
        self._stdio_context = stdio_client(parameters)
        read_stream, write_stream = await self._stdio_context.__aenter__()
        self._session_context = ClientSession(read_stream, write_stream)
        self._session = await self._session_context.__aenter__()
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self._session_context is not None:
            await self._session_context.__aexit__(exc_type, exc, traceback)
        if self._stdio_context is not None:
            await self._stdio_context.__aexit__(exc_type, exc, traceback)

    async def list_tools(self) -> set[str]:
        result = await self._session.list_tools()
        return {str(tool.name) for tool in result.tools}

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = await self._session.call_tool(name, arguments)
        text_parts = [block.text for block in result.content if hasattr(block, "text")]
        if not text_parts:
            raise RuntimeError(f"DataHub MCP tool {name} returned no text content")
        parsed = json.loads("\n".join(text_parts))
        if not isinstance(parsed, dict):
            raise RuntimeError(f"DataHub MCP tool {name} did not return an object")
        self._record(name, arguments, parsed)
        return parsed
