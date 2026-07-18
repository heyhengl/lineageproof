# LineageProof

LineageProof is an evidence-first schema-change audit agent for DataHub. It reads the affected dataset, schema, column-level lineage, and production query context through the official DataHub MCP tools, then produces a deterministic risk decision, remediation plan, SARIF report, and a safe-by-default DataHub write-back plan.

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

For small, fixed-scope technical work, MicroStudio publishes the acceptance
boundary and a synthetic proof before any project data is exchanged:

- [PDF to Excel audit](https://heyhengl.github.io/lineageproof/studio/pdf-to-excel-audit/) - typed workbook, source order, page reconciliation, formulas, and an issues register.
- [PDF layout block extraction](https://heyhengl.github.io/lineageproof/studio/pdf-layout-extraction/) - per-page blocks, article grouping, bbox and map-area coordinates, and a JSON contract.
- [Excel automation](https://heyhengl.github.io/lineageproof/studio/excel-automation/) - controlled inputs, formula-backed reporting, native charts, and a reusable handoff.

[Open a public project inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=project-inquiry.yml) only with synthetic or sanitized details. A public issue is not an order and does not authorize payment; scope, acceptance criteria, price, delivery terms, and any payment action remain separate.

## License

Apache-2.0. See `LICENSE`.
# LineageProof

LineageProof is an evidence-first schema-change audit agent for DataHub. It reads the affected dataset, schema, column-level lineage, and production query context through the official DataHub MCP tools, then produces a deterministic risk decision, remediation plan, SARIF report, and a safe-by-default DataHub write-back plan.

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
uv run --python 3.12 --no-project --with '.[dev]' lineageproof audit \
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
uv run --python 3.12 --no-project --with '.' lineageproof writeback \
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
uv run --python 3.12 --no-project --with '.[mcp]' lineageproof audit \
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
uv run --python 3.12 --no-project --with '.[dev]' pytest
uv run --python 3.12 --no-project --with '.[dev]' ruff check .
uv run --python 3.12 --no-project --with '.[dev]' python scripts/verify_release.py
```

## Build the public source archive

The release packager uses an explicit allowlist and produces a deterministic ZIP plus a
per-file SHA-256 manifest. Internal visual explorations under `design/`, local environments,
caches, and build outputs are excluded.

```bash
uv run --python 3.12 --no-project --with '.[dev]' python scripts/package_release.py
```

## Build the demo video

The macOS video pipeline renders a 1920x1080 synthetic storyboard, English narration, and
sentence-level SRT captions from verified CLI output. It enforces the submission's three-minute
ceiling and keeps account, customer, credential, and production DataHub data out of the recording.
See [`submission/VIDEO_BUILD.md`](submission/VIDEO_BUILD.md) for the reproducible commands and
visual boundary.

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

For small, fixed-scope technical work, MicroStudio publishes the acceptance
boundary and a synthetic proof before any project data is exchanged:

- [PDF to Excel audit](https://heyhengl.github.io/lineageproof/studio/pdf-to-excel-audit/) - typed workbook, source order, page reconciliation, formulas, and an issues register.
- [PDF layout block extraction](https://heyhengl.github.io/lineageproof/studio/pdf-layout-extraction/) - per-page blocks, article grouping, bbox and map-area coordinates, and a JSON contract.
- [Excel automation](https://heyhengl.github.io/lineageproof/studio/excel-automation/) - controlled inputs, formula-backed reporting, native charts, and a reusable handoff.

[Open a public project inquiry](https://github.com/heyhengl/lineageproof/issues/new?template=project-inquiry.yml) only with synthetic or sanitized details. A public issue is not an order and does not authorize payment; scope, acceptance criteria, price, delivery terms, and any payment action remain separate.

## License

Apache-2.0. See `LICENSE`.
