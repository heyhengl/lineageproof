"""Evidence-first DataHub MCP orchestration."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .context import ToolSession
from .models import AuditIssue, AuditManifest, AuditReport
from .rules import FieldContext, evaluate_change, evaluate_dataset_context
from .writeback import build_writeback_preview_document


class AuditAgent:
    """Collect DataHub context and make a deterministic schema-change decision."""

    def __init__(self, session: ToolSession):
        self.session = session

    async def run(self, manifest: AuditManifest) -> AuditReport:
        entity = await self.session.call_tool("get_entities", {"urns": manifest.dataset_urn})
        entity_receipt = len(self.session.receipts)
        schema = await self.session.call_tool(
            "list_schema_fields",
            {"urn": manifest.dataset_urn, "limit": 100, "offset": 0},
        )
        schema_receipt = len(self.session.receipts)

        issues: list[AuditIssue] = evaluate_dataset_context(
            manifest,
            entity,
            schema,
            entity_receipt=entity_receipt,
            schema_receipt=schema_receipt,
            issue_number_start=1,
        )
        for change in manifest.changes:
            field = change.before.field
            lineage = await self.session.call_tool(
                "get_lineage",
                {
                    "urn": manifest.dataset_urn,
                    "column": field,
                    "upstream": False,
                    "max_hops": 3,
                    "max_results": 100,
                    "offset": 0,
                },
            )
            lineage_receipt = len(self.session.receipts)
            queries = await self.session.call_tool(
                "get_dataset_queries",
                {
                    "urn": manifest.dataset_urn,
                    "column": field,
                    "count": 10,
                    "start": 0,
                },
            )
            query_receipt = len(self.session.receipts)
            context = FieldContext(
                lineage=lineage,
                queries=queries,
                lineage_receipt=lineage_receipt,
                queries_receipt=query_receipt,
            )
            issues.extend(
                evaluate_change(
                    change,
                    context,
                    issue_number_start=len(issues) + 1,
                )
            )

        severity_counts = Counter(issue.severity for issue in issues)
        risk_counts = {
            severity: severity_counts.get(severity, 0)
            for severity in ("critical", "high", "medium", "low")
        }
        decision = self._decision(risk_counts)
        return AuditReport(
            report_version="1.0",
            change_id=manifest.change_id,
            as_of=manifest.as_of,
            dataset_urn=manifest.dataset_urn,
            environment=manifest.environment,
            decision=decision,
            risk_counts=risk_counts,
            issues=tuple(issues),
            evidence=tuple(self.session.receipts),
            limitations=(
                "The report evaluates only metadata returned by the selected DataHub MCP context.",
                (
                    "Fixture mode does not prove production DataHub connectivity or "
                    "production query behavior."
                ),
                (
                    "The write-back artifact is a dry-run preview and is not evidence "
                    "of a metadata mutation."
                ),
            ),
            metrics={
                "changed_fields": len(manifest.changes),
                "tool_calls": len(self.session.receipts),
                "issues": len(issues),
            },
        )

    @staticmethod
    def _decision(risk_counts: dict[str, int]) -> str:
        if risk_counts["critical"] or risk_counts["high"]:
            return "request_remediation"
        if risk_counts["medium"]:
            return "approve_with_conditions"
        return "approve"


def build_writeback_preview(report: AuditReport) -> dict[str, Any]:
    return build_writeback_preview_document(report.to_dict())
