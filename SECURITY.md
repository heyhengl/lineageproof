# Security policy

## Supported version

The current supported release is 0.1.x.

## Data handling

- The checked-in demo contains synthetic metadata only.
- Live DataHub credentials stay in the environment consumed by the official MCP server.
- LineageProof does not print, serialize, or persist environment variables or credentials.
- Tool-call receipts contain response hashes rather than raw metadata responses.
- Mutation tools are never invoked by version 0.1.0.

## Reporting a vulnerability

Do not include credentials, customer metadata, or private DataHub responses in a public issue. Provide a minimal synthetic reproduction and describe the affected version and expected security boundary.
