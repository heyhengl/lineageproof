"""Explicit, bounded DataHub write-back execution with privacy-safe receipts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .context import ToolSession, response_hash

ALLOWED_MUTATION_TOOLS = frozenset({"add_tags", "update_description"})
MAX_MUTATION_CALLS = 100


class WritebackSafetyError(ValueError):
    """Raised before any mutation when a write-back safety invariant fails."""


def build_writeback_calls(report: Mapping[str, Any]) -> list[dict[str, Any]]:
    dataset_urn = str(report.get("dataset_urn") or "")
    calls: list[dict[str, Any]] = []
    if report.get("decision") == "request_remediation":
        calls.append(
            {
                "tool": "add_tags",
                "arguments": {
                    "tag_urns": ["urn:li:tag:LineageProofNeedsRemediation"],
                    "entity_urns": [dataset_urn],
                },
                "reason": "Expose the unresolved audit state to later people and agents.",
            }
        )
    issues = report.get("issues")
    if not isinstance(issues, (list, tuple)):
        raise WritebackSafetyError("audit report issues must be an array")
    for issue in issues:
        if not isinstance(issue, Mapping):
            raise WritebackSafetyError("every audit issue must be an object")
        issue_id = str(issue.get("issue_id") or "")
        severity = str(issue.get("severity") or "")
        field = str(issue.get("field") or "")
        title = str(issue.get("title") or "")
        action = str(issue.get("recommended_action") or "")
        if not all((issue_id, severity, field, title, action)):
            raise WritebackSafetyError("audit issue is incomplete")
        calls.append(
            {
                "tool": "update_description",
                "arguments": {
                    "entity_urn": dataset_urn,
                    "column_path": field,
                    "operation": "append",
                    "description": (
                        f"\n\nLineageProof {issue_id} ({severity}): {title}. "
                        f"Recommended action: {action}"
                    ),
                },
                "reason": f"Attach the evidence-backed remediation note for {field}.",
            }
        )
    return calls


def build_writeback_preview_document(report: Mapping[str, Any]) -> dict[str, Any]:
    change_id = str(report.get("change_id") or "")
    dataset_urn = str(report.get("dataset_urn") or "")
    if not change_id:
        raise WritebackSafetyError("audit report change_id is required")
    if not dataset_urn.startswith("urn:li:dataset:"):
        raise WritebackSafetyError("audit report dataset_urn must be a DataHub dataset URN")
    return {
        "preview_version": "1.1",
        "change_id": change_id,
        "audit_report_sha256": response_hash(dict(report)),
        "dry_run": True,
        "mutation_tools_invoked": False,
        "calls": build_writeback_calls(report),
        "truth_boundary": "This file is a plan only; no DataHub metadata was modified.",
    }


def validate_writeback_inputs(
    report: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    expected = build_writeback_preview_document(report)
    if dict(plan) != expected:
        raise WritebackSafetyError(
            "write-back plan does not exactly match the supplied audit report"
        )
    calls = expected["calls"]
    if not calls:
        raise WritebackSafetyError("write-back plan contains no calls")
    if len(calls) > MAX_MUTATION_CALLS:
        raise WritebackSafetyError(
            f"write-back plan exceeds the {MAX_MUTATION_CALLS}-call safety limit"
        )
    tools = {str(call["tool"]) for call in calls}
    if not tools.issubset(ALLOWED_MUTATION_TOOLS):
        raise WritebackSafetyError("write-back plan contains a disallowed mutation tool")
    return calls


def _receipt(
    *,
    report: Mapping[str, Any],
    plan: Mapping[str, Any],
    session: ToolSession,
    status: str,
    apply_requested: bool,
    error_type: str | None = None,
) -> dict[str, Any]:
    mutation_invoked = bool(session.receipts)
    execution_mode = session.provider_kind
    if execution_mode == "synthetic_fixture":
        external_state = False
        truth_boundary = (
            "Mutation tools were exercised against a synthetic fixture; no external "
            "DataHub metadata was modified."
        )
    elif mutation_invoked:
        external_state = "unverified"
        truth_boundary = (
            "The live MCP server returned mutation responses; verify target metadata "
            "separately before claiming the external state changed."
        )
    else:
        external_state = False
        truth_boundary = "No mutation tool was invoked."
    receipt: dict[str, Any] = {
        "receipt_version": "1.0",
        "change_id": str(report["change_id"]),
        "audit_report_sha256": response_hash(dict(report)),
        "writeback_plan_sha256": response_hash(dict(plan)),
        "status": status,
        "apply_requested": apply_requested,
        "execution_mode": execution_mode,
        "mutation_tools_invoked": mutation_invoked,
        "external_metadata_modified": external_state,
        "completed_calls": [item.__dict__ for item in session.receipts],
        "truth_boundary": truth_boundary,
    }
    if error_type is not None:
        receipt["error_type"] = error_type
    return receipt


async def execute_writeback(
    report: Mapping[str, Any],
    plan: Mapping[str, Any],
    session: ToolSession,
    *,
    apply: bool,
    acknowledgement: str | None,
) -> dict[str, Any]:
    calls = validate_writeback_inputs(report, plan)
    required_tools = {str(call["tool"]) for call in calls}
    available_tools = await session.list_tools()
    missing_tools = required_tools - available_tools
    if missing_tools:
        raise WritebackSafetyError(
            "required mutation tools are unavailable: " + ", ".join(sorted(missing_tools))
        )

    if not apply:
        return _receipt(
            report=report,
            plan=plan,
            session=session,
            status="preflight_pass",
            apply_requested=False,
        )

    expected_acknowledgement = f"APPLY {report['change_id']}"
    if acknowledgement != expected_acknowledgement:
        raise WritebackSafetyError(f"--acknowledge must exactly equal {expected_acknowledgement!r}")

    try:
        for call in calls:
            await session.call_tool(str(call["tool"]), dict(call["arguments"]))
    except Exception as exc:  # noqa: BLE001 - preserve a bounded partial-failure receipt
        return _receipt(
            report=report,
            plan=plan,
            session=session,
            status="partial_failure" if session.receipts else "failed",
            apply_requested=True,
            error_type=type(exc).__name__,
        )
    return _receipt(
        report=report,
        plan=plan,
        session=session,
        status="pass",
        apply_requested=True,
    )
