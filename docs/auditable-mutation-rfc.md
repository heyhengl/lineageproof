# RFC: auditable mutation contracts for DataHub MCP

Status: proposal for discussion. This document does not describe a currently implemented DataHub API.

## Motivation

An MCP mutation returning successfully proves that a tool call completed. It does not, by itself, prove that the intended catalog state is present, that the write was not duplicated after a retry, or that a concurrent edit was preserved.

Agents that modify governance metadata need a small, stable contract that makes those distinctions explicit. The contract should support a human-confirmed plan, conflict detection, safe retries, read-back verification, and privacy-safe audit receipts without copying sensitive metadata.

## Goals

- Discover mutation capabilities before planning a write.
- Bind a mutation to the state that a user reviewed.
- Make timeout retries deterministic and idempotent.
- Distinguish transport success from verified catalog state.
- Produce receipts that are useful without echoing credentials or full metadata.

## Non-goals

- Bypassing DataHub authorization, policy, or MCP confirmation controls.
- Treating a hash as proof that the underlying data is correct.
- Replacing normal DataHub audit logs or access controls.
- Claiming that the synthetic LineageProof fixture modified an external tenant.

## 1. Read-only capability receipt

A read-only `get_server_capabilities` tool could return a versioned response:

```json
{
  "contract_version": "1",
  "datahub_version": "<server supplied>",
  "mcp_server_version": "<server supplied>",
  "mutation_enabled": true,
  "available_mutation_tools": ["add_tags", "update_description"],
  "supports_expected_state": true,
  "supports_idempotency_keys": true,
  "supports_post_mutation_readback": true,
  "max_entities_per_call": 50
}
```

The client records a hash of this response with the plan. That proves which advertised capabilities informed the decision without inferring them from a stale document or deployment assumption.

## 2. Mutation request envelope

Existing tool arguments remain the operation payload. A common envelope adds concurrency and retry controls:

```json
{
  "idempotency_key": "client-generated opaque value",
  "expected_state": {
    "aspect_version": 41,
    "normalized_sha256": "<64 lowercase hex characters>"
  },
  "return_readback": true
}
```

The key is scoped to the authenticated principal, tool, and normalized target. Reuse with the same normalized request returns the original result. Reuse with different arguments returns `idempotency_conflict` and performs no write.

If the target no longer matches `expected_state`, the server returns `conflict` and performs no write. Clients must re-read, re-plan, and obtain fresh confirmation rather than silently overwriting newer metadata.

## 3. Standard mutation result

Every mutation tool returns a common versioned result with an operation-specific payload:

```json
{
  "contract_version": "1",
  "operation_id": "server-generated stable identifier",
  "status": "changed",
  "target": {
    "entity_urn": "urn:li:dataset:(...)"
  },
  "before": {
    "aspect_version": 41,
    "normalized_sha256": "<64 lowercase hex characters>"
  },
  "after": {
    "aspect_version": 42,
    "normalized_sha256": "<64 lowercase hex characters>"
  },
  "readback": {
    "verification": "match",
    "tool": "get_entities",
    "normalized_sha256": "<64 lowercase hex characters>"
  },
  "warnings": []
}
```

`status` is one of:

- `changed`: a write occurred and the returned state differs from the expected prior state;
- `already_satisfied`: the requested normalized state was present, so no write was needed;
- `conflict`: expected state did not match and no write occurred;
- `partial`: only a declared subset of a batch changed;
- `failed`: no requested write can be asserted;
- `idempotency_conflict`: the key was previously bound to different normalized arguments.

For `partial`, the result includes per-target outcomes. A top-level transport success must never collapse mixed outcomes into `changed`.

## 4. Canonical client flow

1. Call `get_server_capabilities` and retain its hash.
2. Read the target with an existing read-only tool.
3. Normalize only the fields relevant to the intended mutation and retain their version/hash.
4. Present the exact target, operation, bounded values, expected state, and warnings for human confirmation.
5. Call the mutation with an idempotency key and expected state.
6. Use the server-provided read-back or execute the recommended read-only call.
7. Compare normalized after/read-back hashes.
8. Persist only the capability hash, operation ID, target identifier, statuses, versions, hashes, and warnings unless full metadata retention was explicitly authorized.

LineageProof's current executor implements the plan, acknowledgement, and synthetic receipt portions of this flow. It deliberately leaves external state as unverified because the public fixture cannot prove a live tenant mutation.

## 5. Authentication and privacy

- Prefer OAuth/DCR for interactive clients and service accounts with Default Views for unattended workloads.
- Prefer authorization headers over tokens embedded in URLs.
- Mark query-string tokens as a compatibility path with an explicit warning that URLs can be retained in logs, shell history, screenshots, telemetry, and copied configuration.
- Never echo credentials in mutation results, read-backs, warnings, or operation lookup responses.
- Hash normalized mutation-relevant state, not an entire entity that may contain unrelated sensitive metadata.
- Make full before/after values opt-in and policy controlled.

## 6. Credential-free conformance fixture

An official synthetic profile should cover:

- `changed` and `already_satisfied`;
- permission denial;
- stale expected state;
- timeout followed by same-key retry;
- same-key/different-request conflict;
- partial batch success;
- read-back mismatch.

The fixture should be runnable without a production tenant and should label its result as synthetic. Passing it proves client contract handling, not external DataHub state.

## Acceptance criteria

- One capability response tells a client whether the planned mutation controls are supported.
- The same key and normalized request cannot duplicate appended content.
- The same key with different arguments cannot mutate state.
- A stale expected version/hash cannot silently overwrite newer metadata.
- Results distinguish all six statuses and enumerate partial outcomes.
- The documented read-back verifies the intended normalized state using a read-only tool.
- Receipts contain no credential and do not require full metadata values.
- The official fixture exercises success, conflict, retry, permission, partial, and mismatch paths.

## LineageProof evidence

- Current documented tool mapping: [`mcp-contract.md`](mcp-contract.md)
- Synthetic mutation fixture: [`../examples/datahub-mcp-writeback-fixture.json`](../examples/datahub-mcp-writeback-fixture.json)
- Current executor receipt: [`../examples/expected-output/synthetic-writeback-receipt.json`](../examples/expected-output/synthetic-writeback-receipt.json)
- Proposed result shape: [`../examples/expected-output/proposed-auditable-mutation-receipt.json`](../examples/expected-output/proposed-auditable-mutation-receipt.json)

