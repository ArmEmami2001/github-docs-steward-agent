# GitHub Documentation Steward for Noosphere

A public GitHub Actions agent that performs one real documentation-health observation per run and records the result through Noosphere MCP. It runs once per hour from 00:43 through 14:43 UTC, producing at most 15 truthful events per UTC day.

## Connect it

1. Create a separate unbound connect code in Noosphere. Do not reuse the CI Sentinel code.
2. In this GitHub repository, open **Settings > Secrets and variables > Actions**.
3. Create a repository secret named `NOOSPHERE_CREDENTIAL` containing the complete `nsc_...` code.
4. Run **Actions > Noosphere Documentation Steward > Run workflow** once.

The first authenticated MCP call claims the connect code. The same encrypted secret remains the permanent credential.

## Behavior

- Uses read-only GitHub permissions.
- Inspects documentation files, guidance files, README presence, releases, issues, topics, and licensing metadata.
- Uses its own set of 15 documentation prompts, distinct from CI Sentinel.
- Calls `connect`, then `log_event`; it never supplies its own score or reputation category.
- Treats an already-reached Noosphere quota as a successful no-op.

Do not put the Noosphere credential in source code, workflow YAML, logs, or local `.env` files.

