"""Deterministic audit artifact writers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent import build_writeback_preview
from .models import AuditReport


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def remediation_markdown(report: AuditReport) -> str:
    lines = [
        "# LineageProof remediation plan",
        "",
        f"- Change: `{report.change_id}`",
        f"- Dataset: `{report.dataset_urn}`",
        f"- Decision: **{report.decision}**",
        f"- Evidence tool calls: {len(report.evidence)}",
        "",
        "## Required actions",
        "",
    ]
    if not report.issues:
        lines.append("No remediation is required by the current rule set.")
    for issue in report.issues:
        lines.extend(
            [
                f"### {issue.issue_id} · {issue.severity.upper()} · `{issue.field}`",
                "",
                issue.title,
                "",
                issue.explanation,
                "",
                f"Action: {issue.recommended_action}",
                "",
                "Evidence receipts: " + ", ".join(map(str, issue.evidence_receipts)),
                "",
            ]
        )
    lines.extend(
        [
            "## Truth boundary",
            "",
            "The DataHub write-back file is a dry-run preview. It is not proof of a mutation.",
            "",
        ]
    )
    return "\n".join(lines)


def sarif_document(report: AuditReport) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    level_map = {"critical": "error", "high": "error", "medium": "warning", "low": "note"}
    for issue in report.issues:
        rules.setdefault(
            issue.rule_id,
            {
                "id": issue.rule_id,
                "name": issue.rule_id,
                "shortDescription": {"text": issue.title},
            },
        )
        results.append(
            {
                "ruleId": issue.rule_id,
                "level": level_map[issue.severity],
                "message": {"text": f"{issue.field}: {issue.explanation}"},
                "properties": {
                    "issueId": issue.issue_id,
                    "field": issue.field,
                    "evidenceReceipts": list(issue.evidence_receipts),
                },
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "LineageProof",
                        "version": report.report_version,
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
            }
        ],
    }


def write_artifacts(report: AuditReport, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "audit-report.json"
    remediation_path = output_dir / "remediation-plan.md"
    sarif_path = output_dir / "lineageproof.sarif"
    writeback_path = output_dir / "datahub-writeback-preview.json"
    receipts_path = output_dir / "tool-call-receipts.json"

    _write_json(report_path, report.to_dict())
    remediation_path.write_text(remediation_markdown(report), encoding="utf-8")
    _write_json(sarif_path, sarif_document(report))
    _write_json(writeback_path, build_writeback_preview(report))
    _write_json(receipts_path, [receipt.__dict__ for receipt in report.evidence])
    return {
        "audit_report": str(report_path),
        "remediation_plan": str(remediation_path),
        "sarif": str(sarif_path),
        "writeback_preview": str(writeback_path),
        "tool_receipts": str(receipts_path),
    }
