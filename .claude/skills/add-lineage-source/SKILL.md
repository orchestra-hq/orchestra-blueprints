---
name: add-lineage-source
description: Add a new platform (e.g. Snowflake, Databricks, dbt Cloud, HubSpot, Salesforce) as a source for the platform-lineage pipeline in python/lineage/, so its assets and edges get published into Orchestra's lineage graph. Use this whenever the user wants to "add a new source to the lineage pipeline", "wire up <platform> for lineage", "extend the lineage graph to include <platform>", "add another platform to queries.py", or asks to get a platform showing up in Orchestra's lineage graph -- even if they don't name python/lineage, queries.py, or dlt explicitly.
---

# Add a platform to the lineage pipeline

`python/lineage/` extracts metadata from every platform with dlt, lands it in
BigQuery's `platform_lineage_raw` dataset, and `publish_lineage.py` reads it
back out with the SQL in `queries.py` and publishes it to Orchestra via
`POST /assets` / `POST /assets/dependencies`. Adding a platform is entirely
additive — nothing else in the pipeline changes shape — and touches five
files: a new source module, `config.py`, `load_source.py`, the pipeline YAML,
and `queries.py` (a sixth, `requirements.txt`, if the platform needs a
package not already pulled in — see step 2).

Read `python/lineage/README.md` first (particularly "External ID conventions"
and "Adding another platform") — it documents the same conventions this skill
walks through, and stays the source of truth if the two ever drift.

## Steps

### 1. Write the dlt source module

Create `python/lineage/sources/<platform>.py`. Model it on whichever existing
source is the closer shape:

- **`sources/fivetran.py`** — a paginated REST API called with `requests` and
  a bearer/basic token. Good template for anything with an HTTP API and a
  credential pair.
- **`sources/bigquery.py`** — a client library queried directly (no REST
  calls). Good template for a platform with its own Python SDK.
- **`sources/lightdash.py`** — REST API plus a per-item detail fetch that can
  legitimately 404 for one object without failing the whole load.

Whichever you start from, keep these conventions — they are load-bearing, not
style:

- Decorate the source function `@dlt.source(name="<platform>")` and return a
  tuple of `@dlt.resource(name="<platform>_<noun>", write_disposition="replace")`
  functions. Every resource fully replaces its raw table each run; nothing
  here increments.
- Pull credentials with `config.require_env("SOME_API_KEY", ...)`. It raises
  `MissingCredentials` naming every missing variable, so a half-configured
  platform fails loudly with the exact fix instead of silently publishing a
  partial (or empty) graph.
- When fetching one object's own detail record (a single table, chart, or
  connector), skip just that item on a "this one object isn't available"
  error rather than failing the whole load — but let anything that means the
  credential itself is broken propagate, so a bad credential never looks like
  an empty-but-successful run. For a REST source, that means wrapping the
  call and checking `config.is_skippable(exc)`, which is true for a 403/404
  on `exc.response` (a `requests.HTTPError` shape) — see `sources/fivetran.py`
  and `sources/lightdash.py`. `is_skippable()` only understands that shape,
  so for an SDK-based source (a client library raising its own exception
  type, e.g. `snowflake.connector.errors.ProgrammingError`) follow
  `sources/bigquery.py`'s pattern instead: catch that SDK's specific
  exception (or, where the SDK doesn't give you a narrower one, a broad
  `except Exception` scoped to a single resource — see `job_edges()`), print
  what was skipped and why, and yield nothing/continue rather than raising.
- Yield plain dicts. dlt's naming convention normalizes keys on load
  regardless of what you use (e.g. an API's `projectUuid` becomes the column
  `project_uuid`), so match the API's own field names in the dict and let dlt
  do the rest.

### 2. Wire the source into the extract task

Small, mechanical edits:

- `python/lineage/config.py` — add `"<platform>"` to `KNOWN_SOURCES`. It's
  only used for the `load_source.py` usage/error message, but keep it in sync.
- `python/lineage/load_source.py` — add a branch to `build_source()`:
  ```python
  if name == "<platform>":
      from sources.<platform> import <platform>_source
      return <platform>_source()
  ```
  Keep the `import` inside the branch, not at module top-level — that's what
  lets one platform's optional dependency (or a bad extra) fail only its own
  extract instead of breaking the other two at import time.
- If the source module needs a package that isn't already a dependency of
  something else here (dlt, `requests`, and `google-cloud-bigquery` are
  already pulled in; a vendor SDK like `snowflake-connector-python` is not),
  add it to `python/lineage/requirements.txt`. The pipeline YAML runs one
  shared `pip install -r requirements.txt` for every matrix child, so
  skipping this doesn't show up in `py_compile` or any local syntax check —
  it only surfaces as a runtime `ModuleNotFoundError` when the extract task
  actually runs.

### 3. Add the platform to the pipeline's matrix

In `orchestra/platform_lineage_dlt_bigquery_lightdash_fivetran.yml`, add
`"<platform>"` to the `sources` input's `default` list (search for `sources:`
under `inputs:`). The extract task group's `matrix.inputs.source` already
reads `${{ inputs.sources }}`, so this is the only orchestration change — the
new platform becomes another parallel MetaEngine child automatically, no new
task group needed.

