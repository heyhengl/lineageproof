#!/usr/bin/env python3
"""Render an evidence-grounded LineageProof demo storyboard and narration segments."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1920
HEIGHT = 1080
BACKGROUND = "#F2F0E9"
PAPER = "#FBFAF6"
INK = "#181C21"
MUTED = "#686D73"
DIVIDER = "#D1CEC5"
BLUE = "#315E7A"
CRITICAL = "#A33F36"
PASS = "#2F6A4E"
TERMINAL = "#12161A"
TERMINAL_TEXT = "#E8ECEF"
TERMINAL_MUTED = "#96A0A8"

FONT_DISPLAY = "/System/Library/Fonts/NewYork.ttf"
FONT_SANS = "/System/Library/Fonts/SFNS.ttf"
FONT_MONO = "/System/Library/Fonts/SFNSMono.ttf"


@dataclass(frozen=True)
class Scene:
    scene_id: str
    eyebrow: str
    title: str
    narration: str
    caption: str
    mode: str


SCENES = (
    Scene(
        "01",
        "LINEAGEPROOF / DATAHUB MCP",
        "Schema-change evidence before merge",
        (
            "A schema change rarely fails where it is written. It fails downstream, in a "
            "dashboard, join, contract, or sensitive-data control. LineageProof turns DataHub "
            "context into a reviewable decision before a migration ships."
        ),
        "One change. Its downstream evidence. One explicit decision.",
        "cover",
    ),
    Scene(
        "02",
        "THE PROPOSED CHANGE",
        "Start with a typed, reviewable manifest",
        (
            "The input names one DataHub dataset and records each field before and after the "
            "change. This example renames a monetary field, relaxes nullability, and removes a "
            "sensitive address. Invalid or incomplete manifests stop before any tool call."
        ),
        "Typed before/after state prevents an ambiguous review baseline.",
        "diff",
    ),
    Scene(
        "03",
        "CONTEXT COLLECTION",
        "Read the graph before judging the diff",
        (
            "The agent first reads entity identity, ownership, and the current schema. For every "
            "changed field, it then retrieves downstream lineage and observed query context. "
            "Eight read calls form the evidence chain for this three-field scenario."
        ),
        "Entity + schema + lineage + observed queries",
        "tools",
    ),
    Scene(
        "04",
        "ACTUAL CLI RUN / SYNTHETIC FIXTURE",
        "One command produces five review artifacts",
        (
            "This is the verified public fixture run. It needs no credentials and sends nothing "
            "outside the machine. The command returns request remediation and writes a JSON "
            "audit, human remediation plan, S A R I F, hashed receipts, and a write-back preview."
        ),
        "The displayed result is captured from the installed CLI, not a mockup.",
        "terminal",
    ),
    Scene(
        "05",
        "DECISION",
        "One critical issue. Three high issues.",
        (
            "The decision is request remediation. A field identity change reaches downstream "
            "assets, nullable data conflicts with observed use, a type change violates a query "
            "contract, and sensitive data reaches a target without matching classification."
        ),
        "Critical or high findings block approval under the explicit rule contract.",
        "decision",
    ),
    Scene(
        "06",
        "PROVENANCE",
        "Every finding cites exact tool receipts",
        (
            "Each finding points to the exact receipt sequence used as evidence. Receipts keep the "
            "tool name, non-secret arguments, sequence number, and response hash. Raw DataHub "
            "responses, credentials, and account data are not copied into the public record."
        ),
        "Useful provenance without duplicating potentially sensitive metadata.",
        "receipts",
    ),
    Scene(
        "07",
        "REMEDIATION",
        "The output tells reviewers what must change",
        (
            "The human plan is not a generic warning. It proposes compatibility fields or a "
            "versioned migration, explicit null semantics and backfill, downstream contract "
            "tests, owner notification, and approved classification propagation before deploy."
        ),
        "Findings become concrete, field-level actions.",
        "document",
    ),
    Scene(
        "08",
        "SAFE DEFAULT",
        "The audit command never mutates metadata",
        (
            "The audit produces a deterministic mutation plan, but the plan states dry run true "
            "and mutation tools invoked false. It is bound to the exact audit-report hash, so a "
            "modified plan cannot quietly inherit the report's evidence."
        ),
        "A plan is not proof that DataHub changed.",
        "dryrun",
    ),
    Scene(
        "09",
        "EXPLICIT WRITE-BACK GATE",
        "Apply requires the plan, tools, and change ID",
        (
            "Write-back is a separate command. It checks that every required mutation tool is "
            "available, allowlists add tags and update description, caps execution at one hundred "
            "calls, and requires both apply and an acknowledgement equal to the audited change ID."
        ),
        "Tampered plan, missing tool, or wrong acknowledgement: zero mutation calls.",
        "gate",
    ),
    Scene(
        "10",
        "TRUTH BOUNDARY",
        "Five synthetic calls. Zero external changes.",
        (
            "The public mutation proof exercises one tag call and four description updates against "
            "a synthetic fixture. Its receipt says external metadata modified false. A future live "
            "response would remain unverified until an independent read-back proves the target "
            "state."
        ),
        "Tool invocation and verified external state are different claims.",
        "writeback",
    ),
    Scene(
        "11",
        "RELEASE VERIFICATION",
        "Tests, privacy scan, package, and source scope",
        (
            "Fourteen tests cover the decision rules, deterministic outputs, mutation gates, and "
            "tamper rejection. The release verifier checks eight read receipts, five synthetic "
            "mutation receipts, and every public text file for privacy leaks."
        ),
        "The final wheel and allowlisted source archive also pass isolated installation.",
        "verify",
    ),
    Scene(
        "12",
        "READY FOR PUBLIC APACHE-2.0 RELEASE",
        "Evidence that survives the handoff",
        (
            "LineageProof makes schema-change review reproducible, explainable, and safe by "
            "default. "
            "A reviewer can see what changed, which DataHub evidence matters, why the change is "
            "blocked, and exactly what did and did not happen."
        ),
        "DataHub context at the center; privacy and truth boundaries intact.",
        "close",
    ),
)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


DISPLAY_92 = font(FONT_DISPLAY, 92)
DISPLAY_64 = font(FONT_DISPLAY, 64)
SANS_36 = font(FONT_SANS, 36)
SANS_31 = font(FONT_SANS, 31)
SANS_27 = font(FONT_SANS, 27)
SANS_23 = font(FONT_SANS, 23)
SANS_19 = font(FONT_SANS, 19)
MONO_29 = font(FONT_MONO, 29)
MONO_25 = font(FONT_MONO, 25)
MONO_21 = font(FONT_MONO, 21)


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(text, width=width, break_long_words=False))


def draw_header(draw: ImageDraw.ImageDraw, scene: Scene, index: int) -> None:
    draw.text((82, 62), scene.eyebrow, font=SANS_19, fill=BLUE)
    draw.text((1838, 62), f"{index:02d} / {len(SCENES):02d}", font=MONO_21, fill=MUTED, anchor="ra")
    draw.line((82, 112, 1838, 112), fill=DIVIDER, width=2)


def draw_footer(draw: ImageDraw.ImageDraw, scene: Scene, index: int) -> None:
    draw.line((82, 974, 1838, 974), fill=DIVIDER, width=2)
    draw.text((82, 998), scene.caption, font=SANS_23, fill=INK)
    start = 82
    width = 1756
    draw.rectangle((start, 1054, start + width, 1058), fill="#D8D5CD")
    draw.rectangle((start, 1054, start + int(width * index / len(SCENES)), 1058), fill=BLUE)


def draw_title(draw: ImageDraw.ImageDraw, scene: Scene) -> None:
    draw.text((82, 154), wrap(scene.title, 34), font=DISPLAY_64, fill=INK, spacing=4)


def draw_rail(draw: ImageDraw.ImageDraw, title: str, lines: list[tuple[str, str]]) -> None:
    draw.line((1398, 188, 1398, 922), fill=DIVIDER, width=2)
    draw.text((1440, 202), title.upper(), font=SANS_19, fill=MUTED)
    y = 256
    for label, value in lines:
        draw.text((1440, y), label.upper(), font=SANS_19, fill=MUTED)
        y += 30
        draw.text((1440, y), wrap(value, 24), font=SANS_27, fill=INK, spacing=7)
        y += 54 + 34 * max(0, len(textwrap.wrap(value, width=24)) - 1)
        draw.line((1440, y, 1838, y), fill=DIVIDER, width=1)
        y += 34


def terminal(draw: ImageDraw.ImageDraw, lines: list[tuple[str, str]], y: int = 300) -> None:
    draw.rectangle((82, y, 1348, 912), fill=TERMINAL)
    draw.rectangle((82, y, 1348, y + 42), fill="#1C2228")
    draw.ellipse((108, y + 14, 120, y + 26), fill="#B95D55")
    draw.ellipse((130, y + 14, 142, y + 26), fill="#C39A4A")
    draw.ellipse((152, y + 14, 164, y + 26), fill="#5D9B6A")
    ty = y + 76
    for kind, text in lines:
        color = TERMINAL_TEXT if kind == "out" else ("#7FB2D0" if kind == "cmd" else TERMINAL_MUTED)
        prefix = "$ " if kind == "cmd" else "  "
        for line in text.splitlines():
            draw.text((116, ty), prefix + line, font=MONO_25, fill=color)
            prefix = "  "
            ty += 38


def render_scene(scene: Scene, index: int, context: dict[str, Any]) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    draw_header(draw, scene, index)
    draw_footer(draw, scene, index)

    if scene.mode == "cover":
        draw.text((118, 224), "LineageProof", font=DISPLAY_92, fill=INK)
        draw.text((118, 354), wrap(scene.title, 28), font=DISPLAY_64, fill=INK, spacing=6)
        draw.line((118, 566, 986, 566), fill=BLUE, width=5)
        draw.text(
            (118, 620),
            "DataHub entity · schema · lineage · queries",
            font=MONO_29,
            fill=BLUE,
        )
        draw.text(
            (118, 704),
            wrap(
                "Deterministic decisions, hash-only receipts, explicit write-back truth "
                "boundaries.",
                50,
            ),
            font=SANS_36,
            fill=MUTED,
            spacing=10,
        )
        draw.text((1450, 278), "DECISION", font=SANS_19, fill=MUTED)
        draw.text((1450, 320), "REQUEST\nREMEDIATION", font=DISPLAY_64, fill=CRITICAL, spacing=6)
        draw.text((1450, 532), "1 critical\n3 high", font=MONO_29, fill=INK, spacing=12)
        return image

    draw_title(draw, scene)
    if scene.mode == "diff":
        draw.text((82, 304), "schema-change.json", font=MONO_21, fill=MUTED)
        code = [
            ('"order_total"', 'rename  →  "gross_amount"'),
            ('"status"', "nullable  false  →  true"),
            ('"shipping_address"', "remove  →  null"),
        ]
        y = 356
        for field, change in code:
            draw.text((104, y), field, font=MONO_29, fill=INK)
            draw.text((504, y), change, font=MONO_29, fill=CRITICAL if "remove" in change else BLUE)
            draw.line((104, y + 54, 1320, y + 54), fill=DIVIDER, width=1)
            y += 112
        draw_rail(
            draw,
            "Manifest gate",
            [
                ("Dataset", "One DataHub URN"),
                ("Fields", "Three typed changes"),
                ("Failure mode", "Reject before tool access"),
            ],
        )
    elif scene.mode == "tools":
        tools = [
            ("01", "get_entities", "identity + ownership"),
            ("02", "list_schema_fields", "current field contract"),
            ("03–08", "get_lineage / get_dataset_queries", "downstream impact + observed SQL"),
        ]
        y = 316
        for number, name, purpose in tools:
            draw.text((98, y), number, font=MONO_29, fill=BLUE)
            draw.text((226, y), name, font=MONO_29, fill=INK)
            draw.text((226, y + 48), purpose, font=SANS_27, fill=MUTED)
            draw.line((98, y + 96, 1328, y + 96), fill=DIVIDER, width=1)
            y += 152
        draw_rail(
            draw,
            "Evidence scope",
            [
                ("Calls", "8 read tools"),
                ("Changed fields", "3"),
                ("Persisted raw responses", "None"),
            ],
        )
    elif scene.mode == "terminal":
        output = context["audit_cli"]
        terminal(
            draw,
            [
                (
                    "cmd",
                    "lineageproof audit --change examples/schema-change.json \\\n"
                    "  --fixture examples/datahub-mcp-fixture.json \\\n"
                    "  --out dist/demo-video/run",
                ),
                ("out", f"change_id: {output['change_id']}"),
                ("out", f"decision: {output['decision']}"),
                ("out", "risk_counts: critical 1 · high 3 · medium 0 · low 0"),
                ("dim", "artifacts: audit · remediation · SARIF · receipts · write-back preview"),
            ],
            y=322,
        )
        draw_rail(
            draw,
            "Run boundary",
            [
                ("Provider", "Synthetic fixture"),
                ("Credentials", "None"),
                ("External writes", "None"),
            ],
        )
    elif scene.mode == "decision":
        issues = context["report"]["issues"]
        y = 310
        for issue in issues:
            color = CRITICAL if issue["severity"] == "critical" else INK
            draw.text((94, y), issue["issue_id"], font=MONO_25, fill=BLUE)
            draw.text((238, y), issue["field"], font=MONO_25, fill=color)
            draw.text((610, y), issue["title"], font=SANS_27, fill=color)
            draw.line((94, y + 55, 1332, y + 55), fill=DIVIDER, width=1)
            y += 118
        draw_rail(
            draw,
            "Decision",
            [("Result", "Request remediation"), ("Critical", "1"), ("High", "3")],
        )
    elif scene.mode == "receipts":
        receipts = context["receipts"]
        y = 310
        for item in receipts[:4]:
            draw.text((94, y), f"{item['sequence']:02d}", font=MONO_25, fill=BLUE)
            draw.text((186, y), item["tool"], font=MONO_25, fill=INK)
            draw.text((600, y), item["response_sha256"][:24] + "…", font=MONO_21, fill=MUTED)
            y += 82
        draw.text((94, y + 12), "…", font=DISPLAY_64, fill=DIVIDER)
        last = receipts[-1]
        draw.text((94, y + 108), f"{last['sequence']:02d}", font=MONO_25, fill=BLUE)
        draw.text((186, y + 108), last["tool"], font=MONO_25, fill=INK)
        draw.text((600, y + 108), last["response_sha256"][:24] + "…", font=MONO_21, fill=MUTED)
        draw_rail(
            draw,
            "Receipt shape",
            [
                ("Stored", "Tool + args + hash"),
                ("Raw response", "Not stored"),
                ("Secrets", "Not accepted"),
            ],
        )
    elif scene.mode == "document":
        actions = [
            "Add a compatibility field or versioned migration before removal.",
            "Define null semantics, backfill rows, and add explicit query guards.",
            "Run representative downstream contract tests for the type change.",
            "Confirm classification with owners and propagate the approved tag.",
        ]
        y = 318
        for number, action in enumerate(actions, 1):
            draw.text((98, y), f"{number}.", font=MONO_29, fill=BLUE)
            draw.text((172, y), wrap(action, 58), font=SANS_31, fill=INK, spacing=8)
            y += 128
        draw_rail(
            draw,
            "Reviewer output",
            [("Format", "Markdown"), ("Scope", "Field-level"), ("Owner action", "Explicit")],
        )
    elif scene.mode == "dryrun":
        preview = context["preview"]
        terminal(
            draw,
            [
                ("out", '"dry_run": true'),
                ("out", '"mutation_tools_invoked": false'),
                ("out", f'"change_id": "{preview["change_id"]}"'),
                ("out", f'"audit_report_sha256": "{preview["audit_report_sha256"][:32]}…"'),
                ("dim", f"planned_calls: {len(preview['calls'])}"),
            ],
            y=342,
        )
        draw_rail(
            draw,
            "Default",
            [("Mutation", "False"), ("Plan binding", "Exact report hash"), ("Claim", "Plan only")],
        )
    elif scene.mode == "gate":
        steps = [
            ("1", "Exact plan", "Rebuild expected calls from the audit"),
            ("2", "Tool preflight", "Require add_tags + update_description"),
            ("3", "Bounded apply", "Allowlist and 100-call maximum"),
            ("4", "Change-ID acknowledgement", "Exact text: APPLY <change_id>"),
        ]
        y = 306
        for number, label, detail in steps:
            draw.text((96, y), number, font=DISPLAY_64, fill=BLUE)
            draw.text((192, y + 4), label, font=SANS_31, fill=INK)
            draw.text((192, y + 52), detail, font=SANS_23, fill=MUTED)
            y += 145
        draw_rail(
            draw,
            "Pre-mutation rejection",
            [("Tampered plan", "Reject"), ("Wrong ID", "Reject"), ("Missing tool", "Reject")],
        )
    elif scene.mode == "writeback":
        receipt = context["writeback"]
        terminal(
            draw,
            [
                ("out", f"execution_mode: {receipt['execution_mode']}"),
                (
                    "out",
                    f"mutation_tools_invoked: {str(receipt['mutation_tools_invoked']).lower()}",
                ),
                ("out", f"completed_calls: {len(receipt['completed_calls'])}"),
                ("out", "  add_tags: 1"),
                ("out", "  update_description: 4"),
                ("out", "external_metadata_modified: false"),
            ],
            y=342,
        )
        draw_rail(
            draw,
            "Truth boundary",
            [
                ("Tool calls", "5 synthetic"),
                ("External state", "Not modified"),
                ("Live read-back", "Still required"),
            ],
        )
    elif scene.mode == "verify":
        verifier = context["verifier"]
        terminal(
            draw,
            [
                ("cmd", "python scripts/verify_release.py"),
                ("out", f"status: {verifier['status']}"),
                ("out", f"issues: {verifier['issues']} · read receipts: {verifier['receipts']}"),
                ("out", "synthetic mutation tools invoked: true"),
                ("out", "external metadata modified: false"),
                ("out", f"privacy files scanned: {verifier['privacy_files_scanned']}"),
                ("out", f"privacy findings: {verifier['privacy_findings']}"),
            ],
            y=342,
        )
        draw_rail(
            draw,
            "Release",
            [
                ("Tests", "14 passed"),
                ("Wheel", "Isolated install"),
                ("Source", "Allowlisted files only"),
            ],
        )
    elif scene.mode == "close":
        draw.text((98, 316), "REVIEW", font=SANS_19, fill=MUTED)
        draw.text((98, 356), "What changed?", font=DISPLAY_64, fill=INK)
        draw.text((98, 474), "EVIDENCE", font=SANS_19, fill=MUTED)
        draw.text((98, 514), "What does DataHub prove?", font=DISPLAY_64, fill=INK)
        draw.text((98, 632), "DECISION", font=SANS_19, fill=MUTED)
        draw.text((98, 672), "What must happen before merge?", font=DISPLAY_64, fill=CRITICAL)
        draw_rail(
            draw,
            "Public release",
            [
                ("License", "Apache-2.0"),
                ("Demo", "Synthetic + reproducible"),
                ("Privacy findings", "0"),
            ],
        )
    return image


def run_json(command: list[str], *, cwd: Path) -> dict[str, Any]:
    result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def build_context(root: Path, output: Path) -> dict[str, Any]:
    run_dir = output / "run"
    run_dir.mkdir(parents=True, exist_ok=True)
    audit_cli = run_json(
        [
            sys.executable,
            "-m",
            "lineageproof.cli",
            "audit",
            "--change",
            "examples/schema-change.json",
            "--fixture",
            "examples/datahub-mcp-fixture.json",
            "--out",
            str(run_dir.relative_to(root)),
        ],
        cwd=root,
    )
    writeback_cli = run_json(
        [
            sys.executable,
            "-m",
            "lineageproof.cli",
            "writeback",
            "--report",
            str((run_dir / "audit-report.json").relative_to(root)),
            "--plan",
            str((run_dir / "datahub-writeback-preview.json").relative_to(root)),
            "--fixture",
            "examples/datahub-mcp-writeback-fixture.json",
            "--receipt",
            str((run_dir / "synthetic-writeback-receipt.json").relative_to(root)),
            "--apply",
            "--acknowledge",
            "APPLY scm_2026_07_18_0012",
        ],
        cwd=root,
    )
    verifier = run_json([sys.executable, "scripts/verify_release.py"], cwd=root)
    return {
        "audit_cli": audit_cli,
        "report": json.loads((run_dir / "audit-report.json").read_text(encoding="utf-8")),
        "preview": json.loads(
            (run_dir / "datahub-writeback-preview.json").read_text(encoding="utf-8")
        ),
        "receipts": json.loads((run_dir / "tool-call-receipts.json").read_text(encoding="utf-8")),
        "writeback": writeback_cli,
        "verifier": verifier,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("dist/demo-video"))
    parser.add_argument("--voice", default="Daniel")
    parser.add_argument("--rate", type=int, default=190)
    parser.add_argument("--skip-audio", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.out.resolve()
    frames = output / "frames"
    audio = output / "audio"
    frames.mkdir(parents=True, exist_ok=True)
    audio.mkdir(parents=True, exist_ok=True)
    context = build_context(root, output)

    manifest: list[dict[str, Any]] = []
    for index, scene in enumerate(SCENES, 1):
        frame_path = frames / f"scene-{scene.scene_id}.png"
        render_scene(scene, index, context).save(frame_path, format="PNG", optimize=True)
        audio_path = audio / f"scene-{scene.scene_id}.aiff"
        if not args.skip_audio:
            subprocess.run(
                [
                    "/usr/bin/say",
                    "-v",
                    args.voice,
                    "-r",
                    str(args.rate),
                    "-o",
                    str(audio_path),
                    scene.narration,
                ],
                check=True,
            )
        item = asdict(scene)
        item.update(
            {
                "frame": frame_path.name,
                "audio": audio_path.name,
            }
        )
        manifest.append(item)

    payload = {
        "schema_version": 1,
        "project": "LineageProof",
        "width": WIDTH,
        "height": HEIGHT,
        "voice": None if args.skip_audio else args.voice,
        "speech_rate": None if args.skip_audio else args.rate,
        "third_party_music": False,
        "customer_data": False,
        "credentials": False,
        "scenes": manifest,
    }
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", serialized):
        raise AssertionError("demo manifest contains an email-like string")
    (output / "scene-manifest.json").write_text(serialized, encoding="utf-8")
    print(
        json.dumps(
            {
                "audio_generated": not args.skip_audio,
                "frames": len(SCENES),
                "height": HEIGHT,
                "manifest": str(output / "scene-manifest.json"),
                "status": "pass",
                "width": WIDTH,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
