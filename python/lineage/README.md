# Platform lineage: dlt -> BigQuery -> dbt -> Orchestra

Builds an end-to-end lineage graph in Orchestra by extracting metadata from every
platform in the stack, modelling it in BigQuery, and publishing it through
Orchestra's metadata API.

```
Fivetran API  ─┐
BigQuery API  ─┼─ dlt (MetaEngine, one child per source) ─→ BigQuery platform_lineage_raw
Lightdash API ─┘                                                      │
                                                                      ▼
                                       dbt Core (dbt_projects/bigquery_lineage)
                                                                      │
                                              platform_lineage.lineage_assets
                                              platform_lineage.lineage_edges
                                                                      │
                                             publish_lineage.py ──────┘
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

## Running locally

```bash
cd python/lineage
pip install -r requirements.txt

# One source at a time -- this is what each MetaEngine child does.
LINEAGE_SOURCE=lightdash python -m load_source
LINEAGE_SOURCE=bigquery  python -m load_source
LINEAGE_SOURCE=fivetran  python -m load_source

# Then, after dbt has built the marts:
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
| `BIGQUERY_PROJECT` | all | GCP project holding both datasets |
| `BIGQUERY_LOCATION` | all | BigQuery region, default `europe-west1` |
| `LINEAGE_RAW_DATASET` | extract | dlt landing dataset, default `platform_lineage_raw` |
| `LINEAGE_MART_DATASET` | publish | dbt output dataset, default `platform_lineage` |
| `LINEAGE_BQ_LOOKBACK_DAYS` | bigquery | Days of BigQuery job history to read for table-to-table edges, default `7` |
| `LIGHTDASH_PROJECT_UUIDS` | lightdash | Optional comma-separated allowlist of Lightdash projects |

The Lightdash and Fivetran extracts fail loudly with the exact list of missing
variable names rather than loading a partial graph.

### BigQuery job history is optional

`bigquery_job_edges` reads `INFORMATION_SCHEMA.JOBS_BY_PROJECT`, which needs
`bigquery.jobs.listAll` (`roles/bigquery.resourceViewer` at project level). The
demo service account does not have it, so the resource logs the denial and yields
nothing — the load still succeeds. Warehouse table-to-table edges then come from
`bigquery_view_refs` instead, which only needs INFORMATION_SCHEMA read access.
Grant the permission if you want lineage for tables materialised by dbt as
tables rather than views.

## Orchestra setup

Three things live outside this repo. The pipeline reports each one clearly rather
than half-working, so you can tell at a glance which is missing.

### 1. The dbt Core connection (required)

A dbt Core connection carries **both** the warehouse profile and the Git binding,
so one bound to a different repository fails at clone time -- before dbt runs --
with `Failed to find and clone the remote branch`. The connection must be:

| Setting | Value |
| --- | --- |
| Repository | `orchestra-hq/orchestra-blueprints` |
| Warehouse | BigQuery, project `reference-baton-392114`, location `europe-west1` |
| Dataset | anything; the models set their own via `+schema` and the `generate_schema_name` override |
| Profile name | `bigquery_lineage` (must match `dbt_project.yml`) |

Then map `DBT_CORE_BIGQUERY` in the Orchestra environment to that connection --
the dbt task reads `connection: ${{ ENV.DBT_CORE_BIGQUERY }}`, so attaching it
needs no change to the YAML.

### 2. Fivetran credentials (required for the Fivetran leg)

Add `FIVETRAN_API_KEY` and `FIVETRAN_API_SECRET` to the secret JSON of the Python
connection the extract runs under (`blueprints__meltano__51199`, which already
holds the Lightdash PAT and the BigQuery service account). Until then, trigger
with `sources: ["lightdash", "bigquery"]` -- the Fivetran child fails with the
exact missing variable names, it does not load a partial graph.

### 3. BigQuery job-history IAM (optional, richer graph)

Grant `roles/bigquery.resourceViewer` at project level to the service account the
extract uses (`dlt-user@reference-baton-392114.iam.gserviceaccount.com`) so
`bigquery_job_edges` can read `INFORMATION_SCHEMA.JOBS_BY_PROJECT`. Without it the
warehouse edges come only from `bigquery_view_refs`, which covers views but not
tables dbt materialises as tables.

### Testing on a branch

Orchestra pins a run to the last commit that touched the **pipeline YAML**, so a
commit that only changes Python or dbt files is not picked up. Pass the commit
explicitly when iterating:

```
start_pipeline(branch="<feature-branch>", commit="<sha>",
               runInputs={"branch": "<feature-branch>", "sources": [...]})
```

## Adding another platform

Four edits, no changes to the publisher or the API contract:

1. **Source** — add `sources/<platform>.py` exposing `<platform>_source()`, with
   every resource named `<platform>_*`. Add its branch to `build_source()` in
   `load_source.py` and its name to `KNOWN_SOURCES` in `config.py`.
2. **Matrix** — add the platform to `matrix.inputs.source` in the pipeline YAML.
   That is the only orchestration change; it becomes another parallel child.
3. **Staging model** — add `dbt_projects/bigquery_lineage/models/staging/stg_<platform>__*.sql`
   and declare the raw tables in `sources/platform_lineage_raw.yml`. Wrap the
   body in `{% if source_table_exists(...) %}` with a typed `limit 0` fallback,
   like the existing ones: platforms come online at different times, and a build
   that hard-fails on one missing table publishes no lineage at all.
4. **Marts** — add one `union all` block to `lineage_assets.sql` (using the
   integration's real `externalId` convention) and one to `lineage_edges.sql`
   for the edges into or out of the existing platforms.

`lineage_edges` inner-joins both ends against `lineage_assets`, so an edge
pointing at an asset you forgot to publish is dropped at build time instead of
failing the whole API batch.
