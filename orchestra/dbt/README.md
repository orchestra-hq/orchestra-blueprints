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
| `bigquery` | `dbt_projects/bigquery` | `dbt_core__bigquery__01406` | `dbt_bigquery_24777` | `` `…dbt_sao_demo.Stg Orders Clean` `` |
| `postgres` | `dbt_projects/postgres_sao` | `${{ ENV.DBT_CORE_POSTGRES }}` | `postgres__prod__15825` | `dbt_sao_demo."Stg Orders Clean"` |
| `redshift` | `dbt_projects/redshift_sao` | `${{ ENV.DBT_CORE_REDSHIFT }}` | `redshift_prod_02183` | `dbt_sao_demo."stg orders clean"` |
| `motherduck` | `dbt_projects/motherduck_sao` | `dbt_motherduck__prod__39243` | `md_my_db_09250` | `my_db.dbt_sao_demo."Stg Orders Clean"` |
| `fabric` | `dbt_projects/fabric_sao` | `${{ ENV.DBT_CORE_FABRIC }}` | `fabric_prod_sql__workspace_identity___93745` | `dbt_sao_demo.[Stg Orders Clean]` |

Fabric's own integration only exposes data-pipeline and notebook jobs, so its
drop and query steps go through `FABRIC_SYNAPSE` / `FABRIC_SYNAPSE_RUN_QUERY`.

### Awkward identifiers are the point

Five lanes drop a relation whose name needs quoting to resolve: whitespace plus,
where the platform enforces it, case. The dbt model is still `stg_orders` in
every project — only its `alias` carries the name, which keeps `ref()` and the
`schema.yml` tests untouched. A relation-existence check that normalises or
unquotes identifiers will resolve these wrongly, which is what makes them worth
dropping.

What each platform actually enforces, and so what its name tests:

| Lane | Relation | Whitespace | Case |
|---|---|---|---|
| `postgres` | `dbt_sao_demo."Stg Orders Clean"` | quoted | **enforced** — quoted identifiers keep case |
| `redshift` | `dbt_sao_demo."stg orders clean"` | quoted | not testable — quoted mixed case is folded to lowercase unless `enable_case_sensitive_identifier` is on, so the alias is lowercase on purpose |
| `motherduck` | `my_db.dbt_sao_demo."Stg Orders Clean"` | quoted, **required** | preserved but matched case-insensitively |
| `fabric` | `dbt_sao_demo.[Stg Orders Clean]` | bracketed | **enforced** — warehouses default to the case-sensitive `Latin1_General_100_BIN2_UTF8` collation |
| `bigquery` | `` `…dbt_sao_demo.Stg Orders Clean` `` | backticked path | **enforced** — table names are case-sensitive and may contain Unicode `Zs` |

Verified on MotherDuck in run f514af36, which is the lane behaving exactly as
designed:

| Step | Result |
|---|---|
| `seed raw_orders` | SUCCEEDED — `{"Count": 8}` |
| `drop stg_orders` | SUCCEEDED — dropped `my_db.dbt_sao_demo."Stg Orders Clean"` |
| `[MAIN] dbt build` (check off) | SUCCEEDED — reused the node whose relation was gone |
| `query` (group 3) | **FAILED** — `Catalog Error: Table with name Stg Orders Clean does not exist!` |
| `dbt build` (check on) | SUCCEEDED |
| `query` (group 5) | SUCCEEDED — `{"count_star()": 8}` |

So the candidate resolves a quoted, space-containing, mixed-case relation
correctly through both the reuse and the rebuild path. Postgres, Redshift and
Fabric are written to their dialect but unrun — no dbt Core connection exists
for them yet.

Two things follow from that run:

- **A working demo reports the pipeline run as FAILED**, because group 3 failing
  is the point. Add `treat_failure_as_warning: true` to group 3's task if a green
  run is wanted for the lanes that are behaving.
- The MotherDuck error said `Did you mean "stg_orders"?`, so the pre-alias
  relation `my_db.dbt_sao_demo.stg_orders` is still there and no longer managed
  by dbt. Worth dropping once, or it will keep showing up in these hints.

**Snowflake and Databricks are deliberately left on plain names:**

- Databricks cannot do it *on this lane*, which is a narrower claim than it
  first looks. The lane builds into `hive_metastore` — the drop targets
  ``hive_metastore`.`default`.`orders``, and dbt-orchestra reported that exact
  relation as `deleted from the warehouse` in the 13:12 run on 2026-09-03 — and
  `hive_metastore` table names allow only alphanumeric ASCII and underscores.
  Nothing to quote, so nothing to test.

  **Unity Catalog is a different story.** UC bars spaces, `.`, `/` and control
  characters, but permits other special characters, and Databricks SQL requires
  backtick delimiters for them — so a UC relation named `stg-orders-clean` is a
  real quoting test, just not a whitespace one. Case still is not testable: UC
  stores object names lowercased and matches case-insensitively.

  Making the Databricks lane meaningful therefore means pointing it at a UC
  catalog, which is a change to the `profiles.yml` on the dbt Core connection
  rather than anything in this repo. The tidiest version would be a purpose-built
  `databricks_sao` project on a UC catalog, mirroring the other five, so the
  shared `dbt_projects/databricks` is left alone.
- Snowflake could, but not cheaply. dbt's Snowflake relations default to
  `quote_policy.identifier = False`, so an aliased name with a space compiles
  unquoted and fails; fixing it means turning on `quoting` for
  `dbt_projects/snowflake`, a project of ~30 models shared with other pipelines,
  and renaming a physical table other consumers may read by name. Both lanes
  drop models from those shared projects rather than purpose-built ones, which is
  the same reason.

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

### What actually switches the behaviour under test

The lever is an **environment variable on the candidate task**, not the installed
package:

```yaml
environment_variables: >-
  {"ORCHESTRA_VERIFY_RELATIONS_EXIST": "true"}
```

Every lane's group 4 (`dbt build (X)`) carries it; group 2 (`[MAIN] dbt build`)
does not. So the A/B is check-off versus check-on within the same
`dbt-orchestra`, which is a cleaner comparison than swapping package versions.

This matters because the `requirements.txt` git pin does **not** select the
version. Evidence from run f8c34b1f's two MotherDuck legs:

- `main`'s `dbt_projects/motherduck_sao/requirements.txt` names no
  `dbt-orchestra` at all, yet the `[MAIN]` leg still logged
  `[dbt-orchestra] Version: 1.2.0. Stateful orchestration enabled.` — the task
  supplies the package itself when `use_state_orchestration: true`.
- The candidate leg cloned the branch, whose `requirements.txt` *does* carry
  `dbt-orchestra @ git+…@claude/warehouse-schema-existence-checks-2d3f0a`, but
  its pip step downloaded the same six wheels as the `main` leg and ran no git
  clone.
- Both legs' `dbt build` logs were byte-identical (1363 bytes), down to the
  reuse reasons.

That makes the git pin in the seven `requirements.txt` files — the only
difference between `main` and the test branch — most likely redundant. Worth
deciding whether to drop it, which would collapse the branch into `main`.

Run f8c34b1f is the pre-env-var baseline: it showed group 3 failing (the drop
was not noticed) *and* group 5 failing, because neither leg had the check on.
With the variable in place, group 5 is the one expected to pass.
