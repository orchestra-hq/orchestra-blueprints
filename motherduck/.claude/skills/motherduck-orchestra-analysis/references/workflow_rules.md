# Durable workflow rules

## Append-only pipeline extension

- Preserve every existing task group; mart and optional Dive tasks run downstream.
- Do not delete, rename, or rewrite upstream groups (including ingest the user defined).
- New groups use `depends_on` pointing at the correct upstream group.
- Default to extending the pipeline the user named; create a new pipeline only when they explicitly ask or the target alias does not exist.

## Live introspection over repo SQL

- Derive marts from MotherDuck source data (schemas, columns, samples), not from reading `sql/*.sql` as a spec.
- After authoring, keep `sql/<alias>.sql` and `pipelines/<alias>.yaml` aligned with what is deployed.

## User-supplied pipeline

- No baked-in default alias, ID, or ingest definition in this workflow.
- Ingest lives in the pipeline the user passes; do not regenerate ingest YAML.

## Orchestra templating

- `${{ inputs.x }}` resolves only when it is the **entire** field value (e.g. `connection:`).
- Hardcode database and schema names inside SQL strings.

## Semicolon splitting

- Orchestra splits `MOTHERDUCK_EXECUTE_QUERY` on `;`.
- Multi-statement SQL is fine; TSX and JSON payloads must be base64-encoded.

## Deploy gotchas

- `update_pipeline` via MCP may send `storage_provider`; REST PUT rejects it (`extra_forbidden`).
- REST fallback: `PUT /api/engine/public/pipelines/{alias}` with `{"data": {...}, "published": true}` — no `storage_provider`, no alias in body.
- API key: `~/.claude/mcp.json` → `mcpServers.orchestra.env.ORCHESTRA_API_KEY`.
- No alias-assign endpoint: use `create_pipeline` with the alias if missing; orphan cleanup via Orchestra UI.
- Cold Python ingest workers: often 1–3 minutes before mart tasks; marts alone ~30s after upstream work.

## publish-dive ordering

When a pipeline already has `publish-dive`, new mart build groups must run before it, and `publish-dive.depends_on` must include the new group.
