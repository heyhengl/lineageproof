"""Explainable schema-change risk rules."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .models import AuditIssue, AuditManifest, ProposedChange


@dataclass(frozen=True)
class FieldContext:
    lineage: dict[str, Any]
    queries: dict[str, Any]
    lineage_receipt: int
    queries_receipt: int


def evaluate_dataset_context(
    manifest: AuditManifest,
    entity: dict[str, Any],
    schema: dict[str, Any],
    *,
    entity_receipt: int,
    schema_receipt: int,
    issue_number_start: int,
) -> list[AuditIssue]:
    """Validate ownership and proposal baseline before downstream reasoning."""

    issues: list[AuditIssue] = []

    def add(
        rule_id: str,
        severity: str,
        field: str,
        title: str,
        explanation: str,
        action: str,
        receipts: tuple[int, ...],
    ) -> None:
        issues.append(
            AuditIssue(
                issue_id=f"LP-{issue_number_start + len(issues):03d}",
                rule_id=rule_id,
                severity=severity,
                field=field,
                title=title,
                explanation=explanation,
                evidence_receipts=receipts,
                recommended_action=action,
            )
        )

    owners = (entity.get("ownership") or {}).get("owners") or []
    if not owners:
        add(
            "LP_MISSING_OWNER",
            "medium",
            "<dataset>",
            "Dataset has no accountable owner",
            "The DataHub entity response contains no ownership assignment for this dataset.",
            "Assign a technical or data owner before approving the production schema change.",
            (entity_receipt,),
        )

    fields = {
        str(item.get("fieldPath")): item
        for item in schema.get("fields") or []
        if isinstance(item, dict) and item.get("fieldPath")
    }
    for change in manifest.changes:
        current = fields.get(change.before.field)
        if current is None:
            add(
                "LP_STALE_BASELINE",
                "critical",
                change.before.field,
                "Proposed baseline field is absent from DataHub",
                (
                    f"{change.before.field} is present in the change manifest but absent "
                    "from the retrieved DataHub schema."
                ),
                "Refresh the proposal from the current schema and rerun LineageProof.",
                (schema_receipt,),
            )
            continue
        current_type = str(current.get("nativeDataType") or "")
        current_nullable = current.get("nullable")
        if current_type.upper() != change.before.native_type.upper() or (
            isinstance(current_nullable, bool) and current_nullable != change.before.nullable
        ):
            add(
                "LP_STALE_BASELINE",
                "critical",
                change.before.field,
                "Proposed baseline does not match DataHub",
                (
                    f"Manifest baseline is {change.before.native_type}, nullable="
                    f"{change.before.nullable}; DataHub reports {current_type}, "
                    f"nullable={current_nullable}."
                ),
                "Regenerate the change from the current schema before impact analysis.",
                (schema_receipt,),
            )

    return issues


def _downstream_results(lineage: dict[str, Any]) -> list[dict[str, Any]]:
    downstreams = lineage.get("downstreams") or {}
    results = downstreams.get("searchResults") or []
    return [item for item in results if isinstance(item, dict)]


def downstream_urns(lineage: dict[str, Any]) -> tuple[str, ...]:
    urns = []
    for result in _downstream_results(lineage):
        entity = result.get("entity") or {}
        urn = entity.get("urn")
        if isinstance(urn, str):
            urns.append(urn)
    return tuple(sorted(set(urns)))


def _query_statements(queries: dict[str, Any]) -> list[str]:
    statements: list[str] = []
    for query in queries.get("queries") or []:
        value = (((query or {}).get("properties") or {}).get("statement") or {}).get("value")
        if isinstance(value, str):
            statements.append(value)
    return statements


def _is_decimal_widening(before_type: str, after_type: str) -> bool:
    pattern = re.compile(r"^DECIMAL\((\d+),(\d+)\)$", re.IGNORECASE)
    before_match = pattern.match(before_type.strip())
    after_match = pattern.match(after_type.strip())
    if not before_match or not after_match:
        return False
    before_precision, before_scale = map(int, before_match.groups())
    after_precision, after_scale = map(int, after_match.groups())
    return after_precision >= before_precision and after_scale == before_scale


def _downstream_without_pii(lineage: dict[str, Any]) -> tuple[str, ...]:
    missing: list[str] = []
    for result in _downstream_results(lineage):
        entity = result.get("entity") or {}
        urn = entity.get("urn")
        tags_raw = (entity.get("tags") or {}).get("tags") or []
        tags = {str(((item or {}).get("tag") or {}).get("urn") or "").lower() for item in tags_raw}
        if isinstance(urn, str) and not any(tag.endswith(":pii") for tag in tags):
            missing.append(urn)
    return tuple(sorted(set(missing)))


def evaluate_change(
    change: ProposedChange,
    context: FieldContext,
    *,
    issue_number_start: int,
) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    downstream = downstream_urns(context.lineage)
    receipts = (context.lineage_receipt, context.queries_receipt)
    field = change.before.field
    statements = _query_statements(context.queries)

    def add(
        rule_id: str,
        severity: str,
        title: str,
        explanation: str,
        action: str,
        assets: tuple[str, ...] = downstream,
    ) -> None:
        issue_id = f"LP-{issue_number_start + len(issues):03d}"
        issues.append(
            AuditIssue(
                issue_id=issue_id,
                rule_id=rule_id,
                severity=severity,
                field=field,
                title=title,
                explanation=explanation,
                evidence_receipts=receipts,
                downstream_assets=assets,
                recommended_action=action,
            )
        )

    if change.kind in {"rename", "remove"} and downstream:
        new_field = change.after.field if change.after else "<removed>"
        severity = "critical" if len(downstream) >= 5 else "high"
        add(
            "LP_BREAKING_FIELD_IDENTITY",
            severity,
            "Field identity change reaches downstream assets",
            (
                f"{field} changes to {new_field} while {len(downstream)} downstream "
                "assets are recorded."
            ),
            (
                "Add a compatibility field or versioned migration, notify owners, "
                "and verify each contract before removal."
            ),
        )

    if change.kind == "type_change" and change.after is not None:
        before_type = change.before.native_type
        after_type = change.after.native_type
        if before_type.upper() != after_type.upper():
            exact_contract = any(
                before_type.lower() in statement.lower() for statement in statements
            )
            widening = _is_decimal_widening(before_type, after_type)
            severity = "high" if exact_contract or not widening else "medium"
            add(
                "LP_TYPE_CONTRACT",
                severity,
                "Type change conflicts with observed usage"
                if exact_contract
                else "Type change needs contract review",
                f"{field} changes from {before_type} to {after_type}; "
                f"{len(statements)} production query examples were inspected.",
                (
                    "Run contract tests against representative downstream queries "
                    "and document the accepted type range."
                ),
            )

    if (
        change.kind == "nullability_change"
        and change.after is not None
        and not change.before.nullable
        and change.after.nullable
    ):
        risky_pattern = re.compile(
            rf"\b(sum|avg|min|max|join|group\s+by|order\s+by)\b[^;]*\b{re.escape(field)}\b",
            re.IGNORECASE | re.DOTALL,
        )
        risky_queries = [statement for statement in statements if risky_pattern.search(statement)]
        severity = "high" if risky_queries else "medium"
        add(
            "LP_NULLABILITY_USAGE",
            severity,
            "Nullable field is used without a migration guard",
            (
                f"{field} becomes nullable; {len(risky_queries)} of {len(statements)} "
                "observed queries use it in a sensitive operation."
            ),
            (
                "Define null semantics, backfill existing rows, and update downstream "
                "queries with an explicit guard."
            ),
        )

    pii_before = any(
        tag.lower().endswith(":pii") or tag.lower() == "pii" for tag in change.before.tags
    )
    if pii_before:
        unclassified = _downstream_without_pii(context.lineage)
        if unclassified:
            add(
                "LP_PII_PROPAGATION",
                "high",
                "PII lineage reaches unclassified downstream assets",
                (
                    f"{field} is tagged PII, but {len(unclassified)} downstream assets "
                    "lack the PII tag in the retrieved context."
                ),
                (
                    "Confirm classification with asset owners and propagate the "
                    "approved DataHub tag before deployment."
                ),
                unclassified,
            )

    return issues
