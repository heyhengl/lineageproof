"""Credential-free source inventory for legacy Content API exposure."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

SUPPORTED_SUFFIXES = {
    ".cjs",
    ".go",
    ".gs",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".mjs",
    ".php",
    ".py",
    ".rb",
    ".ts",
    ".tsx",
}
EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
    "vendor",
}

LEGACY_METHOD_RE = re.compile(
    r"\b(?P<service>accounts|accountstatuses|datafeeds|inventory|products|"
    r"productstatuses|shippingsettings)\s*[.\[]\s*[\"']?(?P<method>"
    r"custombatch|delete|get|insert|list|patch|update)[\"']?",
    re.IGNORECASE,
)

SIGNATURES = (
    (
        "content_api_endpoint",
        re.compile(r"shoppingcontent\.googleapis\.com", re.IGNORECASE),
        "Content API endpoint",
    ),
    (
        "python_content_client",
        re.compile(
            r"(?:googleapiclient\.discovery\.)?build\s*\(\s*[\"']content[\"']\s*,"
            r"\s*[\"']v2(?:\.1)?[\"']",
            re.IGNORECASE,
        ),
        "Python Shopping Content client",
    ),
    (
        "node_content_client",
        re.compile(r"@googleapis/content|\b(?:googleapis|google)\.content\s*\(", re.IGNORECASE),
        "Node Shopping Content client",
    ),
    (
        "apps_script_service",
        re.compile(
            r"\bShoppingContent\.(?:Accounts|Accountstatuses|Datafeeds|Inventory|Products|"
            r"Productstatuses|Shippingsettings)\b"
        ),
        "Google Ads Scripts Shopping Content service",
    ),
    (
        "java_content_client",
        re.compile(r"com\.google\.api\.services\.content\.ShoppingContent"),
        "Java Shopping Content client",
    ),
    (
        "php_content_client",
        re.compile(r"\bGoogle_Service_ShoppingContent\b"),
        "PHP Shopping Content client",
    ),
    (
        "go_content_client",
        re.compile(r"google\.golang\.org/api/content/v2(?:\.1)?", re.IGNORECASE),
        "Go Shopping Content client",
    ),
    (
        "ruby_content_client",
        re.compile(r"Google::Apis::ContentV2_?1", re.IGNORECASE),
        "Ruby Shopping Content client",
    ),
    (
        "custom_batch",
        re.compile(r"\bcustom[_-]?batch\b", re.IGNORECASE),
        "customBatch",
    ),
    (
        "product_statuses_service",
        re.compile(r"\bproductstatuses\b", re.IGNORECASE),
        "productstatuses service",
    ),
)

ANCHOR_PATTERN_IDS = {
    "apps_script_service",
    "content_api_endpoint",
    "go_content_client",
    "java_content_client",
    "node_content_client",
    "php_content_client",
    "python_content_client",
    "ruby_content_client",
}


def _migration_hint(service: str, method: str) -> str:
    service_lower = service.lower()
    method_lower = method.lower()
    if method_lower == "custombatch":
        return "Replace with individually tracked async calls or HTTP batching."
    if service_lower == "productstatuses":
        return "Read processed status from products.get or products.list."
    if service_lower == "products" and method_lower == "insert":
        return "Map to productInputs.insert and verify the processed Product separately."
    if service_lower == "products" and method_lower in {"patch", "update"}:
        return "Map to productInputs.patch with an explicit update mask."
    if service_lower == "products" and method_lower == "delete":
        return "Map to productInputs.delete and reconcile processed state."
    if service_lower == "products" and method_lower in {"get", "list"}:
        return f"Map to products.{method_lower} and review response/status semantics."
    return "Map this legacy contract to an exact Merchant API v1 method or retire it."


def _operation_kind(method: str) -> str:
    if method.lower() in {"get", "list"}:
        return "read"
    if method.lower() in {"custombatch", "delete", "insert", "patch", "update"}:
        return "write"
    return "unknown"


def _iter_source_files(source: Path) -> list[Path]:
    files: list[Path] = []
    for current_root, directories, filenames in os.walk(source, topdown=True, followlinks=False):
        root = Path(current_root)
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in EXCLUDED_DIRECTORIES and not (root / directory).is_symlink()
        )
        for filename in sorted(filenames):
            path = root / filename
            if path.is_symlink() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
                continue
            files.append(path)
    return sorted(files, key=lambda item: item.relative_to(source).as_posix())


def scan_legacy_content_api(source: Path, *, max_file_bytes: int = 2_000_000) -> dict[str, Any]:
    """Return a deterministic, snippet-free inventory for an authorized source tree."""

    source = source.resolve()
    if not source.is_dir():
        raise ValueError(f"source is not a directory: {source}")
    if max_file_bytes < 1:
        raise ValueError("max_file_bytes must be positive")

    findings: list[dict[str, Any]] = []
    scanned_files = 0
    skipped_files: list[dict[str, str]] = []
    seen: set[tuple[str, int, str, str]] = set()

    for path in _iter_source_files(source):
        relative = path.relative_to(source).as_posix()
        size = path.stat().st_size
        if size > max_file_bytes:
            skipped_files.append({"path": relative, "reason": "file_too_large"})
            continue
        raw = path.read_bytes()
        if b"\x00" in raw:
            skipped_files.append({"path": relative, "reason": "binary_content"})
            continue
        scanned_files += 1
        text = raw.decode("utf-8", errors="replace")
        if not any(
            pattern_id in ANCHOR_PATTERN_IDS and pattern.search(text)
            for pattern_id, pattern, _label in SIGNATURES
        ):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            line_hash = hashlib.sha256(line.encode("utf-8")).hexdigest()
            method_matches = list(LEGACY_METHOD_RE.finditer(line))
            for match in method_matches:
                service = match.group("service")
                method = match.group("method")
                legacy_method = f"{service.lower()}.{method.lower()}"
                key = (relative, line_number, "legacy_method", legacy_method)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    {
                        "path": relative,
                        "line": line_number,
                        "pattern_id": "legacy_method",
                        "legacy_service": service.lower(),
                        "legacy_method": legacy_method,
                        "operation_kind": _operation_kind(method),
                        "migration_hint": _migration_hint(service, method),
                        "line_sha256": line_hash,
                    }
                )

            for pattern_id, pattern, label in SIGNATURES:
                if not pattern.search(line):
                    continue
                duplicate_method_signature = any(
                    (pattern_id == "custom_batch" and item.group("method").lower() == "custombatch")
                    or (
                        pattern_id == "product_statuses_service"
                        and item.group("service").lower() == "productstatuses"
                    )
                    for item in method_matches
                )
                if duplicate_method_signature:
                    continue
                key = (relative, line_number, pattern_id, label)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    {
                        "path": relative,
                        "line": line_number,
                        "pattern_id": pattern_id,
                        "legacy_service": label,
                        "legacy_method": label,
                        "operation_kind": "unknown",
                        "migration_hint": (
                            "Inventory the owner and map every dependent request "
                            "and response contract."
                        ),
                        "line_sha256": line_hash,
                    }
                )

    findings.sort(
        key=lambda item: (
            item["path"],
            item["line"],
            item["pattern_id"],
            item["legacy_method"],
        )
    )
    for index, finding in enumerate(findings, start=1):
        finding["inventory_id"] = f"legacy-{index:04d}"

    return {
        "schema_version": 1,
        "source_label": "authorized-source",
        "scanned_files": scanned_files,
        "skipped_files": skipped_files,
        "findings_count": len(findings),
        "legacy_exposure_found": bool(findings),
        "findings": findings,
        "truth_boundary": (
            "Static source evidence only. No credential, API call, Merchant Center account, "
            "runtime traffic or completed migration is represented."
        ),
    }


def write_scan_artifacts(report: dict[str, Any], output_directory: Path) -> dict[str, str]:
    output_directory.mkdir(parents=True, exist_ok=True)
    json_path = output_directory / "merchant-api-legacy-inventory.json"
    csv_path = output_directory / "merchant-api-legacy-inventory.csv"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    fieldnames = [
        "inventory_id",
        "path",
        "line",
        "pattern_id",
        "legacy_service",
        "legacy_method",
        "operation_kind",
        "migration_hint",
        "line_sha256",
        "truth_boundary",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for finding in report["findings"]:
            row = {name: finding[name] for name in fieldnames if name in finding}
            row["truth_boundary"] = report["truth_boundary"]
            writer.writerow(row)
    return {"json": str(json_path), "csv": str(csv_path)}
