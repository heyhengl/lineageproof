"""Validated domain models for LineageProof."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


class ManifestError(ValueError):
    """Raised when a schema-change manifest violates the public contract."""


ALLOWED_CHANGE_KINDS = {"rename", "remove", "type_change", "nullability_change"}
ALLOWED_SEVERITIES = {"low", "medium", "high", "critical"}


@dataclass(frozen=True)
class FieldState:
    field: str
    native_type: str
    nullable: bool
    tags: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, label: str) -> FieldState:
        required = ("field", "native_type", "nullable")
        missing = [key for key in required if key not in raw]
        if missing:
            raise ManifestError(f"{label} missing fields: {', '.join(missing)}")
        if not isinstance(raw["nullable"], bool):
            raise ManifestError(f"{label}.nullable must be boolean")
        tags = raw.get("tags") or []
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ManifestError(f"{label}.tags must be an array of strings")
        return cls(
            field=str(raw["field"]),
            native_type=str(raw["native_type"]),
            nullable=raw["nullable"],
            tags=tuple(sorted(set(tags))),
        )


@dataclass(frozen=True)
class ProposedChange:
    kind: str
    before: FieldState
    after: FieldState | None
    rationale: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, index: int) -> ProposedChange:
        kind = str(raw.get("kind") or "")
        if kind not in ALLOWED_CHANGE_KINDS:
            raise ManifestError(
                f"changes[{index}].kind must be one of {sorted(ALLOWED_CHANGE_KINDS)}"
            )
        before_raw = raw.get("before")
        if not isinstance(before_raw, dict):
            raise ManifestError(f"changes[{index}].before must be an object")
        before = FieldState.from_dict(before_raw, label=f"changes[{index}].before")
        after_raw = raw.get("after")
        if kind == "remove":
            if after_raw is not None:
                raise ManifestError(f"changes[{index}].after must be null for remove")
            after = None
        else:
            if not isinstance(after_raw, dict):
                raise ManifestError(f"changes[{index}].after must be an object")
            after = FieldState.from_dict(after_raw, label=f"changes[{index}].after")
        rationale = str(raw.get("rationale") or "").strip()
        if not rationale:
            raise ManifestError(f"changes[{index}].rationale is required")
        return cls(kind=kind, before=before, after=after, rationale=rationale)


@dataclass(frozen=True)
class AuditManifest:
    change_id: str
    as_of: str
    dataset_urn: str
    environment: str
    changes: tuple[ProposedChange, ...]

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> AuditManifest:
        required = ("change_id", "as_of", "dataset_urn", "environment", "changes")
        missing = [key for key in required if key not in raw]
        if missing:
            raise ManifestError(f"manifest missing fields: {', '.join(missing)}")
        dataset_urn = str(raw["dataset_urn"])
        if not dataset_urn.startswith("urn:li:dataset:"):
            raise ManifestError("dataset_urn must be a DataHub dataset URN")
        changes_raw = raw["changes"]
        if not isinstance(changes_raw, list) or not changes_raw:
            raise ManifestError("changes must be a non-empty array")
        changes = tuple(
            ProposedChange.from_dict(item, index=index)
            for index, item in enumerate(changes_raw)
            if isinstance(item, dict)
        )
        if len(changes) != len(changes_raw):
            raise ManifestError("every changes entry must be an object")
        return cls(
            change_id=str(raw["change_id"]),
            as_of=str(raw["as_of"]),
            dataset_urn=dataset_urn,
            environment=str(raw["environment"]),
            changes=changes,
        )


@dataclass(frozen=True)
class ToolReceipt:
    sequence: int
    tool: str
    arguments: dict[str, Any]
    response_sha256: str


@dataclass(frozen=True)
class AuditIssue:
    issue_id: str
    rule_id: str
    severity: str
    field: str
    title: str
    explanation: str
    evidence_receipts: tuple[int, ...]
    downstream_assets: tuple[str, ...] = ()
    recommended_action: str = ""

    def __post_init__(self) -> None:
        if self.severity not in ALLOWED_SEVERITIES:
            raise ValueError(f"invalid severity: {self.severity}")


@dataclass(frozen=True)
class AuditReport:
    report_version: str
    change_id: str
    as_of: str
    dataset_urn: str
    environment: str
    decision: str
    risk_counts: dict[str, int]
    issues: tuple[AuditIssue, ...]
    evidence: tuple[ToolReceipt, ...]
    limitations: tuple[str, ...]
    metrics: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
