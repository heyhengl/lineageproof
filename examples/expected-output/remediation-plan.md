# LineageProof remediation plan

- Change: `scm_2026_07_18_0012`
- Dataset: `urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.warehouse.orders,PROD)`
- Decision: **request_remediation**
- Evidence tool calls: 8

## Required actions

### LP-001 · HIGH · `order_total`

Type change conflicts with observed usage

order_total changes from DECIMAL(12,2) to DECIMAL(14,2); 2 production query examples were inspected.

Action: Run contract tests against representative downstream queries and document the accepted type range.

Evidence receipts: 3, 4

### LP-002 · HIGH · `status`

Nullable field is used without a migration guard

status becomes nullable; 1 of 1 observed queries use it in a sensitive operation.

Action: Define null semantics, backfill existing rows, and update downstream queries with an explicit guard.

Evidence receipts: 5, 6

### LP-003 · CRITICAL · `shipping_address`

Field identity change reaches downstream assets

shipping_address changes to shipping_address_id while 6 downstream assets are recorded.

Action: Add a compatibility field or versioned migration, notify owners, and verify each contract before removal.

Evidence receipts: 7, 8

### LP-004 · HIGH · `shipping_address`

PII lineage reaches unclassified downstream assets

shipping_address is tagged PII, but 5 downstream assets lack the PII tag in the retrieved context.

Action: Confirm classification with asset owners and propagate the approved DataHub tag before deployment.

Evidence receipts: 7, 8

## Truth boundary

The DataHub write-back file is a dry-run preview. It is not proof of a mutation.