This is a live, already-deployed pipeline. Keep the edit to that one list —
don't touch task/group/connection IDs.

### 4. Add the platform to `queries.py`

This is the step most likely to be gotten wrong, because getting the
`external_id` convention wrong doesn't error — it silently creates a second,
disconnected lineage graph next to Orchestra's own collected one instead of
merging with it.

**Before writing SQL, find out what `externalId` Orchestra's own collector
already uses for this integration.** If the platform already has assets in
Orchestra (most do, if it's wired in as an integration at all), query one
with `list_assets` (filtered to that integration) and read its `externalId`.
Match that format exactly. If you can't find an existing convention, ask
rather than guess — a wrong format is a silent failure mode, not a loud one.

Then add one entry to `ASSET_QUERIES` in `python/lineage/queries.py`:

```python
"<platform>_<noun>": (
    {"<platform>_<noun>"},  # required_raw_tables: the dlt resource name(s) this reads
    r"""
    select
      <external id expression, matching Orchestra's own convention> as external_id,
      '<INTEGRATION_NAME>' as integration,
      <...> as integration_account_id,
      <...> as asset_name,
      '<ASSET_TYPE>' as asset_type,
      cast(null as string) as database_name,
      cast(null as string) as schema_name,
      cast(null as string) as table_name,
      cast(null as string) as workspace_name,
      <...> as description,
      cast(null as string) as url,
      cast(null as timestamp) as created_in_integration
    from `$project`.`$raw_dataset`.<platform>_<noun>
    where <...>
    """,
),
```

A few things the shape above depends on:

- The `select` list must produce exactly these columns (see the module
  docstring in `queries.py` for the current authoritative list):
  `external_id`, `integration`, `integration_account_id`, `asset_name`,
  `asset_type`, `database_name`, `schema_name`, `table_name`,
  `workspace_name`, `description`, `url`, `created_in_integration`.
  `cast(null as ...)` the ones that don't apply — `publish_lineage.py`'s
  `fetch_assets()` only drops a row when `external_id`, `asset_name`, or
  `integration_account_id` is null, everything else is optional.
- `required_raw_tables` is the set of raw table names in
  `platform_lineage_raw` this query reads (i.e. the `@dlt.resource` names
  from step 1). `_fetch_rows()` in `publish_lineage.py` skips *just this
  query* — not the whole build — when any of them hasn't landed yet, since
  platforms come online at different times (credentials not provisioned yet,
  or a run that only extracted a subset via the pipeline's `sources` input).
- The SQL is a `string.Template` body: only `$project` and `$raw_dataset` are
  always-available placeholders. Don't invent new ones — `$table_col` is a
  one-off reserved for Fivetran's optional `table` column (see the existing
  `fivetran_connectors` entry for why: dlt only creates a column when it's
  present in at least one extracted record, so a field that's null/absent for
  every row across an account may not exist as a column at all).

If the new platform has lineage edges into or out of a platform already in
the graph (its assets are fed by, or feed, a BigQuery table, a Lightdash
chart, etc.), add a matching entry to `EDGE_QUERIES` in the same file,
producing `from_external_id`, `to_external_id`, `integration`,
`lineage_detail` — same `required_raw_tables` convention. You don't need to
worry about dangling edges: `fetch_edges()` drops any edge whose `from`/`to`
external ID isn't in the set of assets actually published, so an edge
pointing at an asset you forgot to add (or got the `external_id` wrong for)
is silently dropped rather than failing the whole publish batch.

## Verifying before you're done

There's usually no BigQuery connection available to actually run these
queries locally, so lean on what you *can* check:

1. `python3 -m py_compile python/lineage/queries.py python/lineage/publish_lineage.py python/lineage/config.py python/lineage/load_source.py python/lineage/sources/*.py`
   from the repo root — catches syntax errors.
2. Render every query's `Template` with placeholder values and print the
   result, to eyeball the generated SQL for the new entries specifically:
   ```python
   from string import Template
   from queries import ASSET_QUERIES, EDGE_QUERIES
   for name, (required, sql) in {**ASSET_QUERIES, **EDGE_QUERIES}.items():
       print("---", name, sorted(required))
       print(Template(sql).safe_substitute(
           project="proj", raw_dataset="platform_lineage_raw",
           table_col="cast(null as string)",
       ))
   ```
3. If Orchestra credentials and a live pipeline branch are available, the
   real test is triggering
   `orchestra/platform_lineage_dlt_bigquery_lightdash_fivetran.yml` on a
   feature branch with `sources: ["<platform>"]` alone first, so a bug in the
   new platform's queries doesn't get lost in three platforms' worth of
   output — then with the full default list once that's clean. Orchestra
   pins a run to the last commit that touched the pipeline YAML, so pass
   `commit` explicitly to `start_pipeline` when iterating on Python-only
   changes.

After a real run, sanity-check the published result: pull a handful of the
new platform's assets with `list_assets` (filtered to its integration) and
confirm they got `meta.source: "orchestra-blueprints/platform-lineage"` set
and, critically, that their `externalId` matches ones Orchestra's own
collector would already be using — if the count of *created* assets for that
integration is suspiciously high (it should mostly be *updated*, merging
into what Orchestra already collected), the `external_id` convention is
probably wrong.
