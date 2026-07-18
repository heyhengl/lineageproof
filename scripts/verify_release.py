#!/usr/bin/env python3
"""Verify the checked-in synthetic LineageProof release artifacts."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

SECRET_PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "email": re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "credential_url": re.compile(r"https?://[^\s/:]+:[^\s/@]+@"),
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(value) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def iter_release_text(root: Path):
    ignored = {".git", ".venv", ".pytest_cache", ".ruff_cache", "design", "dist"}
    extensions = {".md", ".py", ".swift", ".toml", ".json", ".txt", ".gitignore"}
    for path in root.rglob("*"):
        if not path.is_file() or any(part in ignored for part in path.parts):
            continue
        if path.name in {"uv.lock", "LICENSE"}:
            continue
        if path.suffix in extensions or path.name == ".gitignore":
            yield path, path.read_text(encoding="utf-8")


def verify(root: Path) -> dict[str, object]:
    output = root / "examples" / "expected-output"
    required = {
        "audit-report.json",
        "datahub-writeback-preview.json",
        "lineageproof.sarif",
        "proposed-auditable-mutation-receipt.json",
        "remediation-plan.md",
        "synthetic-writeback-receipt.json",
        "tool-call-receipts.json",
    }
    actual = {path.name for path in output.iterdir() if path.is_file()}
    if actual != required:
        raise AssertionError(
            f"expected outputs differ: required={sorted(required)}, actual={sorted(actual)}"
        )

    report = load_json(output / "audit-report.json")
    if report["decision"] != "request_remediation":
        raise AssertionError("synthetic demo must request remediation")
    if report["risk_counts"] != {"critical": 1, "high": 3, "low": 0, "medium": 0}:
        raise AssertionError("unexpected synthetic risk counts")

    preview = load_json(output / "datahub-writeback-preview.json")
    if preview.get("dry_run") is not True or preview.get("mutation_tools_invoked") is not False:
        raise AssertionError("write-back preview crossed the no-mutation boundary")
    if preview.get("audit_report_sha256") != canonical_hash(report):
        raise AssertionError("write-back preview is not bound to the audit report")

    writeback_receipt = load_json(output / "synthetic-writeback-receipt.json")
    if writeback_receipt.get("status") != "pass":
        raise AssertionError("synthetic write-back did not pass")
    if writeback_receipt.get("execution_mode") != "synthetic_fixture":
        raise AssertionError("write-back proof must use the synthetic fixture")
    if writeback_receipt.get("mutation_tools_invoked") is not True:
        raise AssertionError("synthetic write-back did not invoke mutation tools")
    if writeback_receipt.get("external_metadata_modified") is not False:
        raise AssertionError("synthetic write-back crossed the external-state boundary")
    if writeback_receipt.get("audit_report_sha256") != canonical_hash(report):
        raise AssertionError("synthetic receipt is not bound to the audit report")
    if writeback_receipt.get("writeback_plan_sha256") != canonical_hash(preview):
        raise AssertionError("synthetic receipt is not bound to the write-back plan")
    completed_mutations = writeback_receipt.get("completed_calls")
    if not isinstance(completed_mutations, list) or len(completed_mutations) != 5:
        raise AssertionError("synthetic write-back must contain five mutation receipts")
    if {item.get("tool") for item in completed_mutations} != {
        "add_tags",
        "update_description",
    }:
        raise AssertionError("unexpected mutation tools in synthetic receipt")

    proposed_receipt = load_json(output / "proposed-auditable-mutation-receipt.json")
    if proposed_receipt.get("proposal_status") != "not_an_implemented_datahub_api":
        raise AssertionError("proposed receipt must not imply an implemented DataHub API")
    if proposed_receipt.get("execution_mode") != "proposal_fixture":
        raise AssertionError("proposed receipt must remain a fixture")
    if proposed_receipt.get("external_metadata_modified") is not False:
        raise AssertionError("proposed receipt crossed the external-state boundary")
    if proposed_receipt.get("status") != "changed":
        raise AssertionError("proposed receipt does not exercise the changed outcome")
    before_hash = proposed_receipt.get("before", {}).get("normalized_sha256")
    after_hash = proposed_receipt.get("after", {}).get("normalized_sha256")
    readback_hash = proposed_receipt.get("readback", {}).get("normalized_sha256")
    key_hash = proposed_receipt.get("idempotency_key_sha256")
    for label, digest in {
        "before": before_hash,
        "after": after_hash,
        "readback": readback_hash,
        "idempotency_key": key_hash,
    }.items():
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AssertionError(f"invalid proposed {label} hash")
    if before_hash == after_hash or readback_hash != after_hash:
        raise AssertionError("proposed receipt does not prove a changed, matched read-back")
    privacy = proposed_receipt.get("privacy", {})
    if any(
        privacy.get(field) is not False
        for field in (
            "credentials_retained",
            "full_metadata_retained",
            "idempotency_key_retained",
        )
    ):
        raise AssertionError("proposed receipt retains disallowed sensitive material")
    if "does not claim a live DataHub mutation" not in proposed_receipt.get("truth_boundary", ""):
        raise AssertionError("proposed receipt is missing its live-state truth boundary")

    receipts = load_json(output / "tool-call-receipts.json")
    if len(receipts) != 8:
        raise AssertionError("synthetic demo must produce eight read-tool receipts")
    allowed_receipt_keys = {"arguments", "response_sha256", "sequence", "tool"}
    for receipt in receipts:
        if set(receipt) != allowed_receipt_keys:
            raise AssertionError("receipt contains unexpected or raw response fields")
        if not re.fullmatch(r"[0-9a-f]{64}", receipt["response_sha256"]):
            raise AssertionError("invalid response hash")
        if receipt["tool"] in {"add_tags", "update_description"}:
            raise AssertionError("mutation tool appeared in executed receipts")

    findings: list[dict[str, str]] = []
    scanned = 0
    for path, text in iter_release_text(root):
        scanned += 1
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append({"file": str(path.relative_to(root)), "pattern": name})
    if findings:
        raise AssertionError(f"privacy scan findings: {findings}")

    return {
        "status": "pass",
        "decision": report["decision"],
        "issues": len(report["issues"]),
        "receipts": len(receipts),
        "mutation_tools_invoked": False,
        "synthetic_mutation_tools_invoked": True,
        "proposed_auditable_receipt_verified": True,
        "external_metadata_modified": False,
        "privacy_files_scanned": scanned,
        "privacy_findings": 0,
    }


def main() -> int:
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path(__file__).parents[1]
    print(json.dumps(verify(root), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
