# dbt-orchestra on dbt v2: `ls` mapping, CLI flags, mixed install

Tested 2026-10-21 in the Orchestra demo account with dbt-oss 2.0.8 and
dbt-orchestra from sao-paolo `main` at 541283d (it reports itself as 1.4.0), on
BigQuery (`dbt_core__bigquery__01406`, dataset `dbt_sao_v2_edge`). Every task
sets `ORCHESTRA_SEED_STATE_ORCHESTRATION=true`. Without it the seed, and
everything downstream of it, always rebuilds.

Run links go to `https://app.getorchestra.io/pipeline-runs/<id>/lineage`. Where
one run holds several cases, the task name identifies the case.

| Run | Pipeline |
| --- | --- |
| [8567b203](https://app.getorchestra.io/pipeline-runs/8567b203-1fe3-4000-b335-76a3770ddfaa/lineage), [220bd9b4](https://app.getorchestra.io/pipeline-runs/220bd9b4-b60d-41cd-8c79-e85a776dbc4e/lineage) | `sao_v2_edge_claude_test` (cold, then warm `dbt build`) |
| [7a603857](https://app.getorchestra.io/pipeline-runs/7a603857-ed2a-4222-9110-61e11aa5012a/lineage) | `sao_v2_flag_matrix_claude_test` (chained, one task per case) |
| [1e064ab6](https://app.getorchestra.io/pipeline-runs/1e064ab6-9f2d-40e7-b862-8e2508516f9e/lineage) | `sao_v2_duckdb_profiles_claude_test` |
| [0b08f32c](https://app.getorchestra.io/pipeline-runs/0b08f32c-3e0a-40a6-a994-b38c41270c7f/lineage) | `sao_v2_project_dir_claude_test` |
| [b50755d1](https://app.getorchestra.io/pipeline-runs/b50755d1-fcaa-458d-a912-a80fb823d91b/lineage), [a1796b2a](https://app.getorchestra.io/pipeline-runs/a1796b2a-2a5c-48f2-8b43-9955d8eae815/lineage) | `sao_v2_mixed_install_claude_test` (PIP, UV) |

On 2.0.8, `dbtRunner().invoke(["ls", ...])` returns plain fqns in `res.result`,
even though stdout shows the `--output json` lines. So every v2 run below went
through `_nodes_from_fqns` (sao-paolo `src/orchestra_dbt/ls.py:67-76`). For
example, the package model's path came back package-relative from the manifest
(`models/pkg_edge.sql`), not as the JSON's `dbt_packages/...` path.

## 1. `ls` mapping edge cases

No run logged `Error getting [dbt ls]`. Every run logged
`Finding nodes to be executed:` followed by the expected node list.

| Case | Run / task | Nodes resolved | Reuse | Result |
| --- | --- | --- | --- | --- |
| Cold `dbt build`, all node kinds | 8567b203 | 6 (pkg, dim_edge v1+v2, stg, seed, snapshot) | 0/6, 7/7 built | PASS |
| Warm `dbt build` | 220bd9b4 | 6 | 5/6 (snapshot always rebuilds) | PASS |
| `--select dim_edge.v1` (versioned) | 7a603857 `sel_versioned_v1` | `sao_v2_edge.marts.dim_edge.v1` | 1/1 | PASS |
| `--select dim_edge` (both versions) | `sel_versioned_all` | v1, v2 | 2/2 | PASS |
| `--select package:edge_pkg` | `sel_package` | `edge_pkg.pkg_edge` | 1/1 | PASS |
| `--select snap_edge` | `sel_snapshot` | `sao_v2_edge.snap_edge` | 0/1, rebuilt (by design) | PASS |
| `--select edge_seed` | `sel_seed` | `sao_v2_edge.edge_seed` | 1/1 | PASS |
| `--select stg_edge` (model + singular test share fqn `sao_v2_edge.stg_edge`) | `sel_model_test_same_fqn` | the model only; the test is filtered out by `ls.py:74` | 1/1 | PASS |

## 2. CLI flags

| Flag | Run / task | What shows it was honoured | Warm reuse | Result |
| --- | --- | --- | --- | --- |
| `--project-dir ../bigquery_sao_v2_edge` (from `dbt_projects/sao_v2_runner`) | 0b08f32c `project_dir_1`, `project_dir_2` | `Patched ../bigquery_sao_v2_edge/seeds/properties.yml`; dbt `Loading ../sao_v2_runner/profiles.yml` | 5/6; with `--select dim_edge`, 2/2 | PASS |
| `--target-path tgt_alt` | 7a603857 `target_path` | Mapping worked. Locally, with no `target/` dir at all, it still mapped, so it read `tgt_alt/manifest.json` and not Orchestra's pre-copied `target/manifest.json` | 5/6 | PASS |
| `--profiles-dir .` (BigQuery) | `profiles_dir_bigquery` | dbt `Loading profiles.yml`; build succeeded | 5/6 | PASS |
| `--profiles-dir profiles_duckdb` | 1e064ab6 | dbt `Loading profiles_duckdb/profiles.yml`, `target 'dev'` | 5/6 | PASS |
| `--target alt` (DuckDB) | 1e064ab6 | `Finished 'build' ... for target 'alt'`; state grew 54→60 keys; the warm `alt` run reused against `alt` timestamps (10:05:02), not `dev`'s (10:04:54) | 5/6 | PASS |
| `--full-refresh` (twice) | `full_refresh_1`, `full_refresh_2` | `Full refresh detected. Stateful orchestration disabled.` | 7/7 built both times, 0 reused | PASS |
| warm build after full refresh | `warm_after_full_refresh` | reuse timestamps are the full refresh's (10:14:4x) | 5/6 | PASS |
| `--selector edge_marts` | `selector` | `ls` returned only `dim_edge` v1, v2 | 2/2 | PASS |

`--target` ran on DuckDB because the BigQuery connection's profile has only a
`dev` target, and its key is obfuscated, so no second BigQuery target could be
built. `orc` still runs against Orchestra HTTP state there. Orchestra only keeps
the last log for each identical command text, so for the DuckDB task only the
warm halves' logs survive. The cold halves are inferred from the state count and
timestamps.

## 3. Mixed install (dbt-core 1.11.7 + dbt-bigquery 1.11.3 + dbt-oss 2.0.8)

Both distributions own the same files (`bin/dbt`, `dbt/__init__.py`,
`dbt/cli/main.py`, `dbt/artifacts/...`), so whichever installs last wins, file
by file. `is_dbt_v2()` (sao-paolo `src/orchestra_dbt/compatibility.py:14-21`)
checks `dbt-core` first and returns `False` whenever dbt-core's metadata is
present, whatever is actually importable.

| Installer | Which files win | What runs | `is_dbt_v2()` | Outcome | Result |
| --- | --- | --- | --- | --- | --- |
| Orchestra PIP, `requirements.txt` (b50755d1 `mixed_install`) | dbt-core | `dbt --version` → Core 1.11.7, bigquery 1.11.3; build ran with `dbt=1.11.7` | False (matches) | `orc` took the 1.x path (`ls` JSON) and reused 5/6 against state the v2 runs wrote. SUCCEEDED, with **no warning that dbt-oss is installed and unused** | Silent downgrade to 1.x |
| Orchestra UV, `pyproject.toml` (a1796b2a `mixed_install_uv`) | dbt-oss | the `dbt` CLI itself: `ImportError: cannot import name 'ArtifactMixin' from 'dbt.artifacts.schemas.base'` | False | Orchestra's preflight `dbt debug` fails, so the task fails with "dbt debug failed to validate the configuration" before `orc` starts | Fails loudly (not in `orc`) |
| Local `uv pip install -r` (3 of 3 installs) / pip with dbt-oss reinstalled last | dbt-oss | same ImportError | False | `orc` exits 1 at its first dbt import (`ls.py:81`, logged at `ls.py:86` and `cli.py:186`) with `dbt-core is required (supported versions ...)`, even though dbt-core is installed | Fails loudly, misleading message |
| Local `uv sync` with the same `pyproject.toml` | dbt-core | 1.x | False | as PIP | Silent downgrade to 1.x |

So the winner depends on the installer, not on anything the user chose. In no
layout did the v2 engine run fully while `is_dbt_v2()` said False. That is the
case where the v2-only branches would take their 1.x paths
(`target_finder.py:70`, `source_freshness/__init__.py:143`,
`relation_existence.py:206`), but every layout tested here either ran 1.x
consistently or crashed on import.

### Repro: silent downgrade to 1.x

- Config: `dbt_projects/sao_v2_mixed_runner/requirements.txt` (dbt-core 1.11.7, dbt-bigquery 1.11.3, `dbt-oss>=2,<3`, dbt-orchestra@main), Orchestra PIP, `dbt build --project-dir ../bigquery_sao_v2_edge`.
- Log: `Running with dbt=1.11.7`, `Registered adapter: bigquery=1.11.3`, `5/6 nodes reused.`, `Done. PASS=1`.
- Expected: either v2 runs, or `orc` warns or fails because both majors are installed (the README says not to do this).
- Actual: 1.x runs and the task succeeds, with nothing to show that v2 was ignored.
- Likely cause: `compatibility.py:16-18` stops at the first distribution it finds (`dbt-core`) and never checks whether `dbt-oss`/`dbt` is also installed. No code path warns about both being present.

### Repro: misleading error when dbt-oss's files win

- Config: the same requirements with dbt-oss laid down last (`uv pip install -r`, or `pip install --force-reinstall --no-deps dbt-oss` after the rest).
- Log: `[ERROR] [dbt-orchestra] dbt-core is required (supported versions >=1.10,<1.13 or >=2,<3). Install it per README. Import error: cannot import name 'ArtifactMixin' ...`, exit 1.
- Expected: an error naming the conflict (dbt-core and dbt-oss both installed).
- Actual: tells the user to install dbt-core, which is already installed.
- Likely cause: `ls.py:81-87` and `cli.py:185-187` report every `ImportError` through `dbt_core_import_error_message` (`compatibility.py:7-11`) with no check for both distributions.

## Side findings (not v2 regressions; 1.x behaves the same)

- **A test-only selection runs nothing.** `orc dbt build --select test_name:stg_edge` on a warm run: `ls` (model/snapshot/seed only) returns `[]`. `cli.py:262` treats an empty `paths_to_run` as "no filter", so the log says `5/6 nodes reused`, all 5 get the reused tag, and the cautious exclusion (`modify.py:34-39`, `:124`) drops the test: `Nothing to do`. Plain `dbt build --select test_name:stg_edge` runs and passes the test. Same on dbt-core 1.11.7 locally. `orc dbt test --select stg_edge` also runs nothing.
- **Local mode keys state by node id, not target.** With `ORCHESTRA_LOCAL_RUN=true`, `asset_external_id.py:16-17` returns `node_id`. So `orc dbt build --target alt` reuses `dev`'s state and skips building into `alt`, and the snapshot then failed with `Table with name edge_seed does not exist`. This does not happen against Orchestra HTTP state, where keys use the relation name.

## Orchestra task gotchas hit along the way (not sao-paolo)

- Separate multiple commands with `;`. Newlines, in an input or on the task, are joined into one command.
- `shallow_clone_dirs` takes a space-separated list. Commas make it one bad path.
- The dbt Core task runs `dbt debug` in `project_dir` before any command, so `project_dir` has to be a dbt project. `sao_v2_runner` is an empty placeholder for this reason.
- `download_task_run_log` returns 403 for log names containing `../`. The same output is in `1/debug_task`.
- UV mode needs a `pyproject.toml`. It ignores `requirements.txt`.
