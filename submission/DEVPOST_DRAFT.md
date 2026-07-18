# LineageProof — Devpost submission draft

> Draft status: technically verified, not yet submitted. The repository and GitHub Pages preview
> are public and anonymously verified. A rule-compliant YouTube, Vimeo, or Youku video URL and the
> Devpost project URL remain pending.

## Project name

LineageProof

## Tagline

Evidence-first schema-change reviews powered by DataHub lineage and query context.

## Challenge category

Agents That Do Real Work. LineageProof reads DataHub context, makes a deterministic remediation
decision, and can contribute bounded tags and column guidance back to the graph only through an
explicitly authorized write-back gate.

## One-line description

LineageProof is a schema-change audit agent that uses DataHub MCP read tools to find downstream breakage, sensitive-data propagation, stale proposal baselines, and missing ownership before a migration ships.

## Inspiration

A schema change can look harmless in a pull request while silently breaking dashboards, joins, contracts, or sensitive-data controls several hops downstream. Metadata platforms already contain much of the evidence needed to catch those risks, but reviewers still have to gather and interpret it manually. We built LineageProof to turn that evidence into a deterministic, reviewable decision.

## What it does

Given a field-level change manifest and a DataHub dataset URN, LineageProof:

1. Retrieves the dataset and its ownership with `get_entities`.
2. Retrieves the current schema with `list_schema_fields`.
3. Retrieves downstream field lineage and observed query context with `get_lineage` and `get_dataset_queries`.
4. Checks baseline freshness, rename and removal impact, type compatibility, nullability-sensitive queries, ownership, and PII propagation.
5. Produces a deterministic decision: `approve`, `approve_with_conditions`, or `request_remediation`.
6. Generates a JSON audit report, reviewer-ready remediation plan, SARIF findings, privacy-safe tool receipts, and a DataHub write-back plan with an explicit execution gate.

The included synthetic scenario finds one critical and three high-severity issues and returns `request_remediation`.

## How we built it

LineageProof is a Python 3.12 package with a typed CLI and two interchangeable context providers:

- `FixtureToolSession` makes the public demo deterministic and credential-free.
- `StdioMcpToolSession` connects to the official DataHub MCP server through the MCP Python SDK.

Context collection and rule evaluation are separated. The agent records only the tool name, non-secret arguments, sequence number, and SHA-256 response hash in its receipt file. Raw responses are used in memory for the audit but are not copied into the receipts.

The generated mutation plan follows the official `add_tags` and `update_description` signatures. The audit remains dry-run-only. A separate executor requires the plan to exactly match the supplied report, preflights tool availability, allowlists mutation tools, caps the call count, and requires both `--apply` and an exact change-ID acknowledgement. The public proof executes five calls against a synthetic fixture and records `external_metadata_modified: false`; it does not claim a live write-back.

The submitted application was created during the hackathon submission period. It uses
open-source Python, MCP, testing, and packaging dependencies under their respective licenses; no
pre-existing proprietary project code or customer dataset is included. AI coding assistance was
used during development, and every submitted source file, fixture, claim, and generated artifact
was reviewed against executable tests and release evidence. The demo uses code-generated visuals
and a synthetic English voice.

## How it uses DataHub

DataHub is the core evidence layer, not a decorative integration. The audit decision depends on:

- dataset identity and ownership from `get_entities`;
- the current field contract from `list_schema_fields`;
- downstream field and asset impact from `get_lineage`; and
- observed SQL context from `get_dataset_queries`.

Each issue cites the exact receipt sequence numbers used as evidence. A stale schema baseline stops the analysis with a critical issue rather than producing a confident conclusion from mismatched metadata.

## Challenges

The hardest design problem was preserving useful evidence without turning the audit artifact into another copy of potentially sensitive production metadata. We solved this by separating in-memory context from persisted receipts and hashing canonical tool responses.

Another challenge was making a synthetic demo honest. The read fixture proves audit orchestration and rules. A separate mutation fixture proves the guarded write-back control flow and hash receipts while explicitly proving that no external metadata changed. Neither claims production connectivity or a live metadata update.

## Accomplishments

- A working CLI installable from a standalone wheel.
- Deterministic multi-tool orchestration using official DataHub MCP tool contracts.
- Explainable decisions with receipt-level evidence references.
- Five complementary outputs for reviewers, automation, and code scanning.
- A no-mutation default plus an audit-bound, tool-preflighted, explicitly acknowledged write-back executor.
- Fourteen automated tests, static checks, an isolated-wheel CLI test, and a release verifier.
- A release-tree privacy scan with zero credential or personal-data findings.
- An open RFC for capability discovery, idempotent expected-state mutations, privacy-safe before/after hashes, and read-back verification, plus a credential-free proposed receipt fixture.

## Sample outputs

The public repository includes a complete synthetic evaluation set under
`examples/expected-output/`: JSON audit and write-back preview, SARIF findings, a Markdown
remediation plan, hash-only tool receipts, a synthetic write-back receipt, and a clearly labeled
proposed auditable-mutation receipt. Judges can inspect
the outputs without a DataHub account, API key, or production dataset.

## What we learned

Lineage is most useful when it is evaluated together with the current schema and observed query behavior. We also learned that write access needs two truth boundaries: an executed MCP call is different from a verified external state change, and a synthetic mutation proof must never be reported as a production write-back. We captured the missing capability, concurrency, retry, and read-back contracts as a concrete RFC rather than weakening that boundary in the demo.

## What's next

- Add an HTTP MCP transport.
- Support versioned organization-specific policy packs.
- Attach SARIF findings to pull-request checks.
- Add post-mutation read-back verification for tags and column descriptions.
- Validate against a live DataHub test deployment and publish the connection receipt without exposing credentials or private metadata.

## Built with

Python, DataHub, DataHub MCP Server, MCP Python SDK, SARIF, uv, pytest, Ruff.

## Public links

- Source code: `https://github.com/heyhengl/lineageproof`
- Public preview: `https://heyhengl.github.io/lineageproof/`
- Rule-compliant video URL: pending public YouTube, Vimeo, or Youku upload
- Project/testing URL: `https://github.com/heyhengl/lineageproof`

The repository is the unrestricted testing surface: it contains Apache-2.0 source, complete setup
instructions, credential-free fixtures, expected outputs, and a deterministic local demo. No login,
paid service, or private test credential is required.

## Truth-boundary checklist before submission

- [x] Public repository exists and public-site commit `3bf07f23d7d9016ac2df093ef223f98ed98736ee` is recorded.
- [ ] Challenge category is `Agents That Do Real Work` in the live form.
- [x] Apache-2.0 license is visible in the public repository.
- [x] GitHub Pages preview opens in a signed-out browser and is under three minutes.
- [ ] The final video is public on YouTube, Vimeo, or Youku as required by the official rules.
- [x] Project/testing URL opens without login or payment and matches the public repository URL.
- [x] `examples/expected-output/` is present and readable in the public repository.
- [x] The submission states that the project was created during the submission period.
- [x] AI coding assistance, code-generated visuals, and synthetic narration are disclosed truthfully.
- [x] Every visual shown in the video exists in the public repository or generated demo output.
- [x] No claim says a live DataHub connection or verified external write-back occurred unless new evidence proves it.
- [ ] The Devpost preview contains no private identity, account, credential, or customer data.
- [ ] Final submit action is free and creates no financial movement.
