# DataHub MCP contract

LineageProof follows the official [`acryldata/mcp-server-datahub`](https://github.com/acryldata/mcp-server-datahub) tool names and arguments documented by [DataHub](https://docs.datahub.com/docs/features/feature-guides/mcp/).

## Read sequence

### `get_entities`

```json
{
  "urns": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.warehouse.orders,PROD)"
}
```

Used for dataset identity and ownership.

### `list_schema_fields`

```json
{
  "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.warehouse.orders,PROD)",
  "limit": 100,
  "offset": 0
}
```

Used to prove that the change manifest is based on the current schema.

### `get_lineage`

```json
{
  "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.warehouse.orders,PROD)",
  "column": "order_total",
  "upstream": false,
  "max_hops": 3,
  "max_results": 100,
  "offset": 0
}
```

Used to inspect downstream field and asset impact.

### `get_dataset_queries`

```json
{
  "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.warehouse.orders,PROD)",
  "column": "order_total",
  "count": 10,
  "start": 0
}
```

Used to find observed SQL operations and exact type contracts.

## Mutation preview and executor

The generated plan uses the official signatures:

- `add_tags(tag_urns, entity_urns, column_paths?)`
- `update_description(entity_urn, operation, description, column_path?)`

The audit command does not call these tools. The separate write-back command requires an exact audit-bound plan, verifies that every required mutation tool is available, and requires both `--apply` and `--acknowledge 'APPLY <change_id>'`. The official MCP server also keeps mutation tools disabled unless its operator explicitly enables them.

The public proof uses `examples/datahub-mcp-writeback-fixture.json`; it exercises both mutation tool contracts but cannot alter external DataHub metadata. A live response receipt remains `external_metadata_modified: "unverified"` until a separate read-back is implemented.

## Proposed auditable extension

[`auditable-mutation-rfc.md`](auditable-mutation-rfc.md) proposes a capability receipt, expected-state check, idempotency key, common mutation outcomes, privacy-safe before/after hashes, and canonical read-back contract. It is a discussion proposal, not a claim about the current DataHub API. A credential-free example response is available at `examples/expected-output/proposed-auditable-mutation-receipt.json`.

## Credentials

The live stdio command inherits the operator's environment. LineageProof does not accept a token on the command line, print environment values, or save credentials in receipts or reports.
