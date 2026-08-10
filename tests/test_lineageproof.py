from __future__ import annotations

import asyncio
import copy
import json
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from lineageproof.agent import AuditAgent, build_writeback_preview
from lineageproof.cli import main
from lineageproof.context import FixtureToolSession
from lineageproof.merchant_scan import scan_legacy_content_api, write_scan_artifacts
from lineageproof.models import AuditManifest, ManifestError
from lineageproof.output import write_artifacts
from lineageproof.writeback import WritebackSafetyError, execute_writeback
from lineageproof.zipapp_build import build_merchant_scan_zipapp

ROOT = Path(__file__).parents[1]
CHANGE = ROOT / "examples" / "schema-change.json"
FIXTURE = ROOT / "examples" / "datahub-mcp-fixture.json"
WRITEBACK_FIXTURE = ROOT / "examples" / "datahub-mcp-writeback-fixture.json"


def load_manifest() -> AuditManifest:
    return AuditManifest.from_dict(json.loads(CHANGE.read_text(encoding="utf-8")))


async def run_demo():
    session = FixtureToolSession(FIXTURE)
    async with session:
        report = await AuditAgent(session).run(load_manifest())
    return report


async def run_fixture(path: Path):
    session = FixtureToolSession(path)
    async with session:
        return await AuditAgent(session).run(load_manifest())


def test_demo_requests_remediation_with_evidence() -> None:
    report = asyncio.run(run_demo())
    assert report.decision == "request_remediation"
    assert report.risk_counts == {"critical": 1, "high": 3, "medium": 0, "low": 0}
    assert report.metrics == {"changed_fields": 3, "tool_calls": 8, "issues": 4}
    assert [issue.rule_id for issue in report.issues] == [
        "LP_TYPE_CONTRACT",
        "LP_NULLABILITY_USAGE",
        "LP_BREAKING_FIELD_IDENTITY",
        "LP_PII_PROPAGATION",
    ]
    assert [receipt.sequence for receipt in report.evidence] == list(range(1, 9))
    assert all(
        re.fullmatch(r"[0-9a-f]{64}", receipt.response_sha256) for receipt in report.evidence
    )


def test_artifacts_are_deterministic_and_writeback_is_preview(tmp_path: Path) -> None:
    report = asyncio.run(run_demo())
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_artifacts(report, first)
    write_artifacts(report, second)
    for path in sorted(item.name for item in first.iterdir()):
        assert (first / path).read_bytes() == (second / path).read_bytes()

    preview = json.loads((first / "datahub-writeback-preview.json").read_text())
    assert preview["dry_run"] is True
    assert preview["mutation_tools_invoked"] is False
    assert {call["tool"] for call in preview["calls"]} == {"add_tags", "update_description"}


def test_receipts_do_not_persist_raw_responses_or_credentials(tmp_path: Path) -> None:
    report = asyncio.run(run_demo())
    write_artifacts(report, tmp_path)
    receipts = (tmp_path / "tool-call-receipts.json").read_text(encoding="utf-8")
    assert "searchResults" not in receipts
    assert "DATAHUB_GMS_TOKEN" not in receipts
    assert "authorization" not in receipts.lower()
    assert not re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", receipts)


