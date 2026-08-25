# Platform lineage: dlt -> BigQuery -> Orchestra

Builds an end-to-end lineage graph in Orchestra by extracting metadata from every
platform in the stack, landing it in BigQuery, and publishing it through
Orchestra's metadata API.

```
Fivetran API  ─┐
BigQuery API  ─┼─ dlt (MetaEngine, one child per source) ─→ BigQuery platform_lineage_raw
Lightdash API ─┘                                                      │
                                                                      ▼
                                        publish_lineage.py (queries.py shapes
                                        the raw tables into asset/edge rows,
                                        straight from BigQuery -- no dbt build)
                                                      │
                                    POST /assets  +  POST /assets/dependencies
                                                      │
                                                      ▼
                                         Orchestra Data assets → Lineage
```

The Orchestra pipeline that runs all of this is
[`orchestra/platform_lineage_dlt_bigquery_lightdash_fivetran.yml`](../../orchestra/platform_lineage_dlt_bigquery_lightdash_fivetran.yml).

## Why publish through the API

Orchestra collects lineage automatically from integrations that expose
dependency information, but the graph has holes wherever a tool does not
(`dlt` loads, or a platform Orchestra has no metadata collector for). Orchestra's
lineage is not editable in the UI, so the supported way to fill those holes is
`POST /assets` plus `POST /assets/dependencies` — which is exactly what
`publish_lineage.py` does.

## External ID conventions

The publisher deliberately reuses the `externalId` format Orchestra already uses
per integration, so published assets **merge with** the ones Orchestra collected
itself instead of creating duplicates:

| Integration | `externalId` |
| --- | --- |
| `GCP_BIG_QUERY` | `<project>.<dataset>.<table>` |
| `LIGHTDASH` | `<project_uuid>.<chart_or_dashboard_uuid>` |
| `FIVETRAN` | `fivetran.<group_id>.<connector_id>` |

Get this wrong and you get a parallel, disconnected graph. Check an existing
asset with `list_assets` before adding a platform.

## Verifying a published run is correct

Getting an `externalId` wrong doesn't error — it silently creates a second,
disconnected graph next to Orchestra's own instead of merging with it. The
asset/edge counts a run prints are not enough to trust on their own; after a
real run, check a few real assets:

1. **Confirm assets merged instead of duplicating.** Pick an asset that
   should already exist in Orchestra (a real BigQuery table, a real Fivetran
   connector) and `get_asset_by_id` it by its `externalId`. If `createdAt`
   predates this pipeline's first run, that asset already existed in
   Orchestra — this publish only PATCHed it. Look for native fields the
   publisher never sends (a `connection` field, a live `status` like
   `HEALTHY`/`UNHEALTHY`, a rich pre-existing `downstreamDependencies`
   array) still present after the PATCH; if they've been wiped out, the
   publish overwrote instead of merging.
2. **Check for accidental duplicates.** `list_assets` filtered to one
   `database_name`/`schema_name` (or one Fivetran `integration_account_id`)
   and count the rows against what you know should be there. A second row
   for a table you expect once means the `external_id` convention doesn't
   match what Orchestra's own collector produces for that platform.
3. **Verify edges bidirectionally on a real chain.** Pick one you know the
   real data flow for (e.g. a Fivetran connector syncing into a table that
   feeds a dbt view) and follow it hop by hop: each asset's
   `upstreamDependencies`/`downstreamDependencies` should agree with its
   neighbour's on the other end.
