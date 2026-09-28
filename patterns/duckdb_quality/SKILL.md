---
name: duckdb-snowflake-data-quality
description: Run declarative data quality tests against Snowflake using the DuckDB CLI, then classify the findings and post a summary to Slack. Use when asked to run data quality tests or checks on Snowflake, profile a warehouse table for quality issues, validate a table before or after a load, or investigate whether an alert is a data quality failure rather than a genuine operational anomaly.
---

# DuckDB data quality tests on Snowflake

Pull the `duckdb_quality` pattern from the blueprints repo, install the DuckDB
CLI, run the declarative test suite against Snowflake, classify what comes
back, and post the summary to Slack.

DuckDB is the driver and assertion engine only — every aggregate is evaluated
inside Snowflake. Never pull tables down to test them locally; the tables this
is aimed at have hundreds of millions of rows.

## 1. Pull the pattern

```bash
cd /tmp && rm -rf dq && \
  git clone --depth 1 --filter=blob:none --sparse \
  https://x-access-token:$GIT_TOKEN@github.com/orchestra-hq/orchestra-blueprints.git dq && \
  cd dq && git sparse-checkout set patterns/duckdb_quality
```

Leave `$GIT_TOKEN` as a variable reference so the token never appears in a
command you write. Do not print the remote URL or `.git/config`.

## 2. Install

```bash
cd /tmp/dq/patterns/duckdb_quality && ./install_duckdb_snowflake.sh
```

Idempotent, takes about a minute, downloads roughly 80 MB. It detects the
architecture, installs the DuckDB CLI, the `snowflake` community extension, and
the ADBC driver the extension needs.

If it fails, read the error before retrying — the script already handles the
common traps (arch mismatch, no `unzip`, no `pip`, version-stamped driver
path). A new failure is a real one. Report it rather than working around it.

## 3. Configure the suite

Copy `example.tests.json` and edit it for the tables in question. Check types
and their keys are documented in the pattern's `README.md`.

Credentials come from the environment. The Orchestra runtime exposes them as
`SNOWFLAKE__<FIELD>__<NAMESPACE>__<CONNECTION_ID>`, so map them to the names
the runner expects:

```bash
export SNOWFLAKE_ACCOUNT="$SNOWFLAKE__SNOWFLAKE_ACCOUNT__DEFAULT__<CONNECTION_ID>"
export SNOWFLAKE_USER="$SNOWFLAKE__SNOWFLAKE_USER__DEFAULT__<CONNECTION_ID>"
export SNOWFLAKE_PASSWORD="$SNOWFLAKE__SNOWFLAKE_PASSWORD__DEFAULT__<CONNECTION_ID>"
export SNOWFLAKE_DATABASE="$SNOWFLAKE__SNOWFLAKE_DATABASE__DEFAULT__<CONNECTION_ID>"
export SNOWFLAKE_WAREHOUSE="$SNOWFLAKE__SNOWFLAKE_WAREHOUSE__DEFAULT__<CONNECTION_ID>"
export SNOWFLAKE_ROLE="$SNOWFLAKE__SNOWFLAKE_ROLE__DEFAULT__<CONNECTION_ID>"
```

Read the connection id from the environment variable names available in the
session. Never echo a credential value.

**Always include `distinct_floor` and `freshness` checks**, not just
`not_null`. A column that is 0% null and stuck on a single value passes every
completeness check, and a fully NULL timestamp column makes `MAX()` return
NULL. Those two shapes are the ones that generate downstream anomaly alerts
that look like incidents and are not.

## 4. Run

```bash
python3 run_quality_tests.py --config <config>.json --output /tmp/dq-results.json
```

Exit `0` all passed, `1` something failed or errored, `2` bad config or the run
could not execute. A non-zero exit is the expected outcome when data is bad —
do not treat it as the tool being broken.

`/tmp/dq-results.json` holds the machine-readable results: one object per check
with `table`, `criticality`, `type`, `column`, `severity`, `observed`,
`operator`, `threshold`, `status`.

## 5. Classify before reporting

Do not just relay pass/fail counts. For each non-passing check:

- **Categorise** the issue: Freshness, Completeness, Validity, Uniqueness,
  Consistency, Schema, or Referential Integrity.
- **Distinguish a data quality failure from a genuine operational anomaly**,
  and state your confidence. A 100% NULL column or a single-valued column is a
  pipeline or mapping failure, not an anomaly worth paging anyone about.
- **Group by likely root cause.** One dead column plus one constant column plus
  sparse measures on the same table is usually a single upstream mapping
  failure, not four independent problems. Say so, and label it as an inference
  rather than a fact.
- **Rank by asset criticality and business impact**, using the suite's
  `criticality` and each check's `severity`. A failure on a table other
  models read beats a failure on a scratch table.
- **Recommend the next action**, highest noise-reduction first.

An `ERROR` status means the check could not be evaluated. Treat that as a
finding, not a gap — "we cannot measure freshness on this column" is itself
the answer.

## 6. Post the summary to Slack

This runtime has no Slack credential. Send through Orchestra by triggering the
alerting pipeline with `start_pipeline`:

- alias: `agent_dq_slack_alert`
- `runInputs.channel_name`: the target channel, e.g. `alert-testing`
- `runInputs.message`: the summary, in Slack mrkdwn

Slack mrkdwn is not Markdown: `*bold*`, `_italic_`, `` `code` ``, and links as
`<url|text>`. Markdown tables do not render — use short lines or a code block.
Keep it to the findings someone would act on, worst first, with counts rather
than every passing check.

Then confirm the run reached `SUCCEEDED` with `get_pipeline_run_status`, and
give the user the pipeline run link. If it failed, say the message was not
delivered — do not report a send you did not verify.

If the pipeline does not exist in the workspace, create it: one task,
`integration: SLACK`, `integrationJob: SEND_SLACK_MESSAGE`, parameters
`channel_name` and `text` wired to the two inputs. Confirm which Slack
connection serves the target channel rather than assuming the default; the
Orchestra Slack app must already be invited to the channel.

## Reporting back to the user

Lead with the findings, not the mechanics. State plainly which tables were
tested, what failed, what you think the root cause is, and what should happen
next. Mention the Slack post and link the pipeline run.
