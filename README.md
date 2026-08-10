# LineageProof

LineageProof is an evidence-first schema-change audit agent for DataHub. It reads the affected dataset, schema, column-level lineage, and production query context through the official DataHub MCP tools, then produces a deterministic risk decision, remediation plan, SARIF report, and a safe-by-default DataHub write-back plan.

Looking for a small, fixed-scope data or automation deliverable? [MicroStudio evidence-led services](https://heyhengl.github.io/lineageproof/studio/) lists current opening scopes, public synthetic evidence, prices, and metadata-only inquiry forms. Buyers can review the [public Python source](https://github.com/heyhengl/lineageproof) before opening an inquiry. An inquiry or repository view is not an order or payment request.

Current deadline route: Google says Content API for Shopping sunsets on 18 August 2026. The [seven-control Merchant API migration plan](https://heyhengl.github.io/lineageproof/studio/notes/merchant-api-migration-controls/) includes a [two-page readiness checklist](https://heyhengl.github.io/lineageproof/studio/merchant-api-migration-readiness-checklist.pdf), a blank method inventory, a [five-call-site synthetic audit receipt](https://heyhengl.github.io/lineageproof/studio/merchant-api-synthetic-audit-receipt.csv) and a USD 249 fixed source-code dependency review for custom integrations. It does not require live Merchant Center access or credentials.

For the engineering walkthrough behind those controls, read [Seven Failure Modes Hidden in a Content API-to-Merchant API Migration](https://microstudio-evidence.hashnode.dev/migrating-content-api-source-code-inventory-before-august-18).

Run the credential-free static inventory before sharing any source archive. The easiest
path is the inspectable, dependency-free Python zipapp; it does not install a package:

```bash
python3 merchant-api-legacy-scan.pyz merchant-scan \
  --source /path/to/authorized-source \
  --out merchant-scan-output
```

[Download the deterministic zipapp](https://heyhengl.github.io/lineageproof/studio/merchant-api-legacy-scan.pyz)
or build it from the public source with
`python3 scripts/build_merchant_scan_zipapp.py --output dist/merchant-api-legacy-scan.pyz`.
Published SHA-256: `556affee3266bc605d8b4ffdbb07b3b18bc71f843be33bae38dd7c26cfeb1328`.
The repository development command remains:

```bash
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof lineageproof merchant-scan \
  --source /path/to/authorized-source \
  --out dist/merchant-scan
```

The scanner searches supported source files for legacy endpoints, client libraries,
Apps Script services, methods, `productstatuses` and `customBatch`. Its JSON and CSV
outputs contain relative paths, line numbers, contract labels and hashes only—never
source snippets, credentials, Merchant IDs or API responses. It performs no network
request and does not prove runtime coverage or a completed migration.

Inspect the public synthetic run: [JSON inventory](https://heyhengl.github.io/lineageproof/studio/merchant-api-legacy-scan-synthetic.json),
[CSV inventory](https://heyhengl.github.io/lineageproof/studio/merchant-api-legacy-scan-synthetic.csv),
and [fictional input files](examples/merchant-api-legacy-source/). The fixture represents
no customer, live catalog, account or completed cutover.

The fixture demo is fully synthetic and requires no credentials or external writes.

## Why it exists

Schema changes often look safe in isolation but break downstream contracts, dashboards, joins, or sensitive-data controls. LineageProof turns DataHub context into a review artifact that can be attached to a pull request before a migration ships.

## What the agent does

1. Calls `get_entities` and `list_schema_fields` for the proposed dataset.
2. Calls downstream `get_lineage` and `get_dataset_queries` for each changed field.
3. Verifies that the proposal baseline matches the current DataHub schema and that an accountable owner exists.
4. Applies explainable rules for renames, removals, type compatibility, nullability, query usage, ownership, and PII propagation.
5. Emits evidence hashes for every DataHub MCP response used in the decision.
6. Prepares compatible `add_tags` and `update_description` calls, then requires a separate command, tool preflight, `--apply`, and an exact change-ID acknowledgement before execution.

## Run the synthetic demo

```bash
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof --extra dev lineageproof audit \
  --change examples/schema-change.json \
  --fixture examples/datahub-mcp-fixture.json \
  --out dist/demo
```

Expected decision: `request_remediation`.

Generated files:

- `audit-report.json` — machine-readable issues, evidence, and decision
- `remediation-plan.md` — reviewer-ready action plan
- `lineageproof.sarif` — code-scanning compatible findings
- `datahub-writeback-preview.json` — mutation plan with `dry_run: true`
- `tool-call-receipts.json` — tool name, arguments, and response hash only

## Prove the write-back gate without external writes

The checked-in write-back fixture exercises the mutation path against synthetic responses. The
command requires both `--apply` and an acknowledgement bound to the audited change ID:

```bash
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof lineageproof writeback \
  --report dist/demo/audit-report.json \
  --plan dist/demo/datahub-writeback-preview.json \
  --fixture examples/datahub-mcp-writeback-fixture.json \
  --receipt dist/demo/synthetic-writeback-receipt.json \
  --apply \
  --acknowledge 'APPLY scm_2026_07_18_0012'
```

The receipt records five mutation-tool response hashes and explicitly states
`external_metadata_modified: false` because the provider is synthetic.

## Connect to the official DataHub MCP server

Install the optional MCP client extra and pass a stdio command. Keep DataHub credentials in the environment expected by the official server; LineageProof never prints or persists them.

```bash
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof --extra mcp lineageproof audit \
  --change examples/schema-change.json \
  --mcp-command "uvx mcp-server-datahub" \
  --out dist/live
```

The official server keeps mutation tools disabled unless `TOOLS_IS_MUTATION_ENABLED=true`. A live
write-back is a separate, operator-controlled action. Running `lineageproof writeback` without
`--apply` performs plan and tool-availability preflight only. With `--apply`, the command also
requires `--acknowledge 'APPLY <change_id>'`; it never accepts or stores a credential argument.

## Test and verify

```bash
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof --extra dev pytest
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof --extra dev ruff check .
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof --extra dev python scripts/verify_release.py
```

The explicit refresh is intentional: it prevents an older local `0.1.0` build from being reused
when the source tree has changed without a version bump.

## Build the public source archive

The release packager uses an explicit allowlist and produces a deterministic ZIP plus a
per-file SHA-256 manifest. Internal visual explorations under `design/`, local environments,
caches, and build outputs are excluded.

```bash
uv run --python 3.12 --isolated --no-editable \
  --refresh-package lineageproof --extra dev python scripts/package_release.py
```

## Build the demo video

The macOS video pipeline renders a 1920x1080 synthetic storyboard, English narration, and
sentence-level SRT captions from verified CLI output. It enforces the submission's three-minute
ceiling and keeps account, customer, credential, and production DataHub data out of the recording.
See [`submission/VIDEO_BUILD.md`](submission/VIDEO_BUILD.md) for the reproducible commands and
visual boundary.

The GitHub Pages player is a public preview, not the final hackathon video host. The official
rules require the submitted video URL to be publicly visible on YouTube, Vimeo, or Youku; that
separate upload must be verified before submission.

The verified assets, paste-ready public metadata, chapters, captions, disclosure fields, and
financial stop conditions for YouTube are in
[`submission/YOUTUBE_PUBLICATION_PACKET.md`](submission/YOUTUBE_PUBLICATION_PACKET.md). The
equivalent localized Youku checklist is in
[`submission/YOUKU_PUBLICATION_PACKET_zh.md`](submission/YOUKU_PUBLICATION_PACKET_zh.md).

See [`docs/architecture.md`](docs/architecture.md) for the decision flow, [`docs/mcp-contract.md`](docs/mcp-contract.md) for the official DataHub MCP calls used by the agent, and [`docs/auditable-mutation-rfc.md`](docs/auditable-mutation-rfc.md) for a clearly labeled proposal covering idempotent, expected-state-bound, read-back-verifiable mutations.

## Safety and truth boundaries

- Demo inputs contain only synthetic metadata.
- Tool receipts store hashes, not raw DataHub responses.
- No credentials, environment variables, or user profile data are logged.
- `datahub-writeback-preview.json` is not proof that metadata was written.
- `synthetic-writeback-receipt.json` proves mutation orchestration only; it explicitly proves that no external metadata was modified.
- A live success receipt proves that the MCP server returned mutation responses, not that a separate read-back verified the final target state.
- A fixture run proves deterministic orchestration and rules, not connectivity to a production DataHub instance.
- Live use requires the operator to have lawful access to the target DataHub deployment and its metadata.

## MicroStudio evidence-led services

MicroStudio publishes the acceptance boundary and owned synthetic evidence before
any project data is exchanged. These opening samples cover small, fixed-scope,
private-sector work outside regulated or high-risk uses.

**Currently available: weekly property watchlist merge — USD 79.** Merge one
prior and one current authorized CSV or XLSX export, up to 1,000 current rows,
using one stable listing key. The fixed scope includes a merged workbook,
carried visit notes, a missing or duplicate ID review queue, a change log,
refresh instructions, and one correction round.

[Inspect the synthetic proof](https://heyhengl.github.io/lineageproof/studio/weekly-property-watchlist-merge/)
or [open the metadata-only inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=weekly-property-watchlist-merge.yml).
Do not post real files, addresses, staff notes, contact details, credentials,
private links, or payment information in a public issue.

| Service | Opening sample | Public evidence | Metadata-only inquiry |
| --- | --- | --- | --- |
| [Cloud pricing change audit](https://heyhengl.github.io/lineageproof/studio/cloud-pricing-change-audit/) | USD 349 for one provider, two authorized JSON snapshots, up to 100 unique price keys and one review round | [Synthetic change-audit proof](https://heyhengl.github.io/lineageproof/studio/portfolio/Synthetic_Cloud_Pricing_Change_Audit_Proof.zip) | [Cloud-pricing inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=cloud-pricing-change-audit-intake.yml) |
| [Replay-safe webhook audit and repair](https://heyhengl.github.io/lineageproof/studio/replay-safe-webhook-audit/) | From USD 349 for one nonregulated event family and one review round | [Synthetic reliability proof](https://heyhengl.github.io/lineageproof/studio/portfolio/Synthetic_Webhook_Reliability_Proof.zip) | [Webhook inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=replay-safe-webhook-intake.yml) |
| [n8n workflow reliability review and repair](https://heyhengl.github.io/lineageproof/studio/n8n-workflow-reliability-review/) | From USD 249 for one inactive workflow, one trigger, up to 25 nodes and one review round | [Synthetic MCP-to-email workflow proof](https://heyhengl.github.io/lineageproof/studio/portfolio/N8N_MCP_Video_Analysis_Email_Synthetic_Proof.zip) | [n8n inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=n8n-workflow-reliability-intake.yml) |
| [Content API to Merchant API source-code dependency review](https://heyhengl.github.io/lineageproof/studio/notes/merchant-api-migration-controls/) | USD 249 for one authorized source snapshot, up to 25 legacy call sites, three jobs, three sub-APIs and one review round | [Local scanner zipapp](https://heyhengl.github.io/lineageproof/studio/merchant-api-legacy-scan.pyz), [two-page readiness checklist](https://heyhengl.github.io/lineageproof/studio/merchant-api-migration-readiness-checklist.pdf) and [synthetic audit receipt](https://heyhengl.github.io/lineageproof/studio/merchant-api-synthetic-audit-receipt.csv) | [Check fit without sharing code](https://github.com/heyhengl/lineageproof/issues/new?template=merchant-api-migration-intake.yml) |
| [Supplier catalog QA and Shopify import prep](https://heyhengl.github.io/lineageproof/studio/catalog-qa-offline-agency-kit/) | USD 249 for one authorized CSV or simple XLSX, up to 200 SKUs and one revision | [Seven-file synthetic sample](https://heyhengl.github.io/lineageproof/studio/catalog-qa-offline-agency-kit/sample/) | [Catalog QA inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=catalog-qa-intake.yml) |
| [Business spreadsheet cleanup and reconciliation](https://heyhengl.github.io/lineageproof/studio/sales-data-cleaning/) | USD 149 for one sanitized CSV or XLSX, up to 10,000 rows, one schema and one correction round | [Synthetic analysis proof](https://heyhengl.github.io/lineageproof/studio/portfolio/Sales_Insight_Audit_Proof.zip) | [Spreadsheet-cleanup inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=sales-data-cleaning-intake.yml) |
| [Weekly property watchlist merge](https://heyhengl.github.io/lineageproof/studio/weekly-property-watchlist-merge/) | USD 79 for one prior and one current authorized CSV/XLSX export, up to 1,000 current rows and one correction round | [Stable-key merge note](https://heyhengl.github.io/lineageproof/studio/notes/weekly-property-stable-key-merge/) and [synthetic workbook](https://heyhengl.github.io/lineageproof/studio/portfolio/Weekly_Property_Watchlist_Merge_Synthetic_Proof.xlsx) | [Weekly-watchlist inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=weekly-property-watchlist-merge.yml) |
| [MT5 indicator and dashboard engineering](https://heyhengl.github.io/lineageproof/studio/mt5-indicator-dashboard-audit/) | From USD 50 for one indicator, dashboard, risk-control module, bounded EA slice or source audit, with one revision | [Compile-evidence note](https://heyhengl.github.io/lineageproof/studio/notes/mql5-compile-evidence/) | [MT5 inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=mt5-build-intake.yml) |

Other evidence-led routes include [PDF to Excel audit](https://heyhengl.github.io/lineageproof/studio/pdf-to-excel-audit/), [PDF layout block extraction](https://heyhengl.github.io/lineageproof/studio/pdf-layout-extraction/), [Excel automation](https://heyhengl.github.io/lineageproof/studio/excel-automation/), [intake automation readiness audit](https://heyhengl.github.io/lineageproof/studio/intake-automation-readiness-audit/), and [release readiness QA audit](https://heyhengl.github.io/lineageproof/studio/release-readiness-qa-audit/). For another bounded route, [open a public project inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=project-inquiry.yml).

Use public issues for metadata only: do not attach files or include customer or personal data, credentials, private URLs, payment data, or production secrets. Health, finance, payments, crypto, government, security, identity, surveillance, and other regulated or high-risk work are out of scope. An inquiry is not an order, revenue, or payment authorization; written scope, acceptance criteria, price, delivery terms, and any payment action remain separate. MT5 work does not include live-account operation or performance promises.

## License

Apache-2.0. See `LICENSE`.