4. **A brand-new asset (`createdAt == updatedAt`, both from this run) is not
   automatically wrong.** Orchestra has no native collector for some things
   this pipeline covers (Lightdash dashboards, a BigQuery view its own
   scanner hadn't synced yet) — that's the gap this pipeline exists to fill
   (see *Why publish through the API* above), not evidence of a duplicate.
   Only worry when something that *should* already exist in Orchestra shows
   up freshly created.

Worked example from this pipeline's own demo-account run: the Fivetran
connector `fivetran.impossibility_incorporating.appetite_trimness` (created
2026-07-24, weeks before this pipeline existed) merged cleanly with the
BigQuery table `reference-baton-392114.gsheets_leads.dbt_community` (created
2026-07-22) via the sync edge the pipeline computes — both sides' native
`connection`/`status` fields survived the PATCH untouched, and following the
chain one hop further (into a dbt-built view downstream) still agreed on
both ends. The Lightdash charts and dashboards published in the same run,
by contrast, were genuinely new — Orchestra had no prior record of them at
all, which is expected, not a bug.

## Running locally

```bash
cd python/lineage
pip install -r requirements.txt

# One source at a time -- this is what each MetaEngine child does.
LINEAGE_SOURCE=lightdash python -m load_source
LINEAGE_SOURCE=bigquery  python -m load_source
LINEAGE_SOURCE=fivetran  python -m load_source

# Then, straight off the raw tables above -- no build step in between:
python -m publish_lineage --dry-run   # prints every asset and edge, sends nothing
python -m publish_lineage
```

## Environment variables

Credentials come from the Orchestra connection's secret JSON; the rest are set by
the pipeline's `environment_variables`. Nothing is read from `secrets.toml`.

| Variable | Used by | Purpose |
| --- | --- | --- |
| `TAP_LIGHTDASH_URL` | lightdash | Lightdash host, e.g. `https://app.lightdash.cloud` |
| `TAP_LIGHTDASH_PERSONAL_ACCESS_TOKEN` | lightdash | Lightdash PAT |
| `FIVETRAN_API_KEY` / `FIVETRAN_API_SECRET` | fivetran | Fivetran API credentials (Basic auth) |
| `BIGQUERY_CREDENTIALS_JSON` | all | Service account JSON as a string; bridged to `GOOGLE_APPLICATION_CREDENTIALS` and dlt's destination vars by `config.ensure_google_credentials()` |
| `GOOGLE_APPLICATION_CREDENTIALS` | all | Alternative to the above: path to a key file |
| `ORCHESTRA_API_KEY` | publish | Injected automatically by Orchestra Python tasks |
| `BIGQUERY_PROJECT` | all | GCP project holding both datasets. Falls back to `LINEAGE_BQ_PROJECT`, then to the `project_id` in the service account JSON, if unset |
| `BIGQUERY_LOCATION` | all | BigQuery region, default `europe-west1` |
| `LINEAGE_RAW_DATASET` | extract, publish | dlt landing dataset; publish reads straight out of it, default `platform_lineage_raw` |
| `LINEAGE_BQ_LOOKBACK_DAYS` | bigquery | Days of BigQuery job history to read for table-to-table edges, default `7` |
| `LIGHTDASH_PROJECT_UUIDS` | lightdash | Optional comma-separated allowlist of Lightdash projects |

The Lightdash and Fivetran extracts fail loudly with the exact list of missing
variable names rather than loading a partial graph.

### BigQuery job history is optional

`bigquery_job_edges` reads `INFORMATION_SCHEMA.JOBS_BY_PROJECT`, which needs
`bigquery.jobs.listAll`. When the credential lacks it the resource logs the denial
and yields nothing — the load still succeeds, and warehouse table-to-table edges
come from `bigquery_view_refs` instead, which only needs INFORMATION_SCHEMA read
access. See *BigQuery job-history IAM* below.

## Orchestra setup

Two things live outside this repo. The pipeline reports each one clearly rather
than half-working, so you can tell at a glance which is missing.

### 1. Fivetran credentials

`FIVETRAN_API_KEY` and `FIVETRAN_API_SECRET` live in the secret JSON of the Python
connection the extract runs under (`blueprints__meltano__51199`, which also holds
the Lightdash PAT and the BigQuery service account). If they are ever removed, the
Fivetran child fails naming the exact missing variables rather than loading a
partial graph; trigger with `sources: ["lightdash", "bigquery"]` to skip that leg
deliberately.

### 2. BigQuery job-history IAM

The extract's service account
(`dlt-user@reference-baton-392114.iam.gserviceaccount.com`) needs
`bigquery.jobs.listAll` (`roles/bigquery.resourceViewer` at project level) for
`bigquery_job_edges` to read `INFORMATION_SCHEMA.JOBS_BY_PROJECT`. Without it the
resource logs the denial and yields nothing -- the load still succeeds, and
warehouse edges fall back to `bigquery_view_refs`, which covers views but not
plain tables.

### Testing on a branch

Orchestra pins a run to the last commit that touched the **pipeline YAML**, so a
commit that only changes Python files is not picked up. Pass the commit
explicitly when iterating:

```
start_pipeline(branch="<feature-branch>", commit="<sha>",
               runInputs={"branch": "<feature-branch>", "sources": [...]})
```

## Scale

The `bigquery_tables` query in `queries.py` filters out dlt/BigQuery
bookkeeping, dbt's temp/backup tables, and (notably) GA4's BigQuery Export --
a table *per day*, which alone was 20k+ rows on the account this was built
against. Without that filter the publisher's single-row
`POST /assets` calls (there is no bulk-upsert endpoint) blow through
Orchestra's 50-requests/minute limit by orders of magnitude. If a warehouse has
another high-cardinality sharded pattern, add it to that filter rather than
letting it reach the publisher.

The publisher paces its own writes to stay under the limit (`_PACING_SECONDS`
in `publish_lineage.py`) and retries 429/5xx with backoff as a safety net, not
the primary plan -- a workspace with a few hundred assets still takes minutes
by design, and progress prints every 25 assets so a long run isn't silent.

The Lightdash extract only pulls `DEFAULT`-type projects; `PREVIEW` projects
(ephemeral CI/PR environments) are skipped unless `LIGHTDASH_PROJECT_UUIDS`
names them explicitly, since they multiplied dashboard/chart calls, produced
assets for environments that expire in days, and caused the API 422
`workspace_name is required when asset_type indicates a dashboard` (their
name and thus `workspace_name` isn't reliably set the way a `DEFAULT`
project's is).

## Adding another platform

Three localised edits, no changes to the publisher's HTTP logic or the API
contract. Walking through adding a hypothetical `snowflake` platform:

1. **Source module** — add `sources/snowflake.py` exposing a `snowflake_source()`
   function decorated `@dlt.source(name="snowflake")` that returns a tuple of
   `@dlt.resource(...)` functions, each named `snowflake_*` (e.g.
   `snowflake_tables`) with `write_disposition="replace"` — every existing
   resource fully replaces its raw table on each run rather than incrementing.
   Model it on `sources/bigquery.py` (metadata pulled straight from the
   platform with a client library) or `sources/fivetran.py` /
   `sources/lightdash.py` (a paginated REST API), and follow the same two
   conventions those use:
   - Pull credentials with `config.require_env(...)`, which raises
     `MissingCredentials` naming every missing variable — the whole load
     fails loudly rather than silently publishing a partial graph.
   - When fetching per-item detail (one table's/connector's/chart's own
     record) wrap the call in `try/except` and skip that item when
     `config.is_skippable(exc)` is true (a 403/404 on one object) — but let
     auth failures and 5xxs propagate so a broken credential doesn't silently
     publish an empty graph.

   Then wire it in:
   - Add a branch to `build_source()` in `load_source.py`:
     `if name == "snowflake": from sources.snowflake import
     snowflake_source; return snowflake_source()`. Keep the import inside the
     branch — that's what lets a missing optional dependency for one platform
     leave the others working.
   - Add `"snowflake"` to `KNOWN_SOURCES` in `config.py` (used for the
     usage/error messages `load_source.py` prints; keep it in sync).
2. **Pipeline input** — add `"snowflake"` to the `sources` input's `default`
   list (`inputs.sources.default`) in
   `orchestra/platform_lineage_dlt_bigquery_lightdash_fivetran.yml`. The
   extract task group's `matrix.inputs.source` already reads
   `${{ inputs.sources }}`, so that's the only orchestration change needed —
   the new platform becomes another parallel extract child automatically.
3. **Queries** — add one entry to `ASSET_QUERIES` in `queries.py`, keyed by a
   name of your choice (e.g. `"snowflake_tables"`), as a
   `(required_raw_tables, sql)` tuple:
   - `required_raw_tables` is the set of raw table names the query reads, as
     they land in `platform_lineage_raw` (i.e. the `@dlt.resource` names from
     step 1). `publish_lineage.py`'s `_fetch_rows()` skips just that query —
     not the whole build — when any of them hasn't landed yet, since
     platforms come online at different times (credentials not provisioned
     yet, or a run that only extracted a subset via the pipeline's `sources`
     input).
   - `sql` is a `string.Template` body; it can reference `$project` and
     `$raw_dataset` (always substituted). Don't invent new placeholders —
     `$table_col` is a one-off already reserved for Fivetran's optional
     `table` column.
   - The `select` list must return exactly these columns (see the module
     docstring in `queries.py`): `external_id`, `integration`,
     `integration_account_id`, `asset_name`, `asset_type`, `database_name`,
     `schema_name`, `table_name`, `workspace_name`, `description`, `url`,
     `created_in_integration`. `cast(null as ...)` the ones you don't have,
     following the existing queries — `fetch_assets()` only drops a row when
     `external_id`, `asset_name`, or `integration_account_id` is null, the
     rest are optional.
   - Build `external_id` to match the `externalId` Orchestra's own collector
     already produces for that integration (see *External ID conventions*
     above), so published assets merge instead of creating a duplicate
     graph. If you don't already know the convention for the new platform,
     check a real asset Orchestra collected with `list_assets` first.
   - If the new platform has lineage edges into or out of an existing one
     (e.g. Snowflake tables feeding, or fed by, something already modeled),
     add a matching entry to `EDGE_QUERIES` returning `from_external_id`,
     `to_external_id`, `integration`, `lineage_detail`, with its own
     `required_raw_tables`.

`fetch_edges()` in `publish_lineage.py` drops any edge whose `from`/`to` isn't
in the set of assets actually published, so an edge pointing at an asset you
forgot to add (or got the externalId convention wrong for) is silently
dropped instead of failing the whole API batch.
