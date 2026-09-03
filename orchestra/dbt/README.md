# dbt Core pipelines

## `sao_multi_warehouse.yml`

One pipeline that runs the same state-aware-orchestration (SAO) A/B test against
seven warehouses. Pick one with the `warehouse` input; every other lane skips.

Each lane is a chain of task groups, all gated on `inputs.warehouse`:

| # | Group | Fires when |
|---|---|---|
| 0 | `seed raw_orders (X)` | the lane is selected — creates the source table if absent and resets its rows. Only on the four newer lanes; see below |
| 1 | `drop mid-DAG model (X)` | `drop_mid_model == True` — removes a relation dbt owns, using the warehouse's own connection |
| 2 | `[MAIN] dbt build (X)` | group 1 succeeded or skipped — builds from `main`, i.e. the **released** `dbt-orchestra` |
| 3 | `query mid-DAG model (X)` | group 2 succeeded — **expected to fail** if SAO reused the dropped node instead of rebuilding it |
| 4 | `dbt build (X)` | group 3 **failed** — rebuilds from `inputs.dbt_branch`, i.e. the **candidate** `dbt-orchestra` |
| 5 | `query mid-DAG model after rebuild (X)` | group 4 succeeded — passes if the candidate rebuilt the relation |

So a green group 5 after a red group 3 is the whole point: the released build
reused a node whose relation no longer existed, the candidate build did not.

Group 0 exists only on the Postgres, Redshift, MotherDuck and Fabric lanes,
whose source tables nothing else in the account maintains. It is idempotent
(create-if-absent, then delete and re-insert) and safe to re-run: the rows are
constant, so `max(order_date)` — and therefore the source freshness SAO reads —
does not move between runs. The Snowflake, Databricks and BigQuery lanes read
standing tables instead and have no group 0. Only MotherDuck's group 0 has
actually been exercised; the other three are written to their warehouse's
dialect but have not run yet.

### The lanes

| `warehouse` | dbt project | dbt Core connection | Warehouse connection | Mid-DAG relation |
|---|---|---|---|---|
| `snowflake` | `dbt_projects/snowflake` | `dbt_snowflake_blueprints_prod_07025` | `snowflake_db_user_72601` | `SNOWFLAKE_WORKING.PUBLIC_CLEAN.CUSTOMERS_CLEAN` |
| `databricks` | `dbt_projects/databricks` | `dbt_databricks_demo_54814` | `databricks__prod__39884` | `hive_metastore.default.orders` |
| `bigquery` | `dbt_projects/bigquery` | `dbt_core__bigquery__01406` | `dbt_bigquery_24777` | `dbt_sao_demo.stg_orders` |
| `postgres` | `dbt_projects/postgres_sao` | `${{ ENV.DBT_CORE_POSTGRES }}` | `postgres__prod__15825` | `dbt_sao_demo.stg_orders` |
| `redshift` | `dbt_projects/redshift_sao` | `${{ ENV.DBT_CORE_REDSHIFT }}` | `redshift_prod_02183` | `dbt_sao_demo.stg_orders` |
| `motherduck` | `dbt_projects/motherduck_sao` | `dbt_motherduck__prod__39243` | `md_my_db_09250` | `my_db.dbt_sao_demo.stg_orders` |
| `fabric` | `dbt_projects/fabric_sao` | `${{ ENV.DBT_CORE_FABRIC }}` | `fabric_prod_sql__workspace_identity___93745` | `dbt_sao_demo.stg_orders` |

Fabric's own integration only exposes data-pipeline and notebook jobs, so its
drop and query steps go through `FABRIC_SYNAPSE` / `FABRIC_SYNAPSE_RUN_QUERY`.

### Before a new lane can run

1. **Create the dbt Core connection.** Postgres, Redshift and Fabric have none in
   this workspace. Each needs this repo as its Git binding plus a `profiles.yml`
   defining the profile its `dbt_project.yml` names (`dbt_postgres`,
   `dbt_redshift`, `dbt_fabric`); the project READMEs carry a worked example.
   Then set the connection id as an environment variable on the Orchestra
   environment — `DBT_CORE_POSTGRES`, `DBT_CORE_REDSHIFT`, `DBT_CORE_FABRIC`.
   MotherDuck reuses the existing `dbt_motherduck__prod__39243`, whose
   `profiles.yml` already defines the `motherduck` profile every MotherDuck
   project in this repo expects.
2. **Nothing to do for `raw_orders`** — group 0 creates it. The equivalent DDL is
   in each project's README if you would rather create it by hand.
3. **Merge the dbt projects to `main`.** Group 2 clones `main` by design, so
   until `dbt_projects/*_sao` exists there, the `[MAIN]` leg of a new lane fails
   at clone time rather than testing anything.
4. **Fabric only:** `dbt-fabric` talks ODBC, so the runtime needs
   `Microsoft ODBC Driver 18 for SQL Server`. That is the one prerequisite a
   `requirements.txt` cannot satisfy.

If a `DBT_CORE_*` environment variable is unset, the task does **not** fail with
a missing-connection error. Orchestra resolves the reference to empty and falls
back to the workspace's default dbt Core connection, which here is the Snowflake
one — so the symptom is `dbt debug` reporting
`Could not find profile named 'dbt_postgres'`, several steps removed from the
actual cause.

The drop step uses the warehouse's own connection while dbt builds through the
dbt Core connection's `profiles.yml` — two separate credentials. Check they point
at the same database before trusting a lane: the Snowflake lane already straddles
two accounts (`JH88529.UK-SOUTH.AZURE` for dbt, `NOEPBEQ-WP69376` for the
`SNOWFLAKE` connection) with identically-named objects in both.

### Which `dbt-orchestra` is under test

The intent is that `main` installs the released `dbt-orchestra` and the test
branch installs the candidate via a git URL in each project's
`requirements.txt`, making group 2 and group 4 a fair comparison.

**As of run f8c34b1f that is not what happens.** Evidence from that run's two
MotherDuck legs:

- `main`'s `dbt_projects/motherduck_sao/requirements.txt` names no
  `dbt-orchestra` at all, yet the `[MAIN]` leg still logged
  `[dbt-orchestra] Version: 1.2.0. Stateful orchestration enabled.` So the task
  supplies the package itself when `use_state_orchestration: true`.
- The candidate leg cloned the branch, whose `requirements.txt` *does* carry
  `dbt-orchestra @ git+…@claude/warehouse-schema-existence-checks-2d3f0a`, but
  its pip step downloaded the same six wheels as the `main` leg and performed no
  git clone.
- The two legs' `dbt build` logs are byte-identical (1363 bytes): same version
  line, same `2 node(s) to be reused`, same reuse reasons, same `Nothing to do`.

So both legs run the same `dbt-orchestra`, and the A/B currently proves nothing
about the candidate. The likely mechanism — inferred, not confirmed — is that the
task installs its own pinned `dbt-orchestra` after the `requirements.txt` step,
overwriting the git version. Until that is settled, treat a failing group 5 as
"the candidate was never exercised" rather than "the candidate does not fix it".
