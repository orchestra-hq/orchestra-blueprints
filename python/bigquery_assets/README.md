# BigQuery asset collection

`collect_bigquery_assets.py` replaces Orchestra's BigQuery asset configuration
with a script you run yourself. It reads the same metadata the built-in
collector does and writes it through the public asset API, so your BigQuery
tables, views and lineage keep showing up under Data assets after asset
configurations are removed.

Each run:

1. Lists every dataset in the project and fetches each table and view.
2. Reads the last seven days of query jobs, including the statements inside
   scripts, and turns each one's
   `referenced_tables` → destination table into a lineage edge.
3. Lists the BigQuery assets Orchestra already has for the project, then
   `POST /assets` for new ones and `PATCH /assets/{assetId}` for ones whose
   metadata changed. Unchanged assets are skipped.
4. Sends the lineage edges to `POST /assets/dependencies`.

Assets are matched on `externalId` (`<project>.<dataset>.<table>`), the key the
built-in collector uses, so assets it already created are updated in place
rather than duplicated. No metrics are written: query counts, usage, row counts
and bytes are not part of the public asset API.

## Setup

```bash
cd python/bigquery_assets
pip install -r requirements.txt
```

The script only depends on `google-cloud-bigquery` and `httpx`.

## Auth

**Orchestra API key.** Set `ORCHESTRA_API_KEY` to a **standard** (not read-only)
key from [workspace settings](https://app.getorchestra.io/settings/workspace).
Orchestra Python tasks inject this automatically.

**GCP service account.** Use the same service account as your BigQuery
connection. It needs:

* `roles/bigquery.metadataViewer` to list datasets and read table metadata.
* `roles/bigquery.resourceViewer` (`bigquery.jobs.listAll`) to read every user's
  query jobs for lineage. Without it the assets are still written and the run
  logs that lineage was skipped.

Pass it as `BIGQUERY_CREDENTIALS_JSON` (the key file's JSON as a string), or
point `GOOGLE_APPLICATION_CREDENTIALS` at the key file.

## Options

| Variable | Default | Purpose |
| --- | --- | --- |
| `ORCHESTRA_API_KEY` | required | Orchestra API key |
| `BIGQUERY_CREDENTIALS_JSON` | | Service account JSON as a string |
| `GOOGLE_APPLICATION_CREDENTIALS` | | Path to a service account key file, used when the variable above is unset |
| `BIGQUERY_PROJECT` | the service account's `project_id` | GCP project to collect from |
| `ASSET_TYPES` | `TABLE,VIEW` | Comma-separated asset types to collect |
| `ORCHESTRA_API_BASE` | `https://app.getorchestra.io/api/engine/public` | API base URL |

## Running

```bash
python collect_bigquery_assets.py --dry-run   # scan BigQuery and print, send nothing
python collect_bigquery_assets.py
```

The script exits non-zero if any asset or lineage write failed.

## Rate limits

The metadata API allows 50 requests a minute, and assets are written one at a
time. The script spaces its requests at 40 a minute and retries 429s and 5xxs
with backoff, honouring `Retry-After`. Expect the first run on a large project to
take a while: 400 new tables is about ten minutes. Later runs only patch what
changed. Progress, and a final count of assets created, updated, skipped and
failed, is logged.

## Scheduling it in Orchestra

Create a [Python connection](https://docs.getorchestra.io/docs/integrations/python)
pointing at a repository containing this folder, with
`BIGQUERY_CREDENTIALS_JSON` in its secrets. Then add a pipeline with one Python
task and a schedule. Match the cadence of your old asset configuration.

```yaml
version: v1
name: BigQuery asset collection
pipeline:
  collect:
    tasks:
      collect_bigquery_assets:
        integration: PYTHON
        integration_job: PYTHON_EXECUTE_SCRIPT
        parameters:
          package_manager: PIP
          python_version: '3.12'
          source: GIT
          project_dir: python/bigquery_assets
          build_command: pip install -r requirements.txt
          command: python collect_bigquery_assets.py
        depends_on: []
        name: Collect BigQuery assets
        connection: your_python_connection_12345
    depends_on: []
    name: Collect
schedule:
  - name: Daily at 6am
    cron: 0 6 ? * * *
    timezone: Europe/London
```

## Tests

```bash
pip install pytest
pytest test_collect_bigquery_assets.py
```
