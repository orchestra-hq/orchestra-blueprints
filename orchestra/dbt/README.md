# dbt Core pipelines

## `sao_multi_warehouse.yml`

One pipeline that runs the same state-aware-orchestration (SAO) A/B test against
seven warehouses. Pick one with the `warehouse` input; every other lane skips.

Each lane is five task groups, all gated on `inputs.warehouse`:

| # | Group | Fires when |
|---|---|---|
| 1 | `drop mid-DAG model (X)` | `drop_mid_model == True` — removes a relation dbt owns, using the warehouse's own connection |
| 2 | `[MAIN] dbt build (X)` | group 1 succeeded or skipped — builds from `main`, i.e. the **released** `dbt-orchestra` |
| 3 | `query mid-DAG model (X)` | group 2 succeeded — **expected to fail** if SAO reused the dropped node instead of rebuilding it |
| 4 | `dbt build (X)` | group 3 **failed** — rebuilds from `inputs.dbt_branch`, i.e. the **candidate** `dbt-orchestra` |
| 5 | `query mid-DAG model after rebuild (X)` | group 4 succeeded — passes if the candidate rebuilt the relation |

So a green group 5 after a red group 3 is the whole point: the released build
reused a node whose relation no longer existed, the candidate build did not.

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
2. **Create the `raw_orders` source table** in each warehouse's `dbt_sao_demo`
   schema. The DDL is in each project's README; the pipeline reads that table but
   does not own it.
3. **Merge the dbt projects to `main`.** Group 2 clones `main` by design, so
   until `dbt_projects/*_sao` exists there, the `[MAIN]` leg of a new lane fails
   at clone time rather than testing anything.
4. **Fabric only:** `dbt-fabric` talks ODBC, so the runtime needs
   `Microsoft ODBC Driver 18 for SQL Server`. That is the one prerequisite a
   `requirements.txt` cannot satisfy.

The drop step uses the warehouse's own connection while dbt builds through the
dbt Core connection's `profiles.yml` — two separate credentials. Check they point
at the same database before trusting a lane: the Snowflake lane already straddles
two accounts (`JH88529.UK-SOUTH.AZURE` for dbt, `NOEPBEQ-WP69376` for the
`SNOWFLAKE` connection) with identically-named objects in both.

### Which `dbt-orchestra` is under test

`DBT_CORE_EXECUTE` has no parameter for installing a specific `dbt-orchestra`
ref — its build step is just the package manager at the project root — so the
candidate is pinned by a git URL in each project's `requirements.txt` on the test
branch. `main` carries no such pin and so installs the released build, and that
difference is the only one between the two: it is what makes group 2 and group 4
a fair comparison rather than two runs of the same code.