def test_cli_generates_expected_files(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(
        [
            "audit",
            "--change",
            str(CHANGE),
            "--fixture",
            str(FIXTURE),
            "--out",
            str(tmp_path),
        ]
    )
    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["decision"] == "request_remediation"
    assert set(path.name for path in tmp_path.iterdir()) == {
        "audit-report.json",
        "datahub-writeback-preview.json",
        "lineageproof.sarif",
        "remediation-plan.md",
        "tool-call-receipts.json",
    }


def test_merchant_scan_is_deterministic_and_does_not_emit_source_text(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    secret_marker = "PRIVATE-OFFER-123"
    (source / "catalog.py").write_text(
        "\n".join(
            [
                "from googleapiclient.discovery import build",
                'client = build("content", "v2.1")',
                f"# {secret_marker}",
                "client.products.insert(merchantId=123, body={})",
                "client.productstatuses.list(merchantId=123)",
            ]
        ),
        encoding="utf-8",
    )
    (source / "batch.ts").write_text(
        'const endpoint = "https://shoppingcontent.googleapis.com/content/v2.1";\n'
        "service.products.customBatch(request);\n",
        encoding="utf-8",
    )

    first = scan_legacy_content_api(source)
    second = scan_legacy_content_api(source)
    assert first == second
    assert first["source_label"] == "authorized-source"
    assert "root_name" not in first
    assert first["legacy_exposure_found"] is True
    assert first["findings_count"] >= 5
    serialized = json.dumps(first)
    assert secret_marker not in serialized
    assert "merchantId=123" not in serialized
    assert all(re.fullmatch(r"[0-9a-f]{64}", row["line_sha256"]) for row in first["findings"])

    artifacts = write_scan_artifacts(first, tmp_path / "out")
    assert set(Path(path).name for path in artifacts.values()) == {
        "merchant-api-legacy-inventory.csv",
        "merchant-api-legacy-inventory.json",
    }
    assert secret_marker not in (tmp_path / "out" / "merchant-api-legacy-inventory.csv").read_text()
    assert (
        "Static source evidence only"
        in (tmp_path / "out" / "merchant-api-legacy-inventory.csv").read_text()
    )


def test_merchant_scan_excludes_dependencies_binary_and_large_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    (source / "node_modules" / "pkg").mkdir(parents=True)
    (source / "node_modules" / "pkg" / "legacy.js").write_text("ShoppingContent.products.list")
    (source / "binary.py").write_bytes(b"ShoppingContent\x00products.list")
    (source / "large.py").write_text("ShoppingContent\n" * 20)
    (source / "clean.py").write_text("products.list()\nproductstatuses.list()\n")

    report = scan_legacy_content_api(source, max_file_bytes=60)
    assert report["findings_count"] == 0
    assert report["scanned_files"] == 1
    assert report["skipped_files"] == [
        {"path": "binary.py", "reason": "binary_content"},
        {"path": "large.py", "reason": "file_too_large"},
    ]


def test_merchant_scan_cli_writes_bounded_inventory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "job.gs").write_text("ShoppingContent.Products.list(merchantId);\n")
    output = tmp_path / "out"

    exit_code = main(["merchant-scan", "--source", str(source), "--out", str(output)])
    assert exit_code == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["legacy_exposure_found"] is True
    assert receipt["findings_count"] >= 1
    assert {path.name for path in output.iterdir()} == {
        "merchant-api-legacy-inventory.csv",
        "merchant-api-legacy-inventory.json",
    }


def test_merchant_scan_zipapp_is_deterministic_and_runs_without_install(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first.pyz"
    second = tmp_path / "second.pyz"
    build_merchant_scan_zipapp(ROOT / "src", first)
    build_merchant_scan_zipapp(ROOT / "src", second)
    assert first.read_bytes() == second.read_bytes()

    source = tmp_path / "source"
    source.mkdir()
    secret_marker = "PRIVATE-CATALOG-CODE"
    (source / "catalog.py").write_text(
        'client = build("content", "v2.1")\n'
        f"# {secret_marker}\n"
        "client.products.insert(merchantId=123, body={})\n",
        encoding="utf-8",
    )
    output = tmp_path / "out"
    completed = subprocess.run(
        [
            sys.executable,
            "-S",
            str(first),
            "merchant-scan",
            "--source",
            str(source),
            "--out",
            str(output),
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=tmp_path,
    )

    receipt = json.loads(completed.stdout)
    assert receipt["legacy_exposure_found"] is True
    assert receipt["findings_count"] >= 2
    assert secret_marker not in (output / "merchant-api-legacy-inventory.json").read_text()
    assert secret_marker not in (output / "merchant-api-legacy-inventory.csv").read_text()


def test_manifest_rejects_non_datahub_urn() -> None:
    raw = json.loads(CHANGE.read_text(encoding="utf-8"))
    raw["dataset_urn"] = "warehouse.orders"
    with pytest.raises(ManifestError, match="DataHub dataset URN"):
        AuditManifest.from_dict(raw)


def test_writeback_contract_matches_official_tool_arguments() -> None:
    report = asyncio.run(run_demo())
    preview = build_writeback_preview(report)
    add_tags = next(call for call in preview["calls"] if call["tool"] == "add_tags")
    assert set(add_tags["arguments"]) == {"tag_urns", "entity_urns"}
    updates = [call for call in preview["calls"] if call["tool"] == "update_description"]
    assert updates
    assert all(
        set(call["arguments"]) == {"entity_urn", "column_path", "operation", "description"}
        for call in updates
    )
    assert preview["audit_report_sha256"]


def test_writeback_preflight_invokes_no_mutations() -> None:
    async def scenario():
        report = await run_demo()
        plan = build_writeback_preview(report)
        session = FixtureToolSession(WRITEBACK_FIXTURE)
        async with session:
            receipt = await execute_writeback(
                report.to_dict(),
                plan,
                session,
                apply=False,
                acknowledgement=None,
            )
        return receipt

    receipt = asyncio.run(scenario())
    assert receipt["status"] == "preflight_pass"
    assert receipt["mutation_tools_invoked"] is False
    assert receipt["completed_calls"] == []
    assert receipt["external_metadata_modified"] is False


def test_synthetic_writeback_requires_exact_acknowledgement() -> None:
    async def scenario():
        report = await run_demo()
        plan = build_writeback_preview(report)
        session = FixtureToolSession(WRITEBACK_FIXTURE)
        async with session:
            with pytest.raises(WritebackSafetyError, match="--acknowledge"):
                await execute_writeback(
                    report.to_dict(),
                    plan,
                    session,
                    apply=True,
                    acknowledgement="yes",
                )
        return session.receipts

    assert asyncio.run(scenario()) == []


def test_synthetic_writeback_executes_bounded_plan_without_external_state() -> None:
    async def scenario():
        report = await run_demo()
        plan = build_writeback_preview(report)
        session = FixtureToolSession(WRITEBACK_FIXTURE)
        async with session:
            return await execute_writeback(
                report.to_dict(),
                plan,
                session,
                apply=True,
                acknowledgement=f"APPLY {report.change_id}",
            )

    receipt = asyncio.run(scenario())
    assert receipt["status"] == "pass"
    assert receipt["execution_mode"] == "synthetic_fixture"
    assert receipt["mutation_tools_invoked"] is True
    assert receipt["external_metadata_modified"] is False
    assert len(receipt["completed_calls"]) == 5
    assert {item["tool"] for item in receipt["completed_calls"]} == {
        "add_tags",
        "update_description",
    }


def test_writeback_rejects_tampered_plan_before_mutation() -> None:
    async def scenario():
        report = await run_demo()
        plan = copy.deepcopy(build_writeback_preview(report))
        plan["calls"][0]["arguments"]["entity_urns"] = ["urn:li:dataset:other"]
        session = FixtureToolSession(WRITEBACK_FIXTURE)
        async with session:
            with pytest.raises(WritebackSafetyError, match="does not exactly match"):
                await execute_writeback(
                    report.to_dict(),
                    plan,
                    session,
                    apply=True,
                    acknowledgement=f"APPLY {report.change_id}",
                )
        return session.receipts

    assert asyncio.run(scenario()) == []


def test_missing_owner_is_reported_without_exposing_identity(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    entity_response = next(item for item in fixture["responses"] if item["tool"] == "get_entities")
    entity_response["result"].pop("ownership")
    fixture_path = tmp_path / "missing-owner.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    report = asyncio.run(run_fixture(fixture_path))
    owner_issue = next(issue for issue in report.issues if issue.rule_id == "LP_MISSING_OWNER")
    assert owner_issue.severity == "medium"
    assert owner_issue.field == "<dataset>"
    assert "@" not in owner_issue.explanation


def test_stale_schema_baseline_blocks_approval(tmp_path: Path) -> None:
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    schema_response = next(
        item for item in fixture["responses"] if item["tool"] == "list_schema_fields"
    )
    status = next(
        item for item in schema_response["result"]["fields"] if item["fieldPath"] == "status"
    )
    status["nativeDataType"] = "INTEGER"
    fixture_path = tmp_path / "stale-schema.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")

    report = asyncio.run(run_fixture(fixture_path))
    stale = next(issue for issue in report.issues if issue.rule_id == "LP_STALE_BASELINE")
    assert stale.severity == "critical"
    assert stale.field == "status"
    assert report.decision == "request_remediation"


def test_checked_release_artifacts_pass_verifier() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "verify_release.py"), str(ROOT)],
        check=True,
        capture_output=True,
        text=True,
    )
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "pass"
    assert receipt["privacy_findings"] == 0
    assert receipt["mutation_tools_invoked"] is False


def test_source_release_archive_is_scoped_and_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    for output in (first, second):
        result = subprocess.run(
            [sys.executable, "scripts/package_release.py", "--out", str(output)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        assert json.loads(result.stdout)["status"] == "pass"

    first_manifest = json.loads(
        (first / "lineageproof-0.1.0-source-manifest.json").read_text(encoding="utf-8")
    )
    second_manifest = json.loads(
        (second / "lineageproof-0.1.0-source-manifest.json").read_text(encoding="utf-8")
    )
    assert first_manifest["archive_sha256"] == second_manifest["archive_sha256"]
    assert first_manifest["scope"]["design_assets_included"] is False

    with ZipFile(first / "lineageproof-0.1.0-source.zip") as archive:
        names = archive.namelist()
    assert names
    assert "src/lineageproof/merchant_scan.py" in names
    assert "examples/merchant-api-legacy-source/catalog_job.py" in names
    assert "examples/merchant-api-legacy-source/scheduled_feed.gs" in names
    assert all("design" not in Path(name).parts for name in names)
    assert all("dist" not in Path(name).parts for name in names)
