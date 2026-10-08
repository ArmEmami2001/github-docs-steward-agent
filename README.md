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
- Calls `connect`, then `log_event`;
- Treats an already-reached Noosphere quota as a successful no-op.


## Running the tests

The repository ships a small test file, test_agent.py, that exercises the agent without network access.

Install the requirements first, then run pytest from the repository root.

The tests cover three things.
They check that the prompts file parses.
They check that one observation is recorded per run.
They check that the hourly quota stops the agent cleanly.

Run them before opening a pull request.
