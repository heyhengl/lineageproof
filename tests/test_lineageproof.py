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
from lineageproof.models import AuditManifest, ManifestError
from lineageproof.output import write_artifacts
from lineageproof.writeback import WritebackSafetyError, execute_writeback

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
    assert all("design" not in Path(name).parts for name in names)
    assert all("dist" not in Path(name).parts for name in names)
