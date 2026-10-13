# Orchestra dbt failure-simulation: results

Account: Orchestra Demo Account (`7868740d-923c-42fe-b7a5-324c5a32289f`), environment Production. Sweep ran 2026-10-13 09:50–14:15 UTC.
dbt branch `demo/failure-sim` (head `e2720d1`), project `dbt_projects/databricks_sao`, connection `dbt_databricks_demo_54814`.

## How the sweep was run

- **dbt 1.12.** I bumped the branch to `dbt-core==1.12.5` and `dbt-databricks==1.12.7`, so the `on_error` config is enforced. `demo_continue` in scenario 04 works because of this. dbt-orchestra is 1.4.0.
- **Three lanes ran in parallel**, one per variant:
  - **sao:** S shape, Touch source → SAO build.
  - **nsao:** N shape, a single non-SAO build.
  - **both:** B shape, Touch source → SAO build → non-SAO build. The non-SAO task runs even if SAO failed.
- **Each lane writes to its own schema.** That is `main.orchestra_demo_<lane>`, with the source in `orchestra_demo_raw_<lane>`. I chose this because SAO state is keyed by relation (`host.catalog.schema.table`), so a separate schema also gives each lane its own SAO state and its own assets.
- **Run order within a lane** was scenario by scenario, R0 (green) → R1 (failure) → R2 (fix). Scenario 02 ran R0 → R1 → R2 (fail, with a `demo_noop` touch) → R3 (green, with `demo_noop`) → R4. For the pair scenarios:
  - **06:** a then b at each step.
  - **08 and 12:** green runs went a then b; the R1 failure runs started both pipelines together.
- **Task-level green runs.** In 10, 11 and 12 the green and fix runs pass `--threads 1` as a neutral argument instead of an empty one.
- **One monitor for the whole grid:** `demo-dbt-by-asset` (`5d5e1c24`), groupBy asset, enabled at order 0. It has no alert destinations. I added a pipeline filter (the 44 scenario pipelines) to its `{integrations: [DBT_CORE]}` match, so it can't claim failures from the rest of the account. The other five demo monitors were created but not exercised (see "Not done").
- **I resolved incidents manually between scenarios.** Auto-resolve turned out to be a periodic sweep, not something triggered by the fix run (finding 1). So I resolved each lane's open incidents through the API before that lane's next scenario failed. That keeps scenarios from appending to each other's incidents. The "auto-resolved?" column records what happened.
- **Merge/unmerge test (04):** at 11:01 I merged nsao-04 `3819f488` into sao-04 `83926422`, then unmerged it.

Totals: 44 scenario pipelines, 144 sweep runs, plus 2 extra runs for the time-window test. 53 incidents, all from monitor `5d5e1c24`.
Run links use `https://app.getorchestra.io/pipeline-runs/<id>/lineage`, which is confirmed. Incident links use `https://app.getorchestra.io/incidents/<id>`, which is **assumed**.

## Key findings

1. **Auto-resolve is a periodic sweep, not part of the fix run.** `autoResolveOnSuccess=true`, yet no incident resolved within 4–30 min of a green fix run. The two nsao-12 control incidents, green since 11:49 and 11:51, were resolved by SYSTEM at **13:00:21**. Other accounts' incidents were resolved in the same second. sao-11, whose fix run went green at 13:03, was left OPEN by that sweep. Earlier SYSTEM resolves in the account landed at 07:00:20 and 19:00:20, which suggests the sweep runs every 6 hours.
2. **Model (asset) failures from one task run group into one incident.** That holds even with groupBy *asset*:
   - 03 and 07: 2 failed models → 1 incident with 2 assets.
   - 09: 8 failed models → 1 incident with 8 assets.
   - Skipped downstream nodes create no events.
3. **The same model failing again appends to the open incident.**
   - Across tasks: in 01 and 05 (both lane), the SAO and non-SAO tasks give one incident with 2 operations.
   - Across pipelines: 06, in every lane. In 06-both, an S-shape SAO pipeline and an N-shape non-SAO pipeline merged.
   - Across runs: 02 R1 and R2.
   - The gap can be at least 4m54s.
   - A new failure after the incident was **resolved** opens a **new** incident; resolved incidents are never reopened.
4. **Asset-less failures go per task and only group inside a short time window.** These are bad target, parse failure, bad flag, failing hook and failing run-operation.
   - 08 (hook): 1 incident per pipeline. The event is an OPERATION `databricks_sao_demo-on-run-start-0` with no asset.
   - 11: one incident per task, t1 and t2.
   - 10: nsao merged its three runs (~2m15s apart) into **1** incident. sao gave **3** (3m27s and 5m46s apart). both gave **6**, one per task per run.
   - The 10x test confirmed it: the same nsao pipeline failing again **6m49s** later opened a **new** incident while the first was still OPEN. So asset-less TASK events join an open incident only within roughly ~3 min (somewhere between 2m17s and 3m27s).
5. **SAO doesn't skip a model that failed last time.** In 02 (sao and both), R2 used a `demo_noop` touch, so the source was unchanged. dbt-orchestra reused 5 of 8 models (stg_*, fp_*, side_demo_sessions) but still re-executed `int_demo_orders`. It failed again and appended a second event to the same incident. Every run with a real `demo_touch_source` touch reused 0 models. Task-level failures computed no reuse at all, because dbt-orchestra's `dbt ls` errored.
6. **The B-shape condition works.** In all 11 failed B-shape runs, `tg_nsao` ran and failed after `tg_sao` FAILED; it was never skipped. The condition was `task_groups['tg_sao'].all().status == 'COMPLETED'`, wrapped in `${{ }}`.
7. **dbt 1.12 `on_error` works.** In 04, `demo_continue: [int_demo_orders]` let `int_demo_orders_enriched` run and fail on its own (ERROR 2, SKIP 2), instead of being skipped.
8. **Merge and unmerge both work.**
   - `merge_incidents` nests the child with a `parentIncidentId` and the child keeps its own status (RESOLVED). The parent's related resources become the union of both; its own `eventCount` doesn't change.
   - `unmerge_incidents` restores both incidents. Both actions add events to the parent's timeline.
9. **Naming and AI behaviour.**
   - Incident names vary: `<model> failed in <pipeline>`, `<model> failed`, `<task> failed in <pipeline>`, `<task> failed`.
   - Every incident got an AI_DIAGNOSIS plus a description rewrite within about 30 s. AI re-diagnosis on appended events is inconsistent: it fired in 06 and 10 but not in 02.
   - No incident sent an alert (alertThreads were empty), because the monitor has no destinations and the pipelines have no alerts.

## Not done, and caveats

- **Monitor comparison not run.** The whole grid uses `demo-dbt-by-asset`. The other monitors (`by-task`, `by-pipeline`, `by-connection`, `one-incident`, `mute`) were created but never enabled. A follow-up could re-run a few scenarios under each, for example 03, 06, 08 and 10.
- **Asset grouping across lanes is untested.** Lanes use separate schemas, so the same model in different lanes is a different asset. Same-asset grouping across SAO and non-SAO is still covered within the both lane and by 06-both.
- **Model counts are partly inferred.** For failed runs they come from the dbt `Done.` summary plus FAILED/SKIPPED operations; run_results artifacts weren't decoded. Green PASS counts in the both lane are inferred, and two both-lane failure summaries are reconstructed (09 R1 `0d337df1`, 10 R1c `c1237842` non-SAO).
- **Six incidents are left OPEN:**
  - sao-12 `c43aba9b` and `ba87d083`, and both-12 `e1f346bb` and `cd9eeb23`: all four pipelines have since gone green, so the next sweep (likely 19:00 UTC) should auto-resolve them.
  - The 10x test incidents `c57dd264` and `8cba8ed3`: that pipeline's last run failed, so these won't auto-resolve.
- `demo-dbt-by-asset` is still enabled at order 0, scoped to the 44 demo pipelines.
- The raw data and scripts are in the session scratchpad: `lane_*_raw.json`, `incidents_all.json`, `ledger.jsonl`, `findings.md`.

## Scenario × lane: incidents created (monitor `demo-dbt-by-asset`)

| scenario | sao | nsao | both |
|---|---|---|---|
| 01 | **1**: [e37a088b](https://app.getorchestra.io/incidents/e37a088b-048d-444f-8352-7025bc2435e4) 1 run(s), 1 asset | **1**: [086e5f7f](https://app.getorchestra.io/incidents/086e5f7f-b5e8-41ba-ba6b-397a5157b40f) 1 run(s), 1 asset | **1**: [e270dc68](https://app.getorchestra.io/incidents/e270dc68-9795-4a51-95f5-b24dfce99929) 1 run(s), 1 asset |
| 02 | **1**: [5e771fd6](https://app.getorchestra.io/incidents/5e771fd6-98a6-48e9-8045-b39f87c32ae7) 2 run(s), 1 asset | **1**: [d936cb8e](https://app.getorchestra.io/incidents/d936cb8e-91e6-463a-bc46-45fdacdbba73) 2 run(s), 1 asset | **1**: [61acb9da](https://app.getorchestra.io/incidents/61acb9da-8739-44a9-8c9c-7aacf065f91c) 2 run(s), 1 asset |
| 03 | **1**: [28d2e05b](https://app.getorchestra.io/incidents/28d2e05b-4b34-4e86-9224-30b60cf16948) 1 run(s), 2 assets | **1**: [cf5a2de2](https://app.getorchestra.io/incidents/cf5a2de2-e1c8-456d-bb48-b38726390b44) 1 run(s), 2 assets | **1**: [60df5f6e](https://app.getorchestra.io/incidents/60df5f6e-2196-44da-8ac4-e4d53537e8ae) 1 run(s), 2 assets |
| 04 | **1**: [83926422](https://app.getorchestra.io/incidents/83926422-5a3a-4b82-afed-895d3409e580) 1 run(s), 2 assets | **1**: [3819f488](https://app.getorchestra.io/incidents/3819f488-1714-4760-98de-7949c1b8df42) 1 run(s), 2 assets | **1**: [2d053a88](https://app.getorchestra.io/incidents/2d053a88-2422-4540-8dac-67f9f8f990e1) 1 run(s), 2 assets |
| 05 | — | — | **1**: [b4ae9081](https://app.getorchestra.io/incidents/b4ae9081-6335-4c52-b9c7-219621535006) 1 run(s), 1 asset |
| 06 | **1**: [9d4eefe5](https://app.getorchestra.io/incidents/9d4eefe5-c96c-4d39-b5e0-09d6606d92ea) 2 run(s), 1 asset | **1**: [b9dda6c6](https://app.getorchestra.io/incidents/b9dda6c6-ae5e-435e-ba6a-6c190ae7a20d) 2 run(s), 1 asset | **1**: [6a62989a](https://app.getorchestra.io/incidents/6a62989a-40c7-463c-ac99-3642e7c0ae42) 2 run(s), 1 asset |
| 07 | **1**: [960f6d25](https://app.getorchestra.io/incidents/960f6d25-7cd3-4ce4-ba99-39005a9d2467) 1 run(s), 2 assets | **1**: [9290bc20](https://app.getorchestra.io/incidents/9290bc20-6334-4f89-9c95-84abc4113dae) 1 run(s), 2 assets | **1**: [e389362c](https://app.getorchestra.io/incidents/e389362c-48fc-44b9-ab2d-b4445815fbb6) 1 run(s), 2 assets |
| 08 | **2**: [3021c3fa](https://app.getorchestra.io/incidents/3021c3fa-de88-4a13-81e9-96987ad8489c) 1 run(s), no asset (databricks_sao_demo-on-run-start-0)<br>[ca0f1b80](https://app.getorchestra.io/incidents/ca0f1b80-1b2a-48b1-9908-9c0c7c2b932a) 1 run(s), no asset (databricks_sao_demo-on-run-start-0) | **2**: [e5d6984e](https://app.getorchestra.io/incidents/e5d6984e-988f-4429-b064-784983c693b6) 1 run(s), no asset (databricks_sao_demo-on-run-start-0)<br>[0e19c2e8](https://app.getorchestra.io/incidents/0e19c2e8-1700-4aa8-bfbb-27103598e2b2) 1 run(s), no asset (databricks_sao_demo-on-run-start-0) | **2**: [dac7d0f6](https://app.getorchestra.io/incidents/dac7d0f6-2eac-4f93-9cca-5c12c8b62174) 1 run(s), no asset (databricks_sao_demo-on-run-start-0)<br>[feb1bde6](https://app.getorchestra.io/incidents/feb1bde6-45fa-4fb6-b00d-6ca037c6ef9e) 1 run(s), no asset (databricks_sao_demo-on-run-start-0) |
| 08b | — | **1**: [cb69f3ba](https://app.getorchestra.io/incidents/cb69f3ba-9509-41a9-88c0-47237601a9f6) 1 run(s), no asset (demo_failing_op) | — |
| 09 | **1**: [2ad5b796](https://app.getorchestra.io/incidents/2ad5b796-16ea-4281-a375-e64f33ace94f) 1 run(s), 8 assets | **1**: [96166a78](https://app.getorchestra.io/incidents/96166a78-b259-4a93-a257-066caa2d704c) 1 run(s), 8 assets | **1**: [f6405f68](https://app.getorchestra.io/incidents/f6405f68-7aa2-4f39-b3b5-573db014a742) 1 run(s), 8 assets |
| 10 | **3**: [a8898216](https://app.getorchestra.io/incidents/a8898216-6462-4033-a6fa-cfd8b050f955) 1 run(s), no asset (task)<br>[082b13ac](https://app.getorchestra.io/incidents/082b13ac-2b4e-4f33-9786-61467eb1ca24) 1 run(s), no asset (task)<br>[229ce387](https://app.getorchestra.io/incidents/229ce387-1617-4b45-83ba-56a992f3e316) 1 run(s), no asset (task) | **1**: [25afae93](https://app.getorchestra.io/incidents/25afae93-5355-4216-8f49-6f1803f7f86e) 3 run(s), no asset (task) | **6**: [81156110](https://app.getorchestra.io/incidents/81156110-766a-4f46-b484-d5c9acc471b2) 1 run(s), no asset (task)<br>[80fec7f1](https://app.getorchestra.io/incidents/80fec7f1-d87a-4722-a852-cc31f902ba5e) 1 run(s), no asset (task)<br>[026486e9](https://app.getorchestra.io/incidents/026486e9-d1cb-4b55-a349-5467b258a8e8) 1 run(s), no asset (task)<br>[774560cb](https://app.getorchestra.io/incidents/774560cb-8326-48cf-98a2-7a1c051d6d32) 1 run(s), no asset (task)<br>[32567d4f](https://app.getorchestra.io/incidents/32567d4f-0b20-44ef-ae24-df8f17502e96) 1 run(s), no asset (task)<br>[9676eb7e](https://app.getorchestra.io/incidents/9676eb7e-137b-4462-b1bc-3836728083d6) 1 run(s), no asset (task) |
| 10x | — | **2**: [c57dd264](https://app.getorchestra.io/incidents/c57dd264-d0cc-4c46-a373-9d9a6e5c80ca) 1 run(s), no asset (task)<br>[8cba8ed3](https://app.getorchestra.io/incidents/8cba8ed3-e812-4b31-89cf-69c02b5732ad) 1 run(s), no asset (task) | — |
| 11 | **2**: [94631f5b](https://app.getorchestra.io/incidents/94631f5b-2702-4678-a26a-ce6d131b9a66) 1 run(s), no asset (task)<br>[56886030](https://app.getorchestra.io/incidents/56886030-a1d4-4157-8a29-166ae827766a) 1 run(s), no asset (task) | **2**: [e4510bb9](https://app.getorchestra.io/incidents/e4510bb9-5a09-459c-9fa2-b0ab90ee4071) 1 run(s), no asset (task)<br>[5b41973a](https://app.getorchestra.io/incidents/5b41973a-6618-4df5-80a9-48ac8e5cb035) 1 run(s), no asset (task) | **2**: [6a7ac231](https://app.getorchestra.io/incidents/6a7ac231-ea1c-41da-a780-d638c07829c8) 1 run(s), no asset (task)<br>[0fad46fe](https://app.getorchestra.io/incidents/0fad46fe-452f-4006-bc43-f40cf056bcc0) 1 run(s), no asset (task) |
| 12 | **2**: [ba87d083](https://app.getorchestra.io/incidents/ba87d083-3a7e-4b83-8dea-6a38be943493) 1 run(s), no asset (task)<br>[c43aba9b](https://app.getorchestra.io/incidents/c43aba9b-4055-4478-a8fe-ea67d9f63225) 1 run(s), no asset (task) | **2**: [01615194](https://app.getorchestra.io/incidents/01615194-15df-497a-b36e-a65f2a36c638) 1 run(s), no asset (task)<br>[3b22e633](https://app.getorchestra.io/incidents/3b22e633-295c-465a-918d-c63a8cadf1ac) 1 run(s), no asset (task) | **2**: [cd9eeb23](https://app.getorchestra.io/incidents/cd9eeb23-90af-4961-9ae3-df392c2a430f) 1 run(s), no asset (task)<br>[e1f346bb](https://app.getorchestra.io/incidents/e1f346bb-0a1c-4d85-a214-b92c78c8b523) 1 run(s), no asset (task) |

## Full grid: one row per run

Columns: run (link) | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS (SAO reuse) | failure detail | incident(s) | new vs appended | events from this run | merged? | alert? | auto-resolved?

### 01 single-mid

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 4d7adc55](https://app.getorchestra.io/pipeline-runs/4d7adc55-1eab-46e5-8811-0d72d9bc2c5c/lineage) | demo-dbt-fail-01-single-mid-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (e1b8362b, 09:52:35)<br>dbt build (SAO): SUCCEEDED (51a73e61, 09:54:43) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 f9d5b6f6](https://app.getorchestra.io/pipeline-runs/f9d5b6f6-2cff-4576-bbc3-77da2958f5ec/lineage) | demo-dbt-fail-01-single-mid-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (cbe337d7, 09:58:22)<br>dbt build (SAO): FAILED (dfc9598f, 10:00:18) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 / SAO: REUSED 0 | PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [e37a088b](https://app.getorchestra.io/incidents/e37a088b-048d-444f-8352-7025bc2435e4) | new | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:14) |
| [R2 75c5f124](https://app.getorchestra.io/pipeline-runs/75c5f124-1aa6-45ea-825f-829524202994/lineage) | demo-dbt-fail-01-single-mid-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (03fa7e13, 10:04:59)<br>dbt build (SAO): SUCCEEDED (ab1a6591, 10:07:15) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- R1 int_demo_orders ERROR (3 SKIP), REUSED 0 (touch_source) -> 1 incident e37a088b, 1 OPERATION event.
- R2 green 10:07:15; incident OPEN until manual resolve 10:14:46.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 869534b1](https://app.getorchestra.io/pipeline-runs/869534b1-b73d-432b-a83d-a71521cc8bb5/lineage) | demo-dbt-fail-01-single-mid-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (f49e178f, 09:52:52) | PASS 11 | - | - | - | - | - | - | - |
| [R1 fc931740](https://app.getorchestra.io/pipeline-runs/fc931740-b523-4137-b1fd-89603e293674/lineage) | demo-dbt-fail-01-single-mid-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (9194cd0e, 09:56:22) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 | PASS=7 ERROR=1 SKIP=3 TOTAL=11; ERROR int_demo_orders Compilation Error DEMO_FAIL[int_demo_orders] | [086e5f7f](https://app.getorchestra.io/incidents/086e5f7f-b5e8-41ba-ba6b-397a5157b40f) | new | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:03) |
| [R2 257ce882](https://app.getorchestra.io/pipeline-runs/257ce882-ee11-4725-a1ec-b54f144a7501/lineage) | demo-dbt-fail-01-single-mid-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (1ee583e3, 09:58:57) | PASS 11 | - | - | - | - | - | - | - |

- R1 int_demo_orders ERROR (3 downstream SKIP) -> 1 incident with 1 OPERATION event; skipped nodes produced no events.
- Incident stayed OPEN after R2 green (09:58:57) until manual resolve 10:03:20.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 d80efe72](https://app.getorchestra.io/pipeline-runs/d80efe72-1b51-4a97-b9d3-fee1daf7d161/lineage) | demo-dbt-fail-01-single-mid-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (b357243a, 09:52:24)<br>dbt build (SAO): SUCCEEDED (8a16a72d, 09:54:34)<br>dbt build (non-SAO): SUCCEEDED (9c3a67a5, 09:56:15) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1 4b620dff](https://app.getorchestra.io/pipeline-runs/4b620dff-7ee8-4cee-835d-d16886ffc2af/lineage) | demo-dbt-fail-01-single-mid-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (87c634f0, 09:58:21)<br>dbt build (SAO): FAILED (65d24be9, 10:00:02)<br>dbt build (non-SAO): FAILED (87fbf803, 10:01:52) | dbt build (SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL<br>dbt build (non-SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL; Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [e270dc68](https://app.getorchestra.io/incidents/e270dc68-9795-4a51-95f5-b24dfce99929) | new | 2 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:17) |
| [R2 57df7529](https://app.getorchestra.io/pipeline-runs/57df7529-06f2-40b7-875f-f53867ad8b34/lineage) | demo-dbt-fail-01-single-mid-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (0c6da1c4, 10:05:01)<br>dbt build (SAO): SUCCEEDED (ee7da75e, 10:07:15)<br>dbt build (non-SAO): SUCCEEDED (4fbf45c2, 10:09:09) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- B-shape R1: SAO build ERROR int_demo_orders, then non-SAO build ran anyway (condition all().status COMPLETED) and hit the same ERROR -> ONE incident e270dc68 with 2 OPERATION events on the same asset (SAO 10:00:16, non-SAO 10:02:01); AI re-diagnosed on the 2nd event.

### 02 sao-skip-next

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 70d2eb7c](https://app.getorchestra.io/pipeline-runs/70d2eb7c-2632-4ecf-b442-4e5aff2fdf28/lineage) | demo-dbt-fail-02-sao-skip-next-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (3f30ceec, 10:10:46)<br>dbt build (SAO): SUCCEEDED (309efc56, 10:12:56) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 f4441cc8](https://app.getorchestra.io/pipeline-runs/f4441cc8-2936-4d4f-bc08-e308d3af3b53/lineage) | demo-dbt-fail-02-sao-skip-next-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (40478385, 10:16:30)<br>dbt build (SAO): FAILED (34e25282, 10:18:30) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 / SAO: REUSED 0 | PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [5e771fd6](https://app.getorchestra.io/incidents/5e771fd6-98a6-48e9-8045-b39f87c32ae7) | new | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:40) |
| [R2-fail+noop af6274a8](https://app.getorchestra.io/pipeline-runs/af6274a8-4596-4269-b2b3-14aedc6c2bb3/lineage) | demo-dbt-fail-02-sao-skip-next-sao | {"touch_cmd": "dbt run-operation demo_noop"}<br>touch: `demo_noop` | FAILED | Touch source: SUCCEEDED (ca6106e3, 10:21:45)<br>dbt build (SAO): FAILED (be34d3cf, 10:23:14) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 1 / SAO: REUSED 5/8 (log: '5 node(s) to be reused', '5/8 nodes reused'): stg_demo_events, stg_demo_users, fp_demo_alpha, fp_demo_beta, side_demo_sessions; executed: hook, int_demo_orders (ERROR); not_null_stg_demo_events_id not selected | dbt ran 5 nodes: PASS=1 ERROR=1 SKIP=3 TOTAL=5; ERROR int_demo_orders DEMO_FAIL | [5e771fd6](https://app.getorchestra.io/incidents/5e771fd6-98a6-48e9-8045-b39f87c32ae7) | appended | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:40) |
| [R3-green+noop b7dbba0e](https://app.getorchestra.io/pipeline-runs/b7dbba0e-3ccf-410b-9414-7a9e7a92e1f9/lineage) | demo-dbt-fail-02-sao-skip-next-sao | {"demo_vars": "{demo_lane: sao}", "touch_cmd": "dbt run-operation demo_noop"}<br>touch: `demo_noop` | SUCCEEDED | Touch source: SUCCEEDED (cc469ba9, 10:26:57)<br>dbt build (SAO): SUCCEEDED (76e33700, 10:29:00) | PASS 5 / SAO: REUSED 5: stg_demo_events, stg_demo_users, fp_demo_alpha, fp_demo_beta, side_demo_sessions; executed: hook, int_demo_orders, int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src (PASS 5) | - | - | - | - | - | - | - |
| [R4 0b82bc1a](https://app.getorchestra.io/pipeline-runs/0b82bc1a-93e4-4030-a746-bed1ab018ea5/lineage) | demo-dbt-fail-02-sao-skip-next-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (f331966d, 10:31:59)<br>dbt build (SAO): SUCCEEDED (15e5f3ee, 10:34:10) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- R1 (touch_source) full build, int_demo_orders ERROR -> incident 5e771fd6. R2-fail+noop: dbt-orchestra reused 5/8 (stg_demo_events/users, fp_alpha/beta, side_demo_sessions: 'no new data since last run' / 'upstream reused') but still EXECUTED int_demo_orders (previously failed) -> ERROR again -> appended 2nd event to 5e771fd6 (no AI re-diagnosis).
- R3-green+noop also reused the same 5 and executed int_demo_orders, int_demo_orders_enriched, mart + test (all OK). R4 (touch_source) reused 0.
- R3/R4 green 10:29/10:34; incident OPEN until manual resolve 10:40:41.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 31e0eabe](https://app.getorchestra.io/pipeline-runs/31e0eabe-8df2-42f9-8edc-7a32865d9e20/lineage) | demo-dbt-fail-02-sao-skip-next-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (42ac5cd1, 10:02:10) | PASS 11 | - | - | - | - | - | - | - |
| [R1 d69019c4](https://app.getorchestra.io/pipeline-runs/d69019c4-2db8-4c91-b9e0-643a1f4ff9ad/lineage) | demo-dbt-fail-02-sao-skip-next-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (a6b71e98, 10:05:09) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 | PASS=7 ERROR=1 SKIP=3 TOTAL=11; ERROR int_demo_orders DEMO_FAIL[int_demo_orders] | [d936cb8e](https://app.getorchestra.io/incidents/d936cb8e-91e6-463a-bc46-45fdacdbba73) | new | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:17) |
| [R2-fail+noop 6f097457](https://app.getorchestra.io/pipeline-runs/6f097457-2eac-4b86-a3af-7d50ee54cf7f/lineage) | demo-dbt-fail-02-sao-skip-next-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (88c7d130, 10:08:52) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 | PASS=7 ERROR=1 SKIP=3 TOTAL=11; ERROR int_demo_orders DEMO_FAIL[int_demo_orders] | [d936cb8e](https://app.getorchestra.io/incidents/d936cb8e-91e6-463a-bc46-45fdacdbba73) | appended | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:17) |
| [R3-green+noop 68aae0c4](https://app.getorchestra.io/pipeline-runs/68aae0c4-66cb-4e84-bd0d-f82cad421599/lineage) | demo-dbt-fail-02-sao-skip-next-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (b9cdb694, 10:11:05) | PASS 11 | - | - | - | - | - | - | - |
| [R4 4c1a1bce](https://app.getorchestra.io/pipeline-runs/4c1a1bce-eaff-4da3-91c5-f5ad8cd3f9db/lineage) | demo-dbt-fail-02-sao-skip-next-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (5ce84baa, 10:13:15) | PASS 11 | - | - | - | - | - | - | - |

- R1 and R2-fail+noop (same failing model) -> both events on ONE incident d936cb8e (R2 appended at 10:09:04); new incident rather than reopening 01's resolved incident on the same asset.
- R3 (10:11) and R4 (10:13) green; incident still OPEN until manual resolve 10:17:40.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 5f67119d](https://app.getorchestra.io/pipeline-runs/5f67119d-75bd-42e7-abbe-1bae6675bc26/lineage) | demo-dbt-fail-02-sao-skip-next-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (8fc4a203, 10:12:48)<br>dbt build (SAO): SUCCEEDED (7a02ef82, 10:14:38)<br>dbt build (non-SAO): SUCCEEDED (768689a3, 10:16:20) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1 8c1e2b87](https://app.getorchestra.io/pipeline-runs/8c1e2b87-050b-454a-8dbf-647bc9496618/lineage) | demo-dbt-fail-02-sao-skip-next-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (e257e73a, 10:19:21)<br>dbt build (SAO): FAILED (54ea2f5b, 10:21:05)<br>dbt build (non-SAO): FAILED (bece4583, 10:22:48) | dbt build (SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL<br>dbt build (non-SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL; Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [61acb9da](https://app.getorchestra.io/incidents/61acb9da-8739-44a9-8c9c-7aacf065f91c) | new | 2 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:53) |
| [R2-fail+noop 6bb8529a](https://app.getorchestra.io/pipeline-runs/6bb8529a-7f42-436b-aa0c-579723b38f09/lineage) | demo-dbt-fail-02-sao-skip-next-both | {"touch_cmd": "dbt run-operation demo_noop"}<br>touch: `demo_noop` | FAILED | Touch source: SUCCEEDED (1a52497a, 10:26:38)<br>dbt build (SAO): FAILED (094bec1c, 10:28:26)<br>dbt build (non-SAO): FAILED (e2f5b8cd, 10:29:57) | dbt build (SAO): FAILED PASS=1 ERROR=1 SKIP=3 REUSED=0 TOTAL=5; ERROR int_demo_orders DEMO_FAIL<br>dbt build (non-SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL / SAO: dbt build (SAO): REUSED 5: fp_demo_alpha, side_demo_sessions, fp_demo_beta, stg_demo_users, stg_demo_events | Done. PASS=1 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=5; ERROR int_demo_orders DEMO_FAIL; Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [61acb9da](https://app.getorchestra.io/incidents/61acb9da-8739-44a9-8c9c-7aacf065f91c) | appended | 2 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:53) |
| [R3-green+noop f3eec5dc](https://app.getorchestra.io/pipeline-runs/f3eec5dc-4e31-419c-9c3a-a2533e06c0c6/lineage) | demo-dbt-fail-02-sao-skip-next-both | {"demo_vars": "{demo_lane: both}", "touch_cmd": "dbt run-operation demo_noop"}<br>touch: `demo_noop` | SUCCEEDED | Touch source: SUCCEEDED (02c9086e, 10:31:47)<br>dbt build (SAO): SUCCEEDED (546423bb, 10:33:42)<br>dbt build (non-SAO): SUCCEEDED (22cddec5, 10:35:25) | dbt build (SAO): PASS 5<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 5: side_demo_sessions, fp_demo_beta, stg_demo_users, stg_demo_events, fp_demo_alpha | - | - | - | - | - | - | - |
| [R4 18ca6146](https://app.getorchestra.io/pipeline-runs/18ca6146-1e3c-4882-9ccb-3fc9d32dafd0/lineage) | demo-dbt-fail-02-sao-skip-next-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (9834ddb9, 10:39:49)<br>dbt build (SAO): SUCCEEDED (5322ea2b, 10:41:57)<br>dbt build (non-SAO): SUCCEEDED (8e46b0c8, 10:43:54) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- R1 and R2-fail+noop each produced 2 OPERATION events (SAO + non-SAO) -> all 4 on ONE incident 61acb9da.
- R2 (demo_noop): SAO build reused 5 (stg_demo_events/users, fp_alpha/beta, side) and re-executed int_demo_orders -> ERROR (dbt TOTAL=5); non-SAO build rebuilt all 11 and failed the same model. R3-green+noop: SAO reused the same 5. R4 (touch_source): reuse 0.

### 03 two-mid

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 b1cba04d](https://app.getorchestra.io/pipeline-runs/b1cba04d-6e56-402d-a275-894f66f7bccc/lineage) | demo-dbt-fail-03-two-mid-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (a23dcf66, 10:37:15)<br>dbt build (SAO): SUCCEEDED (4f8a0488, 10:39:08) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 38ab8ba6](https://app.getorchestra.io/pipeline-runs/38ab8ba6-45bd-4d39-bfe4-89c789e43408/lineage) | demo-dbt-fail-03-two-mid-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (4f4440ff, 10:42:07)<br>dbt build (SAO): FAILED (67ceecaf, 10:43:47) | ERROR 2: int_demo_orders, side_demo_sessions / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 6 / SAO: REUSED 0 | PASS=6 ERROR=2 SKIP=3 REUSED=0 TOTAL=11; ERROR side_demo_sessions, int_demo_orders DEMO_FAIL | [28d2e05b](https://app.getorchestra.io/incidents/28d2e05b-4b34-4e86-9224-30b60cf16948) | new | 2 (int_demo_orders, side_demo_sessions) | no | no (alertThreads empty) | no (manually resolved at 10:56) |
| [R2 42c814aa](https://app.getorchestra.io/pipeline-runs/42c814aa-d85b-41a4-8d4a-fcbad0bd9ff6/lineage) | demo-dbt-fail-03-two-mid-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (fab4668b, 10:47:08)<br>dbt build (SAO): SUCCEEDED (6bf185fc, 10:49:19) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- Two model errors in one task run -> ONE incident (28d2e05b) with 2 assets.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 c8e3a4ee](https://app.getorchestra.io/pipeline-runs/c8e3a4ee-733c-47d4-98c2-dc4f92699009/lineage) | demo-dbt-fail-03-two-mid-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (19a1a523, 10:16:48) | PASS 11 | - | - | - | - | - | - | - |
| [R1 885469e3](https://app.getorchestra.io/pipeline-runs/885469e3-8536-4c81-9f29-8c5780de3ef0/lineage) | demo-dbt-fail-03-two-mid-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (704ebc15, 10:19:29) | ERROR 2: int_demo_orders, side_demo_sessions / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 6 | PASS=6 ERROR=2 SKIP=3 TOTAL=11; ERROR side_demo_sessions, int_demo_orders DEMO_FAIL | [cf5a2de2](https://app.getorchestra.io/incidents/cf5a2de2-e1c8-456d-bb48-b38726390b44) | new | 2 (int_demo_orders, side_demo_sessions) | no | no (alertThreads empty) | no (manually resolved at 10:25) |
| [R2 b7e319a3](https://app.getorchestra.io/pipeline-runs/b7e319a3-43bb-47eb-99fb-afe321bd1fad/lineage) | demo-dbt-fail-03-two-mid-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (640c0f51, 10:21:59) | PASS 11 | - | - | - | - | - | - | - |

- Two independent model errors (int_demo_orders, side_demo_sessions) in one task run -> ONE incident with both assets (2 events).

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 4101e0dc](https://app.getorchestra.io/pipeline-runs/4101e0dc-b461-4a55-a65c-9be39d628da5/lineage) | demo-dbt-fail-03-two-mid-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (c4d07efb, 10:47:20)<br>dbt build (SAO): SUCCEEDED (3a9a7b9d, 10:49:26)<br>dbt build (non-SAO): SUCCEEDED (6be117f0, 10:51:30) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1 2ba3b00a](https://app.getorchestra.io/pipeline-runs/2ba3b00a-6ff1-4b3b-bb15-96e3de8c6633/lineage) | demo-dbt-fail-03-two-mid-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (bdfcbcf8, 10:54:50)<br>dbt build (SAO): FAILED (f7718582, 10:56:44)<br>dbt build (non-SAO): FAILED (503e1daf, 10:58:30) | dbt build (SAO): FAILED PASS=6 ERROR=2 SKIP=3 REUSED=0 TOTAL=11; ERROR side_demo_sessions, int_demo_orders DEMO_FAIL<br>dbt build (non-SAO): FAILED PASS=6 ERROR=2 SKIP=3 REUSED=0 TOTAL=11; ERROR side_demo_sessions, int_demo_orders DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | Done. PASS=6 WARN=0 ERROR=2 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR side_demo_sessions, int_demo_orders DEMO_FAIL; Done. PASS=6 WARN=0 ERROR=2 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR side_demo_sessions, int_demo_orders DEMO_FAIL | [60df5f6e](https://app.getorchestra.io/incidents/60df5f6e-2196-44da-8ac4-e4d53537e8ae) | new | 4 (int_demo_orders, side_demo_sessions) | no | no (alertThreads empty) | no (manually resolved at 11:14) |
| [R2 9e36013a](https://app.getorchestra.io/pipeline-runs/9e36013a-7a2d-41ba-9c41-e2be8845473b/lineage) | demo-dbt-fail-03-two-mid-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (71267258, 11:00:09)<br>dbt build (SAO): SUCCEEDED (763e4045, 11:02:24)<br>dbt build (non-SAO): SUCCEEDED (0daf5cd5, 11:04:34) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- 2 failing models x 2 tasks -> ONE incident 60df5f6e, 4 OPERATION events, 2 assets.

### 04 two-seq

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 17d8b6e0](https://app.getorchestra.io/pipeline-runs/17d8b6e0-492b-4c1a-865b-0b2edba1523b/lineage) | demo-dbt-fail-04-two-seq-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (61a97b35, 10:52:21)<br>dbt build (SAO): SUCCEEDED (c2796f7f, 10:54:27) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 05b4acb1](https://app.getorchestra.io/pipeline-runs/05b4acb1-5246-41e4-a634-c1c566bb2f44/lineage) | demo-dbt-fail-04-two-seq-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (dd55e774, 10:57:43)<br>dbt build (SAO): FAILED (ac7175ad, 10:59:48) | ERROR 2: int_demo_orders, int_demo_orders_enriched / SKIP: mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 / SAO: REUSED 0 | PASS=7 ERROR=2 SKIP=2 REUSED=0 TOTAL=11; ERROR int_demo_orders, int_demo_orders_enriched DEMO_FAIL | [83926422](https://app.getorchestra.io/incidents/83926422-5a3a-4b82-afed-895d3409e580) | new | 2 (int_demo_orders, int_demo_orders_enriched) | parent in manual merge test with nsao-04 3819f488 (11:01:16) then unmerged (11:01:30); currently no children | no (alertThreads empty) | no (manually resolved at 11:16) |
| [R2 aae5f207](https://app.getorchestra.io/pipeline-runs/aae5f207-fbf5-4946-97fa-efd8565a1bd2/lineage) | demo-dbt-fail-04-two-seq-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (f01dd86d, 11:03:07)<br>dbt build (SAO): SUCCEEDED (f613191f, 11:05:18) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- demo_continue -> int_demo_orders + int_demo_orders_enriched both ERROR, SKIP=2 -> ONE incident (83926422) with 2 assets; parent of the 11:01 manual merge/unmerge test with nsao-04.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 2030cf31](https://app.getorchestra.io/pipeline-runs/2030cf31-552c-4d38-b7e0-13f5d6836dbc/lineage) | demo-dbt-fail-04-two-seq-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (651efbcb, 10:24:40) | PASS 11 | - | - | - | - | - | - | - |
| [R1 be8f9485](https://app.getorchestra.io/pipeline-runs/be8f9485-e951-4342-b073-84c8e2ecf520/lineage) | demo-dbt-fail-04-two-seq-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (b680e1e4, 10:26:43) | ERROR 2: int_demo_orders, int_demo_orders_enriched / SKIP: mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 | PASS=7 ERROR=2 SKIP=2 TOTAL=11; ERROR int_demo_orders, int_demo_orders_enriched DEMO_FAIL | [3819f488](https://app.getorchestra.io/incidents/3819f488-1714-4760-98de-7949c1b8df42) | new | 2 (int_demo_orders, int_demo_orders_enriched) | manually merged into sao-04 83926422 at 11:01:16 then unmerged 11:01:30 (test); currently standalone | no (alertThreads empty) | no (manually resolved at 10:35) |
| [R2 ef13f4e8](https://app.getorchestra.io/pipeline-runs/ef13f4e8-b4c3-4a31-8883-bd530f9dc527/lineage) | demo-dbt-fail-04-two-seq-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (338d28d9, 10:29:51) | PASS 11 | - | - | - | - | - | - | - |

- demo_continue let int_demo_orders_enriched run and fail on its own: ERROR=2 SKIP=2 -> ONE incident with 2 assets.
- Incident was merged into sao-04 83926422 (11:01:16) then unmerged (11:01:30) as a manual test; now standalone.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 c64f2220](https://app.getorchestra.io/pipeline-runs/c64f2220-a3a5-4408-85fc-c76bf47644fd/lineage) | demo-dbt-fail-04-two-seq-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (462a096a, 11:07:56)<br>dbt build (SAO): SUCCEEDED (aebc0bf6, 11:10:11)<br>dbt build (non-SAO): SUCCEEDED (90dfdb3a, 11:11:56) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1 b192e23a](https://app.getorchestra.io/pipeline-runs/b192e23a-897f-4980-a10b-a2d0954000e9/lineage) | demo-dbt-fail-04-two-seq-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (0d6eb62c, 11:15:38)<br>dbt build (SAO): FAILED (09244447, 11:17:43)<br>dbt build (non-SAO): FAILED (40091d8d, 11:19:13) | dbt build (SAO): FAILED PASS=7 ERROR=2 SKIP=2 REUSED=0 TOTAL=11; ERROR int_demo_orders, int_demo_orders_enriched DEMO_FAIL<br>dbt build (non-SAO): FAILED PASS=7 ERROR=2 SKIP=2 REUSED=0 TOTAL=11; ERROR int_demo_orders, int_demo_orders_enriched DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | Done. PASS=7 WARN=0 ERROR=2 SKIP=2 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders, int_demo_orders_enriched DEMO_FAIL; Done. PASS=7 WARN=0 ERROR=2 SKIP=2 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders, int_demo_orders_enriched DEMO_FAIL | [2d053a88](https://app.getorchestra.io/incidents/2d053a88-2422-4540-8dac-67f9f8f990e1) | new | 4 (int_demo_orders_enriched, int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 11:35) |
| [R2 def821f7](https://app.getorchestra.io/pipeline-runs/def821f7-c6d4-47a4-920e-de601a311766/lineage) | demo-dbt-fail-04-two-seq-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (b26a4e30, 11:22:53)<br>dbt build (SAO): SUCCEEDED (b09676fe, 11:24:43)<br>dbt build (non-SAO): SUCCEEDED (4b7f782c, 11:26:39) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- demo_continue: int_demo_orders + int_demo_orders_enriched ERROR in both tasks -> ONE incident 2d053a88, 4 OPERATION events, 2 assets.

### 05 same-model-2-tasks

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 3981c173](https://app.getorchestra.io/pipeline-runs/3981c173-4188-4680-a1a0-74e30e7efc9b/lineage) | demo-dbt-fail-05-same-model-2-tasks-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (f6e1197e, 11:30:03)<br>dbt build (SAO): SUCCEEDED (f426fcfa, 11:32:11)<br>dbt build (non-SAO): SUCCEEDED (7bf89c5f, 11:34:02) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1 b9e6900c](https://app.getorchestra.io/pipeline-runs/b9e6900c-6f59-4c64-b671-6276f94c9db0/lineage) | demo-dbt-fail-05-same-model-2-tasks-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (141cf517, 11:37:18)<br>dbt build (SAO): FAILED (4f51a2eb, 11:38:56)<br>dbt build (non-SAO): FAILED (4f4bb3c7, 11:40:39) | dbt build (SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL<br>dbt build (non-SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL; Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [b4ae9081](https://app.getorchestra.io/incidents/b4ae9081-6335-4c52-b9c7-219621535006) | new | 2 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 11:57) |
| [R2 86b06756](https://app.getorchestra.io/pipeline-runs/86b06756-bf1c-4976-9e3a-67b11a90adac/lineage) | demo-dbt-fail-05-same-model-2-tasks-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (d3edb01d, 11:44:38)<br>dbt build (SAO): SUCCEEDED (153e45ee, 11:46:41)<br>dbt build (non-SAO): SUCCEEDED (3fa60ad4, 11:48:40) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- Same model failing in SAO and non-SAO task of one run -> ONE incident b4ae9081 with 2 OPERATION events (2 operations, 2 tasks, 1 asset).

### 06 same-model-2-pipes

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 2fc97fe1](https://app.getorchestra.io/pipeline-runs/2fc97fe1-9255-40b9-abdf-a8b8a8329aba/lineage) | demo-dbt-fail-06-same-model-2-pipes-sao-a | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (bed51e98, 11:08:18)<br>dbt build (SAO): SUCCEEDED (3b91339c, 11:10:30) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R0 5abe5a4b](https://app.getorchestra.io/pipeline-runs/5abe5a4b-8c1f-4bca-8858-f70a31f8c16c/lineage) | demo-dbt-fail-06-same-model-2-pipes-sao-b | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (a0aa6a5f, 11:13:18)<br>dbt build (SAO): SUCCEEDED (a1da275a, 11:15:31) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 b912539e](https://app.getorchestra.io/pipeline-runs/b912539e-28fc-427b-af53-f5a7c0100bbf/lineage) | demo-dbt-fail-06-same-model-2-pipes-sao-a | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (1afcda3c, 11:18:09)<br>dbt build (SAO): FAILED (ace9e595, 11:19:50) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 / SAO: REUSED 0 | PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [9d4eefe5](https://app.getorchestra.io/incidents/9d4eefe5-c96c-4d39-b5e0-09d6606d92ea) | new | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 11:40) |
| [R1 330dfe68](https://app.getorchestra.io/pipeline-runs/330dfe68-3909-48b2-be00-8cddef6e4497/lineage) | demo-dbt-fail-06-same-model-2-pipes-sao-b | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (cfc03fc6, 11:22:39)<br>dbt build (SAO): FAILED (f26f9cb2, 11:24:37) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 / SAO: REUSED 0 | PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [9d4eefe5](https://app.getorchestra.io/incidents/9d4eefe5-c96c-4d39-b5e0-09d6606d92ea) | appended | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 11:40) |
| [R2 f6d74d3f](https://app.getorchestra.io/pipeline-runs/f6d74d3f-a3f2-4050-b279-582ab065ac8b/lineage) | demo-dbt-fail-06-same-model-2-pipes-sao-a | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (4d0aa177, 11:27:43)<br>dbt build (SAO): SUCCEEDED (59e8e4fd, 11:29:54) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R2 66afd574](https://app.getorchestra.io/pipeline-runs/66afd574-5aec-4323-8f08-36fef29adf16/lineage) | demo-dbt-fail-06-same-model-2-pipes-sao-b | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (eaf4f6a8, 11:32:38)<br>dbt build (SAO): SUCCEEDED (a03bfc66, 11:34:44) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- Same model failing in pipe a (11:19:56) and pipe b (11:24:50) -> ONE incident 9d4eefe5; pipe b appended after 4m54s, AI re-diagnosed scope.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 c0b2243b](https://app.getorchestra.io/pipeline-runs/c0b2243b-3a55-4cf9-bd06-87fe296111b4/lineage) | demo-dbt-fail-06-same-model-2-pipes-nsao-a | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (7cbdc137, 10:32:16) | PASS 11 | - | - | - | - | - | - | - |
| [R0 67eb1959](https://app.getorchestra.io/pipeline-runs/67eb1959-aa97-4a60-8252-12b9fb649e4c/lineage) | demo-dbt-fail-06-same-model-2-pipes-nsao-b | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (26731cb6, 10:35:04) | PASS 11 | - | - | - | - | - | - | - |
| [R1 495ff467](https://app.getorchestra.io/pipeline-runs/495ff467-2ae4-4adc-9865-63da3a900539/lineage) | demo-dbt-fail-06-same-model-2-pipes-nsao-a | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (eb74dfbd, 10:37:00) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 | PASS=7 ERROR=1 SKIP=3 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [b9dda6c6](https://app.getorchestra.io/incidents/b9dda6c6-ae5e-435e-ba6a-6c190ae7a20d) | new | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:48) |
| [R1 224bbe2f](https://app.getorchestra.io/pipeline-runs/224bbe2f-faab-4d4c-adc7-c9d8897b66c3/lineage) | demo-dbt-fail-06-same-model-2-pipes-nsao-b | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (3171e5d8, 10:39:46) | ERROR 1: int_demo_orders / SKIP: int_demo_orders_enriched, mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 | PASS=7 ERROR=1 SKIP=3 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [b9dda6c6](https://app.getorchestra.io/incidents/b9dda6c6-ae5e-435e-ba6a-6c190ae7a20d) | appended | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 10:48) |
| [R2 fd7668f1](https://app.getorchestra.io/pipeline-runs/fd7668f1-4f4d-4486-9d27-37d9783f3652/lineage) | demo-dbt-fail-06-same-model-2-pipes-nsao-a | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (ef57d3af, 10:42:39) | PASS 11 | - | - | - | - | - | - | - |
| [R2 db957968](https://app.getorchestra.io/pipeline-runs/db957968-a9e4-4fd7-b188-e53d282d0e01/lineage) | demo-dbt-fail-06-same-model-2-pipes-nsao-b | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (dc737206, 10:44:57) | PASS 11 | - | - | - | - | - | - | - |

- Same model failing in two different pipelines (a 10:37, b 10:39) -> ONE incident b9dda6c6; pipe b appended, AI re-diagnosed scope.
- Both R2 green (10:42, 10:44); still OPEN until manual resolve 10:48:16.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 e9909c2a](https://app.getorchestra.io/pipeline-runs/e9909c2a-0984-4bef-a290-a8804deae0a3/lineage) | demo-dbt-fail-06-same-model-2-pipes-both-a | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (78d00783, 11:51:39)<br>dbt build (SAO): SUCCEEDED (a155ba72, 11:53:46) | dbt build (SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R0 d41fe938](https://app.getorchestra.io/pipeline-runs/d41fe938-c169-41b4-93a4-5c6955c30192/lineage) | demo-dbt-fail-06-same-model-2-pipes-both-b | {"demo_vars": "{demo_lane: both}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (1e45fd38, 11:56:44) | dbt build (non-SAO): PASS 11 | - | - | - | - | - | - | - |
| [R1 6e974056](https://app.getorchestra.io/pipeline-runs/6e974056-e2dd-4959-b8bd-fd66ed21ab36/lineage) | demo-dbt-fail-06-same-model-2-pipes-both-a | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (97aeeac6, 11:59:05)<br>dbt build (SAO): FAILED (ae67f57f, 12:01:09) | dbt build (SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [6a62989a](https://app.getorchestra.io/incidents/6a62989a-40c7-463c-ac99-3642e7c0ae42) | new | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 12:19) |
| [R1 d4c5d151](https://app.getorchestra.io/pipeline-runs/d4c5d151-5865-449f-993c-eb7dc54cee7c/lineage) | demo-dbt-fail-06-same-model-2-pipes-both-b | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (a4cb2dbf, 12:03:55) | dbt build (non-SAO): FAILED PASS=7 ERROR=1 SKIP=3 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | Done. PASS=7 WARN=0 ERROR=1 SKIP=3 NO-OP=0 REUSED=0 TOTAL=11; ERROR int_demo_orders DEMO_FAIL | [6a62989a](https://app.getorchestra.io/incidents/6a62989a-40c7-463c-ac99-3642e7c0ae42) | appended | 1 (int_demo_orders) | no | no (alertThreads empty) | no (manually resolved at 12:19) |
| [R2 f7a000c8](https://app.getorchestra.io/pipeline-runs/f7a000c8-09c5-4ba0-a6df-b7b0880def72/lineage) | demo-dbt-fail-06-same-model-2-pipes-both-a | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (3536776c, 12:06:21)<br>dbt build (SAO): SUCCEEDED (fc423cc2, 12:08:23) | dbt build (SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R2 6e973ff9](https://app.getorchestra.io/pipeline-runs/6e973ff9-7442-4a43-a481-fe3a864e3577/lineage) | demo-dbt-fail-06-same-model-2-pipes-both-b | {"demo_vars": "{demo_lane: both}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (4e362efb, 12:10:57) | dbt build (non-SAO): PASS 11 | - | - | - | - | - | - | - |

- Pipe a (S-shape, SAO) 12:01:18 and pipe b (N-shape, non-SAO) 12:04:01 failing the same model -> ONE incident 6a62989a across 2 pipelines and both task types.

### 07 same-folder

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 f76e4b59](https://app.getorchestra.io/pipeline-runs/f76e4b59-7d86-4ad1-a185-28720004128c/lineage) | demo-dbt-fail-07-same-folder-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (9391af49, 11:37:20)<br>dbt build (SAO): SUCCEEDED (ea889625, 11:39:08) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 b55b112a](https://app.getorchestra.io/pipeline-runs/b55b112a-5867-4672-b0d5-9a84c3971eb6/lineage) | demo-dbt-fail-07-same-folder-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (c66cc052, 11:42:13)<br>dbt build (SAO): FAILED (329ada74, 11:44:10) | ERROR 2: fp_demo_alpha, fp_demo_beta / SKIP: mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 / SAO: REUSED 0 | PASS=7 ERROR=2 SKIP=2 REUSED=0 TOTAL=11; ERROR fp_demo_beta, fp_demo_alpha DEMO_FAIL | [960f6d25](https://app.getorchestra.io/incidents/960f6d25-7cd3-4ce4-ba99-39005a9d2467) | new | 2 (fp_demo_alpha, fp_demo_beta) | no | no (alertThreads empty) | no (manually resolved at 11:59) |
| [R2 2e11ff2a](https://app.getorchestra.io/pipeline-runs/2e11ff2a-2c1a-4fd2-9a99-a825c436585c/lineage) | demo-dbt-fail-07-same-folder-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (8deebf84, 11:47:05)<br>dbt build (SAO): SUCCEEDED (1105d944, 11:49:14) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- fp_demo_alpha + fp_demo_beta ERROR -> ONE incident (960f6d25) with 2 assets.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 bd07bbcd](https://app.getorchestra.io/pipeline-runs/bd07bbcd-40ca-43d9-b2f2-20584d6585d6/lineage) | demo-dbt-fail-07-same-folder-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (18a9c696, 10:47:32) | PASS 11 | - | - | - | - | - | - | - |
| [R1 b5e62115](https://app.getorchestra.io/pipeline-runs/b5e62115-d306-4d38-b65d-11e63e1a513a/lineage) | demo-dbt-fail-07-same-folder-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (8a2631e3, 10:50:06) | ERROR 2: fp_demo_alpha, fp_demo_beta / SKIP: mart_demo_summary, not_null_mart_demo_summary_src / PASS 7 | PASS=7 ERROR=2 SKIP=2 TOTAL=11; ERROR fp_demo_beta, fp_demo_alpha DEMO_FAIL | [9290bc20](https://app.getorchestra.io/incidents/9290bc20-6334-4f89-9c95-84abc4113dae) | new | 2 (fp_demo_alpha, fp_demo_beta) | no | no (alertThreads empty) | no (manually resolved at 10:58) |
| [R2 7096217e](https://app.getorchestra.io/pipeline-runs/7096217e-c0b3-4852-9e4c-bbae9139a73c/lineage) | demo-dbt-fail-07-same-folder-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (9ba41a66, 10:52:38) | PASS 11 | - | - | - | - | - | - | - |

- Two failpath models (fp_demo_alpha, fp_demo_beta) in one run -> ONE incident with both assets.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 568cbd34](https://app.getorchestra.io/pipeline-runs/568cbd34-94bb-4108-aff3-49a8b13c4683/lineage) | demo-dbt-fail-07-same-folder-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (4b5b4061, 12:14:21)<br>dbt build (SAO): SUCCEEDED (f1f89e04, 12:16:12)<br>dbt build (non-SAO): SUCCEEDED (5cc1b715, 12:17:52) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1 1eed691c](https://app.getorchestra.io/pipeline-runs/1eed691c-c859-4d06-aaf2-0f4404143f36/lineage) | demo-dbt-fail-07-same-folder-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (0a403c49, 12:21:21)<br>dbt build (SAO): FAILED (7ba5a0e1, 12:23:26)<br>dbt build (non-SAO): FAILED (8abcb2c0, 12:25:15) | dbt build (SAO): FAILED PASS=7 ERROR=2 SKIP=2 REUSED=0 TOTAL=11; ERROR fp_demo_beta, fp_demo_alpha DEMO_FAIL<br>dbt build (non-SAO): FAILED PASS=7 ERROR=2 SKIP=2 REUSED=0 TOTAL=11; ERROR fp_demo_beta, fp_demo_alpha DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | Done. PASS=7 WARN=0 ERROR=2 SKIP=2 NO-OP=0 REUSED=0 TOTAL=11; ERROR fp_demo_beta, fp_demo_alpha DEMO_FAIL; Done. PASS=7 WARN=0 ERROR=2 SKIP=2 NO-OP=0 REUSED=0 TOTAL=11; ERROR fp_demo_beta, fp_demo_alpha DEMO_FAIL | [e389362c](https://app.getorchestra.io/incidents/e389362c-48fc-44b9-ab2d-b4445815fbb6) | new | 4 (fp_demo_alpha, fp_demo_beta) | no | no (alertThreads empty) | no (manually resolved at 12:41) |
| [R2 16148742](https://app.getorchestra.io/pipeline-runs/16148742-7a2f-4e26-8f31-2d0e757d5942/lineage) | demo-dbt-fail-07-same-folder-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (0d5b9892, 12:27:06)<br>dbt build (SAO): SUCCEEDED (989a61b1, 12:28:54)<br>dbt build (non-SAO): SUCCEEDED (850721e2, 12:30:53) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- fp_demo_alpha + fp_demo_beta in both tasks -> ONE incident e389362c, 4 OPERATION events, 2 assets.

### 08 hook-2-pipes

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 05871d76](https://app.getorchestra.io/pipeline-runs/05871d76-9013-465d-8d0a-30142d6bad14/lineage) | demo-dbt-fail-08-hook-2-pipes-sao-a | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (f6e0f302, 11:51:37)<br>dbt build (SAO): SUCCEEDED (b946afe1, 11:53:26) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R0 84a0894f](https://app.getorchestra.io/pipeline-runs/84a0894f-6dee-4fa4-90ea-06525c335efe/lineage) | demo-dbt-fail-08-hook-2-pipes-sao-b | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (b9418dfa, 11:56:07)<br>dbt build (SAO): SUCCEEDED (5961c872, 11:58:14) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 6440ce05](https://app.getorchestra.io/pipeline-runs/6440ce05-cc14-4b97-acd2-147ade358e72/lineage) | demo-dbt-fail-08-hook-2-pipes-sao-a | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (f9115d11, 12:01:22)<br>dbt build (SAO): FAILED (e1da87ef, 12:02:52) | ERROR 1: on-run-start-0 (hook) / SKIP: all 8 models + 2 tests / PASS 0 / SAO: REUSED 0 | PASS=0 ERROR=1 SKIP=10 REUSED=0 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] | [3021c3fa](https://app.getorchestra.io/incidents/3021c3fa-de88-4a13-81e9-96987ad8489c) | new | 1 (databricks_sao_demo-on-run-start-0) | no | no (alertThreads empty) | no (manually resolved at 12:16) |
| [R1 37ae7053](https://app.getorchestra.io/pipeline-runs/37ae7053-23d0-4864-a7f9-a889ecc07b85/lineage) | demo-dbt-fail-08-hook-2-pipes-sao-b | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (5ad38580, 12:01:05)<br>dbt build (SAO): FAILED (4a0a421f, 12:03:24) | ERROR 1: on-run-start-0 (hook) / SKIP: all 8 models + 2 tests / PASS 0 / SAO: REUSED 0 | PASS=0 ERROR=1 SKIP=10 REUSED=0 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] | [ca0f1b80](https://app.getorchestra.io/incidents/ca0f1b80-1b2a-48b1-9908-9c0c7c2b932a) | new | 1 (databricks_sao_demo-on-run-start-0) | no | no (alertThreads empty) | no (manually resolved at 12:16) |
| [R2 0b1480db](https://app.getorchestra.io/pipeline-runs/0b1480db-9765-44cf-ab10-0606103a0619/lineage) | demo-dbt-fail-08-hook-2-pipes-sao-a | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (7b506f22, 12:06:16)<br>dbt build (SAO): SUCCEEDED (fff7eda4, 12:08:06) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R2 e01f8f99](https://app.getorchestra.io/pipeline-runs/e01f8f99-6f48-4d2f-85f3-6146341343b3/lineage) | demo-dbt-fail-08-hook-2-pipes-sao-b | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (60564b73, 12:10:39)<br>dbt build (SAO): SUCCEEDED (32e3a76b, 12:12:27) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- Hook failure in pipes a and b (started together) -> TWO incidents (3021c3fa a, ca0f1b80 b), asset-less OPERATION events; PASS=0 SKIP=10.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 07c5b69e](https://app.getorchestra.io/pipeline-runs/07c5b69e-4d20-4a81-a5f9-e8460b2a952f/lineage) | demo-dbt-fail-08-hook-2-pipes-nsao-a | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (921d134a, 10:55:23) | PASS 11 | - | - | - | - | - | - | - |
| [R0 1a3cb803](https://app.getorchestra.io/pipeline-runs/1a3cb803-1253-43b1-b481-d596e9fadf39/lineage) | demo-dbt-fail-08-hook-2-pipes-nsao-b | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (83d9f95b, 10:57:59) | PASS 11 | - | - | - | - | - | - | - |
| [R1 e7ac054c](https://app.getorchestra.io/pipeline-runs/e7ac054c-a1cf-4812-892e-bc754353e2de/lineage) | demo-dbt-fail-08-hook-2-pipes-nsao-a | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (516925fb, 11:00:08) | ERROR 1: on-run-start-0 (hook) / SKIP: all 8 models + 2 tests / PASS 0 | PASS=0 ERROR=1 SKIP=10 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] | [e5d6984e](https://app.getorchestra.io/incidents/e5d6984e-988f-4429-b064-784983c693b6) | new | 1 (databricks_sao_demo-on-run-start-0) | no | no (alertThreads empty) | no (manually resolved at 11:09) |
| [R1 3e34c92a](https://app.getorchestra.io/pipeline-runs/3e34c92a-bcf8-441a-a241-5701e6ba37d0/lineage) | demo-dbt-fail-08-hook-2-pipes-nsao-b | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (8304e809, 11:00:28) | ERROR 1: on-run-start-0 (hook) / SKIP: all 8 models + 2 tests / PASS 0 | PASS=0 ERROR=1 SKIP=10 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] | [0e19c2e8](https://app.getorchestra.io/incidents/0e19c2e8-1700-4aa8-bfbb-27103598e2b2) | new | 1 (databricks_sao_demo-on-run-start-0) | no | no (alertThreads empty) | no (manually resolved at 11:09) |
| [R2 992bf3e0](https://app.getorchestra.io/pipeline-runs/992bf3e0-b720-4427-bb30-8beff115b11b/lineage) | demo-dbt-fail-08-hook-2-pipes-nsao-a | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (ec19c462, 11:03:42) | PASS 11 | - | - | - | - | - | - | - |
| [R2 5812c34a](https://app.getorchestra.io/pipeline-runs/5812c34a-5c77-4f14-a445-8b840eca6979/lineage) | demo-dbt-fail-08-hook-2-pipes-nsao-b | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (c128bf42, 11:06:09) | PASS 11 | - | - | - | - | - | - | - |

- Hook failure in two pipelines started together -> TWO incidents (one per pipeline/task run); event is OPERATION databricks_sao_demo-on-run-start-0 with no asset.
- PASS=0 ERROR=1 SKIP=10; skipped models produced no events.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 afedcb40](https://app.getorchestra.io/pipeline-runs/afedcb40-62ee-45db-9d45-df0ee13789ae/lineage) | demo-dbt-fail-08-hook-2-pipes-both-a | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (a9f43167, 12:34:20)<br>dbt build (SAO): SUCCEEDED (70385e5e, 12:36:25) | dbt build (SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R0 332906a6](https://app.getorchestra.io/pipeline-runs/332906a6-ec48-4311-9d89-be66c2836276/lineage) | demo-dbt-fail-08-hook-2-pipes-both-b | {"demo_vars": "{demo_lane: both}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (c2b8e83a, 12:40:30) | dbt build (non-SAO): PASS 11 | - | - | - | - | - | - | - |
| [R1 daf6075f](https://app.getorchestra.io/pipeline-runs/daf6075f-b3da-4320-ac0a-8ec1609b88f6/lineage) | demo-dbt-fail-08-hook-2-pipes-both-a | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (9da7cda0, 12:42:50)<br>dbt build (SAO): FAILED (48da98be, 12:44:40) | dbt build (SAO): FAILED PASS=0 ERROR=1 SKIP=10 REUSED=0 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] / SAO: dbt build (SAO): REUSED 0 | Done. PASS=0 WARN=0 ERROR=1 SKIP=10 NO-OP=0 REUSED=0 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] | [feb1bde6](https://app.getorchestra.io/incidents/feb1bde6-45fa-4fb6-b00d-6ca037c6ef9e) | new | 1 (databricks_sao_demo-on-run-start-0) | no | no (alertThreads empty) | no (manually resolved at 12:59) |
| [R1 f59fc28d](https://app.getorchestra.io/pipeline-runs/f59fc28d-8526-44e3-abd6-310356657250/lineage) | demo-dbt-fail-08-hook-2-pipes-both-b | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (55cb8d50, 12:42:53) | dbt build (non-SAO): FAILED PASS=0 ERROR=1 SKIP=10 REUSED=0 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] | Done. PASS=0 WARN=0 ERROR=1 SKIP=10 NO-OP=0 REUSED=0 TOTAL=11; ERROR on-run-start-0 hook [USER_RAISED_EXCEPTION] DEMO_FAIL[hook] | [dac7d0f6](https://app.getorchestra.io/incidents/dac7d0f6-2eac-4f93-9cca-5c12c8b62174) | new | 1 (databricks_sao_demo-on-run-start-0) | no | no (alertThreads empty) | no (manually resolved at 12:59) |
| [R2 4b988157](https://app.getorchestra.io/pipeline-runs/4b988157-4165-44e4-bd7a-47cb2fdca22c/lineage) | demo-dbt-fail-08-hook-2-pipes-both-a | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (920e975d, 12:46:43)<br>dbt build (SAO): SUCCEEDED (31c1b66e, 12:48:31) | dbt build (SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R2 a532cc26](https://app.getorchestra.io/pipeline-runs/a532cc26-9f6f-4f9b-810c-fbbc37fa11de/lineage) | demo-dbt-fail-08-hook-2-pipes-both-b | {"demo_vars": "{demo_lane: both}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (dd998dc9, 12:50:43) | dbt build (non-SAO): PASS 11 | - | - | - | - | - | - | - |

- Hook failure: pipe a (SAO) and pipe b (non-SAO), started together -> TWO incidents (feb1bde6 a, dac7d0f6 b), asset-less OPERATION events.

### 08b runop

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 ae83c2e7](https://app.getorchestra.io/pipeline-runs/ae83c2e7-9d74-4e6a-bdb6-548eb93ea567/lineage) | demo-dbt-fail-08b-runop-nsao | {"runop_cmd": "dbt run-operation demo_noop"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (e58da667, 11:08:16) | PASS 12 | - | - | - | - | - | - | - |
| [R1 d2cdc543](https://app.getorchestra.io/pipeline-runs/d2cdc543-6697-4eab-bd6e-5895f24785d7/lineage) | demo-dbt-fail-08b-runop-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (a9342208, 11:10:30) | no nodes ran | run-operation demo_failing_op raised [USER_RAISED_EXCEPTION] DEMO_FAIL[run-operation]; dbt build never ran (no models) | [cb69f3ba](https://app.getorchestra.io/incidents/cb69f3ba-9509-41a9-88c0-47237601a9f6) | new | 1 (demo_failing_op) | no | no (alertThreads empty) | no (manually resolved at 11:16) |
| [R2 08aa209b](https://app.getorchestra.io/pipeline-runs/08aa209b-e50e-43d3-8d29-03c27e5d2fd4/lineage) | demo-dbt-fail-08b-runop-nsao | {"runop_cmd": "dbt run-operation demo_noop"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (c1a1730e, 11:13:19) | PASS 12 | - | - | - | - | - | - | - |

- run-operation failure -> 1 incident, single OPERATION event demo_failing_op with no asset; dbt build step never ran.

### 09 all-models

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 fe5b5218](https://app.getorchestra.io/pipeline-runs/fe5b5218-8b7b-4fee-85b4-8ab5bcfcf830/lineage) | demo-dbt-fail-09-all-models-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (89e1bc7c, 12:14:16)<br>dbt build (SAO): SUCCEEDED (bbb87aad, 12:16:06) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 ef0ad9ef](https://app.getorchestra.io/pipeline-runs/ef0ad9ef-fa76-42bd-8da0-382d1fc05275/lineage) | demo-dbt-fail-09-all-models-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (68e33111, 12:18:23)<br>dbt build (SAO): FAILED (9b2d328c, 12:20:05) | ERROR 8: stg_demo_events, stg_demo_users, fp_demo_alpha, fp_demo_beta, side_demo_sessions, int_demo_orders, int_demo_orders_enriched, mart_demo_summary / SKIP: 0 / PASS 3 / SAO: REUSED 0 | 8 errors (all 8 models DEMO_FAIL; summary line truncated in message) | [2ad5b796](https://app.getorchestra.io/incidents/2ad5b796-16ea-4281-a375-e64f33ace94f) | new | 8 (x8: all 8 models) | no | no (alertThreads empty) | no (manually resolved at 12:32) |
| [R2 7fabb977](https://app.getorchestra.io/pipeline-runs/7fabb977-964a-48fc-b2b6-599db36e989a/lineage) | demo-dbt-fail-09-all-models-sao | {"demo_vars": "{demo_lane: sao}"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (47de5abd, 12:23:47)<br>dbt build (SAO): SUCCEEDED (30295727, 12:26:05) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- All 8 models ERROR (PASS=3: hook + 2 tests) -> ONE incident 2ad5b796, 8 OPERATION events, 8 assets (eventCount 12).

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 f40a9473](https://app.getorchestra.io/pipeline-runs/f40a9473-a467-46ea-86a3-81c36f279536/lineage) | demo-dbt-fail-09-all-models-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (2625b554, 11:15:44) | PASS 11 | - | - | - | - | - | - | - |
| [R1 09589e0b](https://app.getorchestra.io/pipeline-runs/09589e0b-a58c-4aa8-8824-21b7b0db25e6/lineage) | demo-dbt-fail-09-all-models-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (4aa72c4a, 11:18:20) | ERROR 8: stg_demo_events, stg_demo_users, fp_demo_alpha, fp_demo_beta, side_demo_sessions, int_demo_orders, int_demo_orders_enriched, mart_demo_summary / SKIP: 0 / PASS 3 | PASS=3 ERROR=8 SKIP=0 TOTAL=11 (hook + 2 tests pass); ERROR all 8 models DEMO_FAIL | [96166a78](https://app.getorchestra.io/incidents/96166a78-b259-4a93-a257-066caa2d704c) | new | 8 (x8: stg_demo_events, stg_demo_users, fp_demo_alpha, fp_demo_beta, side_demo_sessions, int_demo_orders, int_demo_orders_enriched, mart_demo_summary) | no | no (alertThreads empty) | no (manually resolved at 11:23) |
| [R2 f54ce7bf](https://app.getorchestra.io/pipeline-runs/f54ce7bf-5f82-4694-a840-2b2da98d052b/lineage) | demo-dbt-fail-09-all-models-nsao | {"demo_vars": "{demo_lane: nsao}"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (e984121e, 11:20:54) | PASS 11 | - | - | - | - | - | - | - |

- All 8 models ERROR in one task run -> ONE incident, 8 OPERATION events, 8 assets (eventCount 12).

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 d6ef8c06](https://app.getorchestra.io/pipeline-runs/d6ef8c06-a86f-4c0a-9cfe-880f3146d267/lineage) | demo-dbt-fail-09-all-models-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (e82dc813, 12:53:59)<br>dbt build (SAO): SUCCEEDED (bc443aaf, 12:56:07)<br>dbt build (non-SAO): SUCCEEDED (436b9bf5, 12:57:47) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1 0d337df1](https://app.getorchestra.io/pipeline-runs/0d337df1-b99d-4814-ba5f-8b3294f2d7f4/lineage) | demo-dbt-fail-09-all-models-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (3f3fd0fe, 13:01:15)<br>dbt build (SAO): FAILED (f407f6eb, 13:02:45)<br>dbt build (non-SAO): FAILED (bcdc2a8d, 13:04:09) | dbt build (SAO): FAILED 8 errors (summary truncated); ERROR stg_demo_events, stg_demo_users, fp_demo_beta, ... DEMO_FAIL<br>dbt build (non-SAO): FAILED 8 errors (summary truncated); ERROR stg_demo_events, stg_demo_users, fp_demo_beta, ... DEMO_FAIL / SAO: dbt build (SAO): REUSED 0 | 8 errors (summary truncated); ERROR stg_demo_events, stg_demo_users, fp_demo_beta, ... DEMO_FAIL; 8 errors (summary truncated); ERROR stg_demo_events, stg_demo_users, fp_demo_beta, ... DEMO_FAIL | [f6405f68](https://app.getorchestra.io/incidents/f6405f68-7aa2-4f39-b3b5-573db014a742) | new | 16 (mart_demo_summary, int_demo_orders_enriched, int_demo_orders, fp_demo_alpha, side_demo_sessions, fp_demo_beta, stg_demo_users, stg_demo_events) | no | no (alertThreads empty) | no (manually resolved at 13:19) |
| [R2 8ec07a40](https://app.getorchestra.io/pipeline-runs/8ec07a40-9d72-4137-ac71-0b89e41ed68a/lineage) | demo-dbt-fail-09-all-models-both | {"demo_vars": "{demo_lane: both}"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (186edf1a, 13:08:25)<br>dbt build (SAO): SUCCEEDED (64465058, 13:10:18)<br>dbt build (non-SAO): SUCCEEDED (166b918e, 13:12:02) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- All 8 models ERROR in both tasks -> ONE incident f6405f68 with 16 OPERATION events and 8 assets.

### 10 task-level

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 b97010fe](https://app.getorchestra.io/pipeline-runs/b97010fe-deb7-4d75-a130-51c8b5a6f082/lineage) | demo-dbt-fail-10-task-level-sao | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (a175b1cb, 12:29:04)<br>dbt build (SAO): SUCCEEDED (32763131, 12:31:12) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1a-bad-target 30f186ad](https://app.getorchestra.io/pipeline-runs/30f186ad-ab17-446d-bb73-832bc0ea6c49/lineage) | demo-dbt-fail-10-task-level-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (7e44449d, 12:33:56)<br>dbt build (SAO): FAILED (19b9982f, 12:35:27) | no nodes ran / SAO: no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Runtime Error: no target demo_target_does_not_exist (hit at dbt-orchestra dbt ls, source freshness, and build); no nodes ran | [a8898216](https://app.getorchestra.io/incidents/a8898216-6462-4033-a6fa-cfd8b050f955) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (manually resolved at 12:54) |
| [R1b-parse-fail 8ae01a99](https://app.getorchestra.io/pipeline-runs/8ae01a99-15df-4e0e-b495-46cbf30fe508/lineage) | demo-dbt-fail-10-task-level-sao | {"demo_args": "--vars \"{demo_parse_fail: true}\""}<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (2448d1c0, 12:37:33)<br>dbt build (SAO): FAILED (cd4a619b, 12:38:56) | no nodes ran / SAO: no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Compilation Error in model stg_demo_events DEMO_FAIL[parse] (at dbt ls, freshness, build); no nodes ran | [082b13ac](https://app.getorchestra.io/incidents/082b13ac-2b4e-4f33-9786-61467eb1ca24) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (manually resolved at 12:54) |
| [R1c-bad-flag 4504aac3](https://app.getorchestra.io/pipeline-runs/4504aac3-c067-40aa-bb56-77f65bc3642e/lineage) | demo-dbt-fail-10-task-level-sao | {"demo_args": "--not-a-real-flag"}<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (ae16709e, 12:43:11)<br>dbt build (SAO): FAILED (3970a10e, 12:44:45) | no nodes ran / SAO: log: '0 node(s) to be reused', '0/10 nodes reused' (dbt ls failed) | exit 2 No such option '--not-a-real-flag'; dbt-orchestra: dbt ls error, freshness OK (3 sources), '0 node(s) to be reused', '0/10 nodes reused' | [229ce387](https://app.getorchestra.io/incidents/229ce387-1617-4b45-83ba-56a992f3e316) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (manually resolved at 12:54) |
| [R2 b5de1c81](https://app.getorchestra.io/pipeline-runs/b5de1c81-cb12-4f06-9384-6f062e4db19f/lineage) | demo-dbt-fail-10-task-level-sao | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (edfee7cb, 12:46:28)<br>dbt build (SAO): SUCCEEDED (c8b068a4, 12:48:35) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- Three task-level failures in three runs of the same pipeline -> THREE incidents (a8898216, 082b13ac, 229ce387), 1 TASK event each, event gaps 3m27s and 5m46s. Contrast nsao-10: same three failures -> ONE incident (gaps ~2m16s). Event rows have identical shape in both lanes (see section below).
- R2 green 12:48:35; all three OPEN until manual resolve 12:54:57-58.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 6f336f65](https://app.getorchestra.io/pipeline-runs/6f336f65-bee7-49fb-b7a7-3017d700b2d9/lineage) | demo-dbt-fail-10-task-level-nsao | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (3b33ade6, 11:23:14) | PASS 11 | - | - | - | - | - | - | - |
| [R1a-bad-target 2c1eaff3](https://app.getorchestra.io/pipeline-runs/2c1eaff3-a45d-443a-8f46-78eb988fa040/lineage) | demo-dbt-fail-10-task-level-nsao | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (d0f82c6b, 11:25:17) | no nodes ran | exit 2 Runtime Error: profile has no target demo_target_does_not_exist (no models ran) | [25afae93](https://app.getorchestra.io/incidents/25afae93-5355-4216-8f49-6f1803f7f86e) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (manually resolved at 11:35) |
| [R1b-parse-fail 74628c96](https://app.getorchestra.io/pipeline-runs/74628c96-a4fa-474c-87c3-417039562061/lineage) | demo-dbt-fail-10-task-level-nsao | {"demo_args": "--vars \"{demo_parse_fail: true}\""} | FAILED | dbt build (non-SAO): FAILED (0ca5e987, 11:27:31) | no nodes ran | exit 2 Compilation Error in model stg_demo_events DEMO_FAIL[parse] at parse (no models ran) | [25afae93](https://app.getorchestra.io/incidents/25afae93-5355-4216-8f49-6f1803f7f86e) | appended | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (manually resolved at 11:35) |
| [R1c-bad-flag f64ed4d9](https://app.getorchestra.io/pipeline-runs/f64ed4d9-6064-483b-9598-0c00cccedba1/lineage) | demo-dbt-fail-10-task-level-nsao | {"demo_args": "--not-a-real-flag"} | FAILED | dbt build (non-SAO): FAILED (ae2ad92b, 11:29:48) | no nodes ran | exit 2 No such option '--not-a-real-flag' (no models ran) | [25afae93](https://app.getorchestra.io/incidents/25afae93-5355-4216-8f49-6f1803f7f86e) | appended | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (manually resolved at 11:35) |
| [R2 7a296f35](https://app.getorchestra.io/pipeline-runs/7a296f35-027e-4081-b62a-065edccaa320/lineage) | demo-dbt-fail-10-task-level-nsao | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (372968e2, 11:32:50) | PASS 11 | - | - | - | - | - | - | - |

- Three task-level failures (bad target, parse fail, bad flag) in three separate runs of the same pipeline -> ONE incident 25afae93 with 3 TASK events (gaps 2m15s, 2m17s), no asset/operation resources; AI re-diagnosed after each.
- R2 green 11:32:50; still OPEN until manual resolve 11:35:42.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 f0cceee0](https://app.getorchestra.io/pipeline-runs/f0cceee0-c060-4522-bd92-9abefb3821dd/lineage) | demo-dbt-fail-10-task-level-both | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (a00ae415, 13:14:23)<br>dbt build (SAO): SUCCEEDED (9e0bc480, 13:16:32)<br>dbt build (non-SAO): SUCCEEDED (18bd55b5, 13:18:26) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R1a-bad-target 74d909c7](https://app.getorchestra.io/pipeline-runs/74d909c7-fc88-4111-a3e9-a545dca91644/lineage) | demo-dbt-fail-10-task-level-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (cb3c73a4, 13:20:51)<br>dbt build (SAO): FAILED (602fa400, 13:22:11)<br>dbt build (non-SAO): FAILED (50cfa3dc, 13:23:29) | dbt build (SAO): FAILED exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran<br>dbt build (non-SAO): FAILED exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran / SAO: dbt build (SAO): no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran; exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran | [81156110](https://app.getorchestra.io/incidents/81156110-766a-4f46-b484-d5c9acc471b2)<br>[80fec7f1](https://app.getorchestra.io/incidents/80fec7f1-d87a-4722-a852-cc31f902ba5e) | new<br>new | 1 (TASK event (TASK))<br>1 (TASK event (TASK)) | no<br>no | no (alertThreads empty)<br>no (alertThreads empty) | no (manually resolved at 13:48)<br>no (manually resolved at 13:48) |
| [R1b-parse-fail 39607037](https://app.getorchestra.io/pipeline-runs/39607037-45fa-4d56-94cb-c7bc672f908d/lineage) | demo-dbt-fail-10-task-level-both | {"demo_args": "--vars \"{demo_parse_fail: true}\""}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (d4b9093c, 13:27:25)<br>dbt build (SAO): FAILED (d6a09c5e, 13:28:48)<br>dbt build (non-SAO): FAILED (7289419f, 13:30:24) | dbt build (SAO): FAILED exit 2 Compilation Error stg_demo_events DEMO_FAIL[parse]; no nodes ran<br>dbt build (non-SAO): FAILED exit 2 Compilation Error stg_demo_events DEMO_FAIL[parse]; no nodes ran / SAO: dbt build (SAO): no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Compilation Error stg_demo_events DEMO_FAIL[parse]; no nodes ran; exit 2 Compilation Error stg_demo_events DEMO_FAIL[parse]; no nodes ran | [026486e9](https://app.getorchestra.io/incidents/026486e9-d1cb-4b55-a349-5467b258a8e8)<br>[774560cb](https://app.getorchestra.io/incidents/774560cb-8326-48cf-98a2-7a1c051d6d32) | new<br>new | 1 (TASK event (TASK))<br>1 (TASK event (TASK)) | no<br>no | no (alertThreads empty)<br>no (alertThreads empty) | no (manually resolved at 13:48)<br>no (manually resolved at 13:48) |
| [R1c-bad-flag c1237842](https://app.getorchestra.io/pipeline-runs/c1237842-f1c0-499d-ae56-c2ffb3d409af/lineage) | demo-dbt-fail-10-task-level-both | {"demo_args": "--not-a-real-flag"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (cdc5b3b4, 13:32:30)<br>dbt build (SAO): FAILED (5731e6d4, 13:34:00)<br>dbt build (non-SAO): FAILED (a81758f0, 13:35:26) | dbt build (SAO): FAILED exit 2 No such option '--not-a-real-flag'; no nodes ran (SAO: 0/10 nodes reused)<br>dbt build (non-SAO): FAILED exit 2 No such option '--not-a-real-flag'; no nodes ran / SAO: dbt build (SAO): log: '0/10 nodes reused' (dbt ls failed) | exit 2 No such option '--not-a-real-flag'; no nodes ran (SAO: 0/10 nodes reused); exit 2 No such option '--not-a-real-flag'; no nodes ran | [32567d4f](https://app.getorchestra.io/incidents/32567d4f-0b20-44ef-ae24-df8f17502e96)<br>[9676eb7e](https://app.getorchestra.io/incidents/9676eb7e-137b-4462-b1bc-3836728083d6) | new<br>new | 1 (TASK event (TASK))<br>1 (TASK event (TASK)) | no<br>no | no (alertThreads empty)<br>no (alertThreads empty) | no (manually resolved at 13:48)<br>no (manually resolved at 13:48) |
| [R2 743bf4e9](https://app.getorchestra.io/pipeline-runs/743bf4e9-4319-4349-8f67-1ee82b1b3e44/lineage) | demo-dbt-fail-10-task-level-both | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (af2cc032, 13:37:01)<br>dbt build (SAO): SUCCEEDED (97f86930, 13:39:08)<br>dbt build (non-SAO): SUCCEEDED (3fd3cf7f, 13:41:02) | dbt build (SAO): PASS 11<br>dbt build (non-SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |

- Each of the 3 runs failed in BOTH tasks (non-SAO still ran after SAO failed) -> SIX incidents, 1 TASK event each: one per task per run (81156110/80fec7f1, 026486e9/774560cb, 32567d4f/9676eb7e).
- Same-run SAO and non-SAO TASK failures ~1.3 min apart did not group (different task); same task across runs (~6.5 min apart) did not group either (cf. nsao-10, where ~2m15s gaps grouped).

### 10x time-window test

#### nsao

Two extra runs of the nsao-10 pipeline (8fbdcec7), same task (`dbt build (non-SAO)`), spaced further apart than in scenario 10.

| run | inputs | task status | failure detail | incident | created | status | gap to previous failure |
|---|---|---|---|---|---|---|---|
| [X1 bad target 384a029a](https://app.getorchestra.io/pipeline-runs/384a029a-bb91-4a8c-9d9c-3251785e7603/lineage) | --target demo_target_does_not_exist | dbt build (non-SAO): FAILED (d1b308bc, 13:36:53) | exit 2 Runtime Error: profile has no target demo_target_does_not_exist (no models ran) | [c57dd264](https://app.getorchestra.io/incidents/c57dd264-d0cc-4c46-a373-9d9a6e5c80ca) | 13:37:01 | OPEN | - |
| [X2 parse fail ccfcbf5b](https://app.getorchestra.io/pipeline-runs/ccfcbf5b-e1be-4355-8e6c-c718a901a1e7/lineage) | --vars "{demo_parse_fail: true}" | dbt build (non-SAO): FAILED (c72bde70, 13:43:42) | exit 2 Compilation Error in model stg_demo_events DEMO_FAIL[parse] (no models ran) | [8cba8ed3](https://app.getorchestra.io/incidents/8cba8ed3-e812-4b31-89cf-69c02b5732ad) | 13:43:51 | OPEN | 6m49s (task failed 13:36:53 -> 13:43:42); events 13:37:01 -> 13:43:51 |

- X2 created a NEW incident (8cba8ed3) while c57dd264 was still OPEN (c57dd264 has no STATUS_CHANGED event; still OPEN at 14:2x). Both EVENT rows: TASK/FAILED, pipelineId 8fbdcec7, no operation/asset.
- Same pipeline + same task + earlier incident OPEN: grouped at ~2m15s gaps (scenario 10, 25afae93) but split at 6m49s -> consistent with a time window for asset-less TASK events.

### 11 two-task-level

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 59078207](https://app.getorchestra.io/pipeline-runs/59078207-c669-41c8-b67e-604e364508ee/lineage) | demo-dbt-fail-11-two-task-level-sao | {"t1_args": "--threads 1", "t2_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (18b603eb, 12:50:38)<br>t1 bad target: SUCCEEDED (c6f77869, 12:52:43)<br>t2 parse fail: SUCCEEDED (79671dce, 12:52:33) | PASS 12 / SAO: t1 bad target: REUSED 0; t2 parse fail: REUSED 0 | - | - | - | - | - | - | - |
| [R1 ea60c279](https://app.getorchestra.io/pipeline-runs/ea60c279-a807-4555-bf21-4a98e6171ceb/lineage) | demo-dbt-fail-11-two-task-level-sao | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (b96f6ccc, 12:56:37)<br>t1 bad target: FAILED (1f6d8ef2, 12:58:07)<br>t2 parse fail: FAILED (9ce5d07a, 12:58:22) | no nodes ran / SAO: t1 bad target: no reuse computed (dbt-orchestra `dbt ls` errored); t2 parse fail: no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Runtime Error: no target demo_target_does_not_exist (dbt ls, freshness, build); no nodes ran; exit 2 Compilation Error stg_demo_events DEMO_FAIL[parse]; no nodes ran | [94631f5b](https://app.getorchestra.io/incidents/94631f5b-2702-4678-a26a-ce6d131b9a66)<br>[56886030](https://app.getorchestra.io/incidents/56886030-a1d4-4157-8a29-166ae827766a) | new<br>new | 1 (TASK event (TASK))<br>1 (TASK event (TASK)) | no<br>no | no (alertThreads empty)<br>no (alertThreads empty) | no (manually resolved at 13:12)<br>no (manually resolved at 13:12) |
| [R2 f296936a](https://app.getorchestra.io/pipeline-runs/f296936a-0ab6-4d5f-b841-7e5a7bf7cc61/lineage) | demo-dbt-fail-11-two-task-level-sao | {"t1_args": "--threads 1", "t2_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (3a4a6aca, 13:01:37)<br>t1 bad target: SUCCEEDED (79cf14e9, 13:03:40)<br>t2 parse fail: SUCCEEDED (2025b6d9, 13:03:33) | PASS 12 / SAO: t1 bad target: REUSED 0; t2 parse fail: REUSED 0 | - | - | - | - | - | - | - |

- t1 + t2 task-level failures in one run -> TWO incidents (94631f5b t1, 56886030 t2).
- R2 green 13:03:40, i.e. after the 13:00:21 auto-resolve sweep; manual resolve 13:12:42.

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 c726b543](https://app.getorchestra.io/pipeline-runs/c726b543-0fde-45bd-9784-f5c005ee0099/lineage) | demo-dbt-fail-11-two-task-level-nsao | {"t1_args": "--threads 1", "t2_args": "--threads 1"} | SUCCEEDED | t1 bad target: SUCCEEDED (f914e247, 11:35:12)<br>t2 parse fail: SUCCEEDED (e2226894, 11:35:04) | PASS 12 | - | - | - | - | - | - | - |
| [R1 f9c1fed4](https://app.getorchestra.io/pipeline-runs/f9c1fed4-efb5-4dbc-b3e0-224f6eec8167/lineage) | demo-dbt-fail-11-two-task-level-nsao | {} (defaults = failure) | FAILED | t1 bad target: FAILED (b245902a, 11:37:20)<br>t2 parse fail: FAILED (1028361e, 11:37:27) | no nodes ran | exit 2 Runtime Error: profile has no target demo_target_does_not_exist (no models ran); exit 2 Compilation Error in model stg_demo_events DEMO_FAIL[parse] (no models ran) | [e4510bb9](https://app.getorchestra.io/incidents/e4510bb9-5a09-459c-9fa2-b0ab90ee4071)<br>[5b41973a](https://app.getorchestra.io/incidents/5b41973a-6618-4df5-80a9-48ac8e5cb035) | new<br>new | 1 (TASK event (TASK))<br>1 (TASK event (TASK)) | no<br>no | no (alertThreads empty)<br>no (alertThreads empty) | no (manually resolved at 11:45)<br>no (manually resolved at 11:45) |
| [R2 217b29a6](https://app.getorchestra.io/pipeline-runs/217b29a6-cbdf-4097-a13b-4254bc2c7a7a/lineage) | demo-dbt-fail-11-two-task-level-nsao | {"t1_args": "--threads 1", "t2_args": "--threads 1"} | SUCCEEDED | t1 bad target: SUCCEEDED (aa181d3c, 11:39:48)<br>t2 parse fail: SUCCEEDED (ed031969, 11:39:54) | PASS 12 | - | - | - | - | - | - | - |

- Two parallel task-level failures (t1 bad target, t2 parse fail) in one run -> TWO incidents, one per task, named '<task> failed in <pipeline>'.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 d42b94c6](https://app.getorchestra.io/pipeline-runs/d42b94c6-6486-4d89-a79b-e096a46b17d2/lineage) | demo-dbt-fail-11-two-task-level-both | {"t1_args": "--threads 1", "t2_args": "--threads 1"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (2ea3e790, 13:44:00)<br>t1 bad target: SUCCEEDED (b29b3d55, 13:45:45)<br>t2 parse fail: SUCCEEDED (536a8acc, 13:45:45) | t1 bad target: PASS 9<br>t2 parse fail: PASS 3 / SAO: t1 bad target: REUSED 0 | - | - | - | - | - | - | - |
| [R1 9e3b006b](https://app.getorchestra.io/pipeline-runs/9e3b006b-8390-4d64-9ccb-5b603a681111/lineage) | demo-dbt-fail-11-two-task-level-both | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (993daa32, 13:50:02)<br>t1 bad target: FAILED (5d945c1e, 13:51:22)<br>t2 parse fail: FAILED (bcdf2054, 13:51:35) | t1 bad target: FAILED exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran<br>t2 parse fail: FAILED exit 2 Compilation Error stg_demo_events DEMO_FAIL[parse]; no nodes ran / SAO: t1 bad target: no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran; exit 2 Compilation Error stg_demo_events DEMO_FAIL[parse]; no nodes ran | [6a7ac231](https://app.getorchestra.io/incidents/6a7ac231-ea1c-41da-a780-d638c07829c8)<br>[0fad46fe](https://app.getorchestra.io/incidents/0fad46fe-452f-4006-bc43-f40cf056bcc0) | new<br>new | 1 (TASK event (TASK))<br>1 (TASK event (TASK)) | no<br>no | no (alertThreads empty)<br>no (alertThreads empty) | no (manually resolved at 14:04)<br>no (manually resolved at 14:04) |
| [R2 eb695b08](https://app.getorchestra.io/pipeline-runs/eb695b08-fd2c-49be-b449-186cbe868c06/lineage) | demo-dbt-fail-11-two-task-level-both | {"t1_args": "--threads 1", "t2_args": "--threads 1"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (e1ff5b9d, 13:54:04)<br>t1 bad target: SUCCEEDED (6e9156e4, 13:56:10)<br>t2 parse fail: SUCCEEDED (08b0651a, 13:55:35) | t1 bad target: PASS 9<br>t2 parse fail: PASS 3 / SAO: t1 bad target: REUSED 0 | - | - | - | - | - | - | - |

- t1 (SAO) + t2 (non-SAO) in parallel after touch, both failed -> TWO incidents (6a7ac231 t1, 0fad46fe t2).

### 12 task-level-2-pipes

#### sao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 911ba3b8](https://app.getorchestra.io/pipeline-runs/911ba3b8-f78d-4660-84c1-021c63fea5e7/lineage) | demo-dbt-fail-12-task-level-2-pipes-sao-a | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (3591d94f, 13:05:42)<br>dbt build (SAO): SUCCEEDED (b3c40f30, 13:07:55) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R0 88585e74](https://app.getorchestra.io/pipeline-runs/88585e74-e331-4f23-a7c2-ecec184767ea/lineage) | demo-dbt-fail-12-task-level-2-pipes-sao-b | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (885deaf3, 13:10:28)<br>dbt build (SAO): SUCCEEDED (61839acd, 13:12:19) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R1 73d266a7](https://app.getorchestra.io/pipeline-runs/73d266a7-7090-4b91-ae12-02c9f063084c/lineage) | demo-dbt-fail-12-task-level-2-pipes-sao-a | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (0116ed37, 13:14:23)<br>dbt build (SAO): FAILED (42b69bdc, 13:15:41) | no nodes ran / SAO: no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Runtime Error: no target demo_target_does_not_exist (dbt ls, freshness, build); no nodes ran | [c43aba9b](https://app.getorchestra.io/incidents/c43aba9b-4055-4478-a8fe-ea67d9f63225) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (still open) |
| [R1 e87c82c6](https://app.getorchestra.io/pipeline-runs/e87c82c6-960f-4633-ad5d-7d06b47e107f/lineage) | demo-dbt-fail-12-task-level-2-pipes-sao-b | {} (defaults = failure)<br>touch: `demo_touch_source` | FAILED | Touch source: SUCCEEDED (7bbbad93, 13:14:06)<br>dbt build (SAO): FAILED (5414738a, 13:15:35) | no nodes ran / SAO: no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Runtime Error: no target demo_target_does_not_exist (dbt ls, freshness, build); no nodes ran | [ba87d083](https://app.getorchestra.io/incidents/ba87d083-3a7e-4b83-8dea-6a38be943493) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (still open) |
| [R2 355522d2](https://app.getorchestra.io/pipeline-runs/355522d2-1de8-403a-8690-249b16b9c8ec/lineage) | demo-dbt-fail-12-task-level-2-pipes-sao-a | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (8dd74d51, 13:18:29)<br>dbt build (SAO): SUCCEEDED (3c87c0d0, 13:20:33) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |
| [R2 3d533e46](https://app.getorchestra.io/pipeline-runs/3d533e46-790b-42e7-8956-2a1b73e70d1d/lineage) | demo-dbt-fail-12-task-level-2-pipes-sao-b | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source` | SUCCEEDED | Touch source: SUCCEEDED (e57a2f62, 13:23:48)<br>dbt build (SAO): SUCCEEDED (f9170405, 13:25:38) | PASS 11 / SAO: REUSED 0 | - | - | - | - | - | - | - |

- Bad target in pipes a and b (started together) -> TWO incidents (c43aba9b a, ba87d083 b), 1 TASK event each.
- R2 green 13:20:33 / 13:25:38; both still OPEN at collection time (13:3x).

#### nsao

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 5ef1e988](https://app.getorchestra.io/pipeline-runs/5ef1e988-f2bf-44d3-a1fc-391f1851f3d0/lineage) | demo-dbt-fail-12-task-level-2-pipes-nsao-a | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (0a1cc2dc, 11:42:11) | PASS 11 | - | - | - | - | - | - | - |
| [R0 a8d681bc](https://app.getorchestra.io/pipeline-runs/a8d681bc-10db-4761-a670-48b18246dfcf/lineage) | demo-dbt-fail-12-task-level-2-pipes-nsao-b | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (827f3e71, 11:44:52) | PASS 11 | - | - | - | - | - | - | - |
| [R1 9ff10d90](https://app.getorchestra.io/pipeline-runs/9ff10d90-5cd2-491f-8061-b0f71a6e3846/lineage) | demo-dbt-fail-12-task-level-2-pipes-nsao-a | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (fbbf264b, 11:46:52) | no nodes ran | exit 2 Runtime Error: profile has no target demo_target_does_not_exist (no models ran) | [3b22e633](https://app.getorchestra.io/incidents/3b22e633-295c-465a-918d-c63a8cadf1ac) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | yes (SYSTEM at 13:00) |
| [R1 21996af1](https://app.getorchestra.io/pipeline-runs/21996af1-3620-4b84-9226-87b406b67258/lineage) | demo-dbt-fail-12-task-level-2-pipes-nsao-b | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (53703bec, 11:46:51) | no nodes ran | exit 2 Runtime Error: profile has no target demo_target_does_not_exist (no models ran) | [01615194](https://app.getorchestra.io/incidents/01615194-15df-497a-b36e-a65f2a36c638) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | yes (SYSTEM at 13:00) |
| [R2 2838e2d4](https://app.getorchestra.io/pipeline-runs/2838e2d4-4f79-48f0-b1c8-cd3b4f0dc248/lineage) | demo-dbt-fail-12-task-level-2-pipes-nsao-a | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (7f872761, 11:49:32) | PASS 11 | - | - | - | - | - | - | - |
| [R2 d61fe0ce](https://app.getorchestra.io/pipeline-runs/d61fe0ce-39fb-4987-8e7e-93e353c4b3d1/lineage) | demo-dbt-fail-12-task-level-2-pipes-nsao-b | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (58a0a26a, 11:51:52) | PASS 11 | - | - | - | - | - | - | - |

- Same task-level failure (bad target) in two pipelines started together -> TWO incidents (01615194 pipe b, 3b22e633 pipe a), each 1 TASK event.
- Both R2 green (11:49:32, 11:51:52); both incidents left untouched and RESOLVED by SYSTEM at 13:00:21 (~70 min after recovery) - the only SYSTEM auto-resolves in this lane.

#### both

| run | pipeline | inputs | run status | task statuses | models ERROR / SKIPPED / PASS | failure detail | incident(s) | new vs appended | events on incident from this run | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| [R0 a73e731c](https://app.getorchestra.io/pipeline-runs/a73e731c-7781-4ee5-ac3b-9dc44dc8093c/lineage) | demo-dbt-fail-12-task-level-2-pipes-both-a | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (ae5db7be, 13:58:06)<br>dbt build (SAO): SUCCEEDED (1fafefb8, 14:00:10) | dbt build (SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R0 c076a377](https://app.getorchestra.io/pipeline-runs/c076a377-2440-4a2e-8b55-57a2c3dfbec4/lineage) | demo-dbt-fail-12-task-level-2-pipes-both-b | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (e8b6377d, 14:03:29) | dbt build (non-SAO): PASS 11 | - | - | - | - | - | - | - |
| [R1 66503325](https://app.getorchestra.io/pipeline-runs/66503325-a1d6-46fc-a4d7-65fbf367f764/lineage) | demo-dbt-fail-12-task-level-2-pipes-both-a | {} (defaults = failure)<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | FAILED | Touch source: SUCCEEDED (74b78ebb, 14:05:47)<br>dbt build (SAO): FAILED (cd59d6f2, 14:07:17) | dbt build (SAO): FAILED exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran / SAO: dbt build (SAO): no reuse computed (dbt-orchestra `dbt ls` errored) | exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran | [e1f346bb](https://app.getorchestra.io/incidents/e1f346bb-0a1c-4d85-a214-b92c78c8b523) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (still open) |
| [R1 2d5bb70b](https://app.getorchestra.io/pipeline-runs/2d5bb70b-b097-437b-8a3c-0a2a150a1f27/lineage) | demo-dbt-fail-12-task-level-2-pipes-both-b | {} (defaults = failure) | FAILED | dbt build (non-SAO): FAILED (df5589f9, 14:05:37) | dbt build (non-SAO): FAILED exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran | exit 2 Runtime Error: no target demo_target_does_not_exist; no nodes ran | [cd9eeb23](https://app.getorchestra.io/incidents/cd9eeb23-90af-4961-9ae3-df392c2a430f) | new | 1 (TASK event (TASK)) | no | no (alertThreads empty) | no (still open) |
| [R2 d055e910](https://app.getorchestra.io/pipeline-runs/d055e910-c967-4b45-94ba-b1ff5c560d2d/lineage) | demo-dbt-fail-12-task-level-2-pipes-both-a | {"demo_args": "--threads 1"}<br>touch: `demo_touch_source --vars "{demo_lane: both}"` | SUCCEEDED | Touch source: SUCCEEDED (b1bac1ac, 14:09:23)<br>dbt build (SAO): SUCCEEDED (18d18434, 14:11:31) | dbt build (SAO): PASS 11 / SAO: dbt build (SAO): REUSED 0 | - | - | - | - | - | - | - |
| [R2 7cebc96f](https://app.getorchestra.io/pipeline-runs/7cebc96f-69f9-4596-ab70-ad83208a8d35/lineage) | demo-dbt-fail-12-task-level-2-pipes-both-b | {"demo_args": "--threads 1"} | SUCCEEDED | dbt build (non-SAO): SUCCEEDED (4de9af7c, 14:14:20) | dbt build (non-SAO): PASS 11 | - | - | - | - | - | - | - |

- Bad target in pipe a (SAO) and pipe b (non-SAO) -> TWO incidents (e1f346bb a, cd9eeb23 b), 1 TASK event each.
- R2 green 14:11:31 / 14:14:20; both still OPEN at collection (~14:20).

## Incidents index (all 53)

| incident | lane | scn | name | runs (label) | assets | tasks | events | created | resolved | by |
|---|---|---|---|---|---|---|---|---|---|---|
| [086e5f7f](https://app.getorchestra.io/incidents/086e5f7f-b5e8-41ba-ba6b-397a5157b40f) | nsao | 01 | int_demo_orders failed in demo-dbt-fail-01-single-mid-nsao | [fc931740](https://app.getorchestra.io/pipeline-runs/fc931740-b523-4137-b1fd-89603e293674/lineage) R1 | int_demo_orders | dbt build (non-SAO) | 5 | 09:56:28 | 10:03:20 | API |
| [e270dc68](https://app.getorchestra.io/incidents/e270dc68-9795-4a51-95f5-b24dfce99929) | both | 01 | int_demo_orders failed in demo-dbt-fail-01-single-mid-both | [4b620dff](https://app.getorchestra.io/pipeline-runs/4b620dff-7ee8-4cee-835d-d16886ffc2af/lineage) R1 | int_demo_orders | dbt build (SAO), dbt build (non-SAO) | 7 | 10:00:16 | 10:17:40 | API |
| [e37a088b](https://app.getorchestra.io/incidents/e37a088b-048d-444f-8352-7025bc2435e4) | sao | 01 | int_demo_orders failed in demo-dbt-fail-01-single-mid-sao | [f9d5b6f6](https://app.getorchestra.io/pipeline-runs/f9d5b6f6-2cff-4576-bbc3-77da2958f5ec/lineage) R1 | int_demo_orders | dbt build (SAO) | 5 | 10:00:31 | 10:14:46 | API |
| [d936cb8e](https://app.getorchestra.io/incidents/d936cb8e-91e6-463a-bc46-45fdacdbba73) | nsao | 02 | int_demo_orders failed | [d69019c4](https://app.getorchestra.io/pipeline-runs/d69019c4-2db8-4c91-b9e0-643a1f4ff9ad/lineage) R1<br>[6f097457](https://app.getorchestra.io/pipeline-runs/6f097457-2eac-4b86-a3af-7d50ee54cf7f/lineage) R2-fail+noop | int_demo_orders | dbt build (non-SAO) | 6 | 10:05:18 | 10:17:40 | API |
| [5e771fd6](https://app.getorchestra.io/incidents/5e771fd6-98a6-48e9-8045-b39f87c32ae7) | sao | 02 | int_demo_orders failed in demo-dbt-fail-02-sao-skip-next-sao | [f4441cc8](https://app.getorchestra.io/pipeline-runs/f4441cc8-2936-4d4f-bc08-e308d3af3b53/lineage) R1<br>[af6274a8](https://app.getorchestra.io/pipeline-runs/af6274a8-4596-4269-b2b3-14aedc6c2bb3/lineage) R2-fail+noop | int_demo_orders | dbt build (SAO) | 6 | 10:18:45 | 10:40:41 | API |
| [cf5a2de2](https://app.getorchestra.io/incidents/cf5a2de2-e1c8-456d-bb48-b38726390b44) | nsao | 03 | dbt build (non-SAO) failed in demo-dbt-fail-03-two-mid-nsao | [885469e3](https://app.getorchestra.io/pipeline-runs/885469e3-8536-4c81-9f29-8c5780de3ef0/lineage) R1 | int_demo_orders, side_demo_sessions | dbt build (non-SAO) | 6 | 10:19:38 | 10:25:08 | API |
| [61acb9da](https://app.getorchestra.io/incidents/61acb9da-8739-44a9-8c9c-7aacf065f91c) | both | 02 | int_demo_orders failed | [8c1e2b87](https://app.getorchestra.io/pipeline-runs/8c1e2b87-050b-454a-8dbf-647bc9496618/lineage) R1<br>[6bb8529a](https://app.getorchestra.io/pipeline-runs/6bb8529a-7f42-436b-aa0c-579723b38f09/lineage) R2-fail+noop | int_demo_orders | dbt build (SAO), dbt build (non-SAO) | 8 | 10:21:17 | 10:53:23 | API |
| [3819f488](https://app.getorchestra.io/incidents/3819f488-1714-4760-98de-7949c1b8df42) | nsao | 04 | dbt build (non-SAO) failed in demo-dbt-fail-04-two-seq-nsao | [be8f9485](https://app.getorchestra.io/pipeline-runs/be8f9485-e951-4342-b073-84c8e2ecf520/lineage) R1 | int_demo_orders, int_demo_orders_enriched | dbt build (non-SAO) | 8 | 10:26:55 | 10:35:23 | API |
| [b9dda6c6](https://app.getorchestra.io/incidents/b9dda6c6-ae5e-435e-ba6a-6c190ae7a20d) | nsao | 06 | int_demo_orders failed | [495ff467](https://app.getorchestra.io/pipeline-runs/495ff467-2ae4-4adc-9865-63da3a900539/lineage) R1<br>[224bbe2f](https://app.getorchestra.io/pipeline-runs/224bbe2f-faab-4d4c-adc7-c9d8897b66c3/lineage) R1 | int_demo_orders | dbt build (non-SAO) | 7 | 10:37:16 | 10:48:16 | API |
| [28d2e05b](https://app.getorchestra.io/incidents/28d2e05b-4b34-4e86-9224-30b60cf16948) | sao | 03 | dbt build (SAO) failed in demo-dbt-fail-03-two-mid-sao | [38ab8ba6](https://app.getorchestra.io/pipeline-runs/38ab8ba6-45bd-4d39-bfe4-89c789e43408/lineage) R1 | int_demo_orders, side_demo_sessions | dbt build (SAO) | 6 | 10:44:02 | 10:56:00 | API |
| [9290bc20](https://app.getorchestra.io/incidents/9290bc20-6334-4f89-9c95-84abc4113dae) | nsao | 07 | dbt build (non-SAO) failed | [b5e62115](https://app.getorchestra.io/pipeline-runs/b5e62115-d306-4d38-b65d-11e63e1a513a/lineage) R1 | fp_demo_alpha, fp_demo_beta | dbt build (non-SAO) | 6 | 10:50:20 | 10:58:39 | API |
| [60df5f6e](https://app.getorchestra.io/incidents/60df5f6e-2196-44da-8ac4-e4d53537e8ae) | both | 03 | dbt build (SAO) failed in demo-dbt-fail-03-two-mid-both | [2ba3b00a](https://app.getorchestra.io/pipeline-runs/2ba3b00a-6ff1-4b3b-bb15-96e3de8c6633/lineage) R1 | int_demo_orders, side_demo_sessions | dbt build (SAO), dbt build (non-SAO) | 8 | 10:56:53 | 11:14:03 | API |
| [83926422](https://app.getorchestra.io/incidents/83926422-5a3a-4b82-afed-895d3409e580) | sao | 04 | dbt build (SAO) failed in demo-dbt-fail-04-two-seq-sao | [05b4acb1](https://app.getorchestra.io/pipeline-runs/05b4acb1-5246-41e4-a634-c1c566bb2f44/lineage) R1 | int_demo_orders, int_demo_orders_enriched | dbt build (SAO) | 8 | 10:59:58 | 11:16:31 | API |
| [e5d6984e](https://app.getorchestra.io/incidents/e5d6984e-988f-4429-b064-784983c693b6) | nsao | 08 | dbt build (non-SAO) failed | [e7ac054c](https://app.getorchestra.io/pipeline-runs/e7ac054c-a1cf-4812-892e-bc754353e2de/lineage) R1 | — | dbt build (non-SAO) | 5 | 11:00:14 | 11:09:09 | API |
| [0e19c2e8](https://app.getorchestra.io/incidents/0e19c2e8-1700-4aa8-bfbb-27103598e2b2) | nsao | 08 | dbt build (non-SAO) failed | [3e34c92a](https://app.getorchestra.io/pipeline-runs/3e34c92a-bcf8-441a-a241-5701e6ba37d0/lineage) R1 | — | dbt build (non-SAO) | 5 | 11:00:37 | 11:09:10 | API |
| [cb69f3ba](https://app.getorchestra.io/incidents/cb69f3ba-9509-41a9-88c0-47237601a9f6) | nsao | 08b | dbt build (non-SAO) failed in demo-dbt-fail-08b-runop-nsao | [d2cdc543](https://app.getorchestra.io/pipeline-runs/d2cdc543-6697-4eab-bd6e-5895f24785d7/lineage) R1 | — | dbt build (non-SAO) | 5 | 11:10:44 | 11:16:31 | API |
| [2d053a88](https://app.getorchestra.io/incidents/2d053a88-2422-4540-8dac-67f9f8f990e1) | both | 04 | dbt build (SAO) failed in demo-dbt-fail-04-two-seq-both | [b192e23a](https://app.getorchestra.io/pipeline-runs/b192e23a-897f-4980-a10b-a2d0954000e9/lineage) R1 | int_demo_orders, int_demo_orders_enriched | dbt build (SAO), dbt build (non-SAO) | 8 | 11:17:52 | 11:35:42 | API |
| [96166a78](https://app.getorchestra.io/incidents/96166a78-b259-4a93-a257-066caa2d704c) | nsao | 09 | dbt build (non-SAO) failed | [09589e0b](https://app.getorchestra.io/pipeline-runs/09589e0b-a58c-4aa8-8824-21b7b0db25e6/lineage) R1 | stg_demo_events, stg_demo_users, fp_demo_alpha, fp_demo_beta, side_demo_sessions, int_demo_orders, int_demo_orders_enriched, mart_demo_summary | dbt build (non-SAO) | 12 | 11:18:29 | 11:23:44 | API |
| [9d4eefe5](https://app.getorchestra.io/incidents/9d4eefe5-c96c-4d39-b5e0-09d6606d92ea) | sao | 06 | int_demo_orders failed | [b912539e](https://app.getorchestra.io/pipeline-runs/b912539e-28fc-427b-af53-f5a7c0100bbf/lineage) R1<br>[330dfe68](https://app.getorchestra.io/pipeline-runs/330dfe68-3909-48b2-be00-8cddef6e4497/lineage) R1 | int_demo_orders | dbt build (SAO) | 7 | 11:19:56 | 11:40:27 | API |
| [25afae93](https://app.getorchestra.io/incidents/25afae93-5355-4216-8f49-6f1803f7f86e) | nsao | 10 | dbt build (non-SAO) failed | [2c1eaff3](https://app.getorchestra.io/pipeline-runs/2c1eaff3-a45d-443a-8f46-78eb988fa040/lineage) R1a-bad-target<br>[74628c96](https://app.getorchestra.io/pipeline-runs/74628c96-a4fa-474c-87c3-417039562061/lineage) R1b-parse-fail<br>[f64ed4d9](https://app.getorchestra.io/pipeline-runs/f64ed4d9-6064-483b-9598-0c00cccedba1/lineage) R1c-bad-flag | — | dbt build (non-SAO) | 11 | 11:25:25 | 11:35:42 | API |
| [e4510bb9](https://app.getorchestra.io/incidents/e4510bb9-5a09-459c-9fa2-b0ab90ee4071) | nsao | 11 | t1 bad target failed in demo-dbt-fail-11-two-task-level-nsao | [f9c1fed4](https://app.getorchestra.io/pipeline-runs/f9c1fed4-efb5-4dbc-b3e0-224f6eec8167/lineage) R1 | — | t1 bad target | 5 | 11:37:31 | 11:45:21 | API |
| [5b41973a](https://app.getorchestra.io/incidents/5b41973a-6618-4df5-80a9-48ac8e5cb035) | nsao | 11 | t2 parse fail failed in demo-dbt-fail-11-two-task-level-nsao | [f9c1fed4](https://app.getorchestra.io/pipeline-runs/f9c1fed4-efb5-4dbc-b3e0-224f6eec8167/lineage) R1 | — | t2 parse fail | 5 | 11:37:36 | 11:45:21 | API |
| [b4ae9081](https://app.getorchestra.io/incidents/b4ae9081-6335-4c52-b9c7-219621535006) | both | 05 | int_demo_orders failed | [b9e6900c](https://app.getorchestra.io/pipeline-runs/b9e6900c-6f59-4c64-b671-6276f94c9db0/lineage) R1 | int_demo_orders | dbt build (SAO), dbt build (non-SAO) | 6 | 11:39:08 | 11:57:24 | API |
| [960f6d25](https://app.getorchestra.io/incidents/960f6d25-7cd3-4ce4-ba99-39005a9d2467) | sao | 07 | dbt build (SAO) failed in demo-dbt-fail-07-same-folder-sao | [b55b112a](https://app.getorchestra.io/pipeline-runs/b55b112a-5867-4672-b0d5-9a84c3971eb6/lineage) R1 | fp_demo_alpha, fp_demo_beta | dbt build (SAO) | 6 | 11:44:17 | 11:59:38 | API |
| [01615194](https://app.getorchestra.io/incidents/01615194-15df-497a-b36e-a65f2a36c638) | nsao | 12 | dbt build (non-SAO) failed | [21996af1](https://app.getorchestra.io/pipeline-runs/21996af1-3620-4b84-9226-87b406b67258/lineage) R1 | — | dbt build (non-SAO) | 4 | 11:47:03 | 13:00:21 | SYSTEM |
| [3b22e633](https://app.getorchestra.io/incidents/3b22e633-295c-465a-918d-c63a8cadf1ac) | nsao | 12 | dbt build (non-SAO) failed | [9ff10d90](https://app.getorchestra.io/pipeline-runs/9ff10d90-5cd2-491f-8061-b0f71a6e3846/lineage) R1 | — | dbt build (non-SAO) | 4 | 11:47:04 | 13:00:21 | SYSTEM |
| [6a62989a](https://app.getorchestra.io/incidents/6a62989a-40c7-463c-ac99-3642e7c0ae42) | both | 06 | int_demo_orders failed | [6e974056](https://app.getorchestra.io/pipeline-runs/6e974056-e2dd-4959-b8bd-fd66ed21ab36/lineage) R1<br>[d4c5d151](https://app.getorchestra.io/pipeline-runs/d4c5d151-5865-449f-993c-eb7dc54cee7c/lineage) R1 | int_demo_orders | dbt build (SAO), dbt build (non-SAO) | 6 | 12:01:18 | 12:19:28 | API |
| [3021c3fa](https://app.getorchestra.io/incidents/3021c3fa-de88-4a13-81e9-96987ad8489c) | sao | 08 | dbt build (SAO) failed | [6440ce05](https://app.getorchestra.io/pipeline-runs/6440ce05-cc14-4b97-acd2-147ade358e72/lineage) R1 | — | dbt build (SAO) | 5 | 12:03:01 | 12:16:43 | API |
| [ca0f1b80](https://app.getorchestra.io/incidents/ca0f1b80-1b2a-48b1-9908-9c0c7c2b932a) | sao | 08 | dbt build (SAO) failed | [37ae7053](https://app.getorchestra.io/pipeline-runs/37ae7053-23d0-4864-a7f9-a889ecc07b85/lineage) R1 | — | dbt build (SAO) | 5 | 12:03:36 | 12:16:43 | API |
| [2ad5b796](https://app.getorchestra.io/incidents/2ad5b796-16ea-4281-a375-e64f33ace94f) | sao | 09 | dbt build (SAO) failed in demo-dbt-fail-09-all-models-sao | [ef0ad9ef](https://app.getorchestra.io/pipeline-runs/ef0ad9ef-fa76-42bd-8da0-382d1fc05275/lineage) R1 | stg_demo_events, stg_demo_users, fp_demo_alpha, fp_demo_beta, side_demo_sessions, int_demo_orders, int_demo_orders_enriched, mart_demo_summary | dbt build (SAO) | 12 | 12:20:15 | 12:32:32 | API |
| [e389362c](https://app.getorchestra.io/incidents/e389362c-48fc-44b9-ab2d-b4445815fbb6) | both | 07 | dbt build (SAO) failed in demo-dbt-fail-07-same-folder-both | [1eed691c](https://app.getorchestra.io/pipeline-runs/1eed691c-c859-4d06-aaf2-0f4404143f36/lineage) R1 | fp_demo_alpha, fp_demo_beta | dbt build (SAO), dbt build (non-SAO) | 8 | 12:23:44 | 12:41:23 | API |
| [a8898216](https://app.getorchestra.io/incidents/a8898216-6462-4033-a6fa-cfd8b050f955) | sao | 10 | dbt build (SAO) failed in demo-dbt-fail-10-task-level-sao | [30f186ad](https://app.getorchestra.io/pipeline-runs/30f186ad-ab17-446d-bb73-832bc0ea6c49/lineage) R1a-bad-target | — | dbt build (SAO) | 5 | 12:35:41 | 12:54:57 | API |
| [082b13ac](https://app.getorchestra.io/incidents/082b13ac-2b4e-4f33-9786-61467eb1ca24) | sao | 10 | dbt build (SAO) failed in demo-dbt-fail-10-task-level-sao | [8ae01a99](https://app.getorchestra.io/pipeline-runs/8ae01a99-15df-4e0e-b495-46cbf30fe508/lineage) R1b-parse-fail | — | dbt build (SAO) | 5 | 12:39:08 | 12:54:57 | API |
| [dac7d0f6](https://app.getorchestra.io/incidents/dac7d0f6-2eac-4f93-9cca-5c12c8b62174) | both | 08 | dbt build (non-SAO) failed | [f59fc28d](https://app.getorchestra.io/pipeline-runs/f59fc28d-8526-44e3-abd6-310356657250/lineage) R1 | — | dbt build (non-SAO) | 5 | 12:43:02 | 12:59:51 | API |
| [feb1bde6](https://app.getorchestra.io/incidents/feb1bde6-45fa-4fb6-b00d-6ca037c6ef9e) | both | 08 | dbt build (SAO) failed | [daf6075f](https://app.getorchestra.io/pipeline-runs/daf6075f-b3da-4320-ac0a-8ec1609b88f6/lineage) R1 | — | dbt build (SAO) | 5 | 12:44:48 | 12:59:51 | API |
| [229ce387](https://app.getorchestra.io/incidents/229ce387-1617-4b45-83ba-56a992f3e316) | sao | 10 | dbt build (SAO) failed in demo-dbt-fail-10-task-level-sao | [4504aac3](https://app.getorchestra.io/pipeline-runs/4504aac3-c067-40aa-bb56-77f65bc3642e/lineage) R1c-bad-flag | — | dbt build (SAO) | 5 | 12:44:54 | 12:54:58 | API |
| [94631f5b](https://app.getorchestra.io/incidents/94631f5b-2702-4678-a26a-ce6d131b9a66) | sao | 11 | t1 bad target failed in demo-dbt-fail-11-two-task-level-sao | [ea60c279](https://app.getorchestra.io/pipeline-runs/ea60c279-a807-4555-bf21-4a98e6171ceb/lineage) R1 | — | t1 bad target | 5 | 12:58:15 | 13:12:42 | API |
| [56886030](https://app.getorchestra.io/incidents/56886030-a1d4-4157-8a29-166ae827766a) | sao | 11 | t2 parse fail failed in demo-dbt-fail-11-two-task-level-sao | [ea60c279](https://app.getorchestra.io/pipeline-runs/ea60c279-a807-4555-bf21-4a98e6171ceb/lineage) R1 | — | t2 parse fail | 5 | 12:58:31 | 13:12:42 | API |
| [f6405f68](https://app.getorchestra.io/incidents/f6405f68-7aa2-4f39-b3b5-573db014a742) | both | 09 | dbt build (SAO) failed in demo-dbt-fail-09-all-models-both | [0d337df1](https://app.getorchestra.io/pipeline-runs/0d337df1-b99d-4814-ba5f-8b3294f2d7f4/lineage) R1 | fp_demo_alpha, fp_demo_beta, int_demo_orders, int_demo_orders_enriched, mart_demo_summary, side_demo_sessions, stg_demo_events, stg_demo_users | dbt build (SAO), dbt build (non-SAO) | 22 | 13:02:55 | 13:19:25 | API |
| [ba87d083](https://app.getorchestra.io/incidents/ba87d083-3a7e-4b83-8dea-6a38be943493) | sao | 12 | dbt build (SAO) failed | [e87c82c6](https://app.getorchestra.io/pipeline-runs/e87c82c6-960f-4633-ad5d-7d06b47e107f/lineage) R1 | — | dbt build (SAO) | 4 | 13:15:46 | OPEN |  |
| [c43aba9b](https://app.getorchestra.io/incidents/c43aba9b-4055-4478-a8fe-ea67d9f63225) | sao | 12 | dbt build (SAO) failed | [73d266a7](https://app.getorchestra.io/pipeline-runs/73d266a7-7090-4b91-ae12-02c9f063084c/lineage) R1 | — | dbt build (SAO) | 4 | 13:15:53 | OPEN |  |
| [81156110](https://app.getorchestra.io/incidents/81156110-766a-4f46-b484-d5c9acc471b2) | both | 10 | dbt build (SAO) failed in demo-dbt-fail-10-task-level-both | [74d909c7](https://app.getorchestra.io/pipeline-runs/74d909c7-fc88-4111-a3e9-a545dca91644/lineage) R1a-bad-target | — | dbt build (SAO) | 5 | 13:22:23 | 13:48:29 | API |
| [80fec7f1](https://app.getorchestra.io/incidents/80fec7f1-d87a-4722-a852-cc31f902ba5e) | both | 10 | dbt build (non-SAO) failed | [74d909c7](https://app.getorchestra.io/pipeline-runs/74d909c7-fc88-4111-a3e9-a545dca91644/lineage) R1a-bad-target | — | dbt build (non-SAO) | 5 | 13:23:41 | 13:48:29 | API |
| [026486e9](https://app.getorchestra.io/incidents/026486e9-d1cb-4b55-a349-5467b258a8e8) | both | 10 | dbt build (SAO) failed in demo-dbt-fail-10-task-level-both | [39607037](https://app.getorchestra.io/pipeline-runs/39607037-45fa-4d56-94cb-c7bc672f908d/lineage) R1b-parse-fail | — | dbt build (SAO) | 5 | 13:29:00 | 13:48:29 | API |
| [774560cb](https://app.getorchestra.io/incidents/774560cb-8326-48cf-98a2-7a1c051d6d32) | both | 10 | dbt build (non-SAO) failed | [39607037](https://app.getorchestra.io/pipeline-runs/39607037-45fa-4d56-94cb-c7bc672f908d/lineage) R1b-parse-fail | — | dbt build (non-SAO) | 5 | 13:30:36 | 13:48:30 | API |
| [32567d4f](https://app.getorchestra.io/incidents/32567d4f-0b20-44ef-ae24-df8f17502e96) | both | 10 | dbt build (SAO) failed in demo-dbt-fail-10-task-level-both | [c1237842](https://app.getorchestra.io/pipeline-runs/c1237842-f1c0-499d-ae56-c2ffb3d409af/lineage) R1c-bad-flag | — | dbt build (SAO) | 5 | 13:34:09 | 13:48:30 | API |
| [9676eb7e](https://app.getorchestra.io/incidents/9676eb7e-137b-4462-b1bc-3836728083d6) | both | 10 | dbt build (non-SAO) failed | [c1237842](https://app.getorchestra.io/pipeline-runs/c1237842-f1c0-499d-ae56-c2ffb3d409af/lineage) R1c-bad-flag | — | dbt build (non-SAO) | 5 | 13:35:32 | 13:48:30 | API |
| [c57dd264](https://app.getorchestra.io/incidents/c57dd264-d0cc-4c46-a373-9d9a6e5c80ca) | nsao | 10x | dbt build (non-SAO) failed | [384a029a](https://app.getorchestra.io/pipeline-runs/384a029a-bb91-4a8c-9d9c-3251785e7603/lineage) X1-bad-target | — | dbt build (non-SAO) | 4 | 13:37:01 | OPEN |  |
| [8cba8ed3](https://app.getorchestra.io/incidents/8cba8ed3-e812-4b31-89cf-69c02b5732ad) | nsao | 10x | dbt build (non-SAO) failed | [ccfcbf5b](https://app.getorchestra.io/pipeline-runs/ccfcbf5b-e1be-4355-8e6c-c718a901a1e7/lineage) X2-parse-fail | — | dbt build (non-SAO) | 4 | 13:43:51 | OPEN |  |
| [6a7ac231](https://app.getorchestra.io/incidents/6a7ac231-ea1c-41da-a780-d638c07829c8) | both | 11 | t1 bad target failed in demo-dbt-fail-11-two-task-level-both | [9e3b006b](https://app.getorchestra.io/pipeline-runs/9e3b006b-8390-4d64-9ccb-5b603a681111/lineage) R1 | — | t1 bad target | 5 | 13:51:31 | 14:04:05 | API |
| [0fad46fe](https://app.getorchestra.io/incidents/0fad46fe-452f-4006-bc43-f40cf056bcc0) | both | 11 | t2 parse fail failed in demo-dbt-fail-11-two-task-level-both | [9e3b006b](https://app.getorchestra.io/pipeline-runs/9e3b006b-8390-4d64-9ccb-5b603a681111/lineage) R1 | — | t2 parse fail | 5 | 13:51:44 | 14:04:04 | API |
| [cd9eeb23](https://app.getorchestra.io/incidents/cd9eeb23-90af-4961-9ae3-df392c2a430f) | both | 12 | dbt build (non-SAO) failed | [2d5bb70b](https://app.getorchestra.io/pipeline-runs/2d5bb70b-b097-437b-8a3c-0a2a150a1f27/lineage) R1 | — | dbt build (non-SAO) | 4 | 14:05:49 | OPEN |  |
| [e1f346bb](https://app.getorchestra.io/incidents/e1f346bb-0a1c-4d85-a214-b92c78c8b523) | both | 12 | dbt build (SAO) failed | [66503325](https://app.getorchestra.io/pipeline-runs/66503325-a1d6-46fc-a4d7-65fbf367f764/lineage) R1 | — | dbt build (SAO) | 4 | 14:07:26 | OPEN |  |

## Pipelines

All published, retries 0, branch `demo/failure-sim`. The 00-setup pipelines are the smoke tests from Step 3.

| pipeline | id |
|---|---|
| demo-dbt-fail-00-setup-nsao | `d1bee532-8092-4e46-a7a1-5cf1ebce427e` |
| demo-dbt-fail-00-setup-sao | `5b01c1a2-2446-459f-808a-268da8e8108a` |
| demo-dbt-fail-01-single-mid-both | `830a8541-1894-48d4-9b43-09b4d71e87a3` |
| demo-dbt-fail-01-single-mid-nsao | `54ccd574-0377-4650-84c3-09eb698416bf` |
| demo-dbt-fail-01-single-mid-sao | `943c029f-16d3-40ea-a363-a83cb27d90f9` |
| demo-dbt-fail-02-sao-skip-next-both | `5656fa4d-e439-47e4-a17d-49ce54fc9e0a` |
| demo-dbt-fail-02-sao-skip-next-nsao | `b5411dbf-5acd-459b-9bc9-b01bcfbf712b` |
| demo-dbt-fail-02-sao-skip-next-sao | `b9b05475-f01a-4e25-86ca-39c54c100d51` |
| demo-dbt-fail-03-two-mid-both | `9e3700ba-9d37-498f-9b9f-b6fac2b3532d` |
| demo-dbt-fail-03-two-mid-nsao | `8b5ef9b5-3641-4120-aacf-a262d3a35537` |
| demo-dbt-fail-03-two-mid-sao | `464d03cb-7c9d-41e4-ba5e-e82b3eeb4783` |
| demo-dbt-fail-04-two-seq-both | `93071663-9e37-4509-bcb5-7db5c092d38c` |
| demo-dbt-fail-04-two-seq-nsao | `f4f4def4-5deb-4f07-a0b2-fe07854aebf1` |
| demo-dbt-fail-04-two-seq-sao | `e93e8afc-33f5-41da-b9c7-57e31cb52fc7` |
| demo-dbt-fail-05-same-model-2-tasks-both | `629c613f-8c11-48ee-909f-53efdf15fafa` |
| demo-dbt-fail-06-same-model-2-pipes-both-a | `48df26d4-3ed2-446e-adbf-474c7ec0f1b6` |
| demo-dbt-fail-06-same-model-2-pipes-both-b | `c2634534-d2c9-4151-ac2c-780583bb16f9` |
| demo-dbt-fail-06-same-model-2-pipes-nsao-a | `df21e94f-5530-4b93-86cc-747f7320a951` |
| demo-dbt-fail-06-same-model-2-pipes-nsao-b | `bac4ce6b-353b-409c-8be2-db9523530331` |
| demo-dbt-fail-06-same-model-2-pipes-sao-a | `97384306-c1dc-4fc7-b7a9-49680010d480` |
| demo-dbt-fail-06-same-model-2-pipes-sao-b | `8dcdcf12-e221-48ac-9245-d6c297cc27a3` |
| demo-dbt-fail-07-same-folder-both | `addbe65e-83ca-45fc-9eea-d6107abbe4af` |
| demo-dbt-fail-07-same-folder-nsao | `29e6dde1-13be-413f-abce-0be8219c7adb` |
| demo-dbt-fail-07-same-folder-sao | `098f446c-1fb6-408a-9537-c5ce296274c2` |
| demo-dbt-fail-08-hook-2-pipes-both-a | `a968db99-60c6-43a2-a7d2-f57dd33c1099` |
| demo-dbt-fail-08-hook-2-pipes-both-b | `cedbf7e1-bca5-4e88-9c59-1ded6c72368e` |
| demo-dbt-fail-08-hook-2-pipes-nsao-a | `6729579c-084a-4ac4-82b9-668f2b493c07` |
| demo-dbt-fail-08-hook-2-pipes-nsao-b | `d63495d1-d32b-41ce-bd25-779da8a8d7b3` |
| demo-dbt-fail-08-hook-2-pipes-sao-a | `aaa835e1-5322-4113-acac-9a3421fe6688` |
| demo-dbt-fail-08-hook-2-pipes-sao-b | `89f3e3d4-2a74-48a5-a87c-1a50a2bab8f1` |
| demo-dbt-fail-08b-runop-nsao | `6918c3ea-01be-458c-8188-db197cb3c901` |
| demo-dbt-fail-09-all-models-both | `25677cd3-01e1-4619-9385-bf4ca0213881` |
| demo-dbt-fail-09-all-models-nsao | `8a91903b-32d2-4b6f-bafd-41ea55b96cbc` |
| demo-dbt-fail-09-all-models-sao | `40faf329-fc86-4cf2-aa22-8e6e4271213d` |
| demo-dbt-fail-10-task-level-both | `e0269926-d3f1-4f2c-b974-5c02695448ae` |
| demo-dbt-fail-10-task-level-nsao | `8fbdcec7-22d7-4977-973b-19c3f6676860` |
| demo-dbt-fail-10-task-level-sao | `4346c54c-0e7c-48e3-bfef-063acf4cfb04` |
| demo-dbt-fail-11-two-task-level-both | `8474c2b0-c69e-4c1b-a1db-d0f30adc3a11` |
| demo-dbt-fail-11-two-task-level-nsao | `74400e38-37be-4760-a67f-3de5ef8da3e6` |
| demo-dbt-fail-11-two-task-level-sao | `8d0776b8-89fd-4836-abd4-643cffedfe65` |
| demo-dbt-fail-12-task-level-2-pipes-both-a | `36ce75ce-7592-477a-8fe1-1affb4e806b4` |
| demo-dbt-fail-12-task-level-2-pipes-both-b | `69b0e19d-ede4-476f-9066-7436a79a8e88` |
| demo-dbt-fail-12-task-level-2-pipes-nsao-a | `87bdad4d-6827-4bf5-b73d-8c77b4ae3eec` |
| demo-dbt-fail-12-task-level-2-pipes-nsao-b | `8d74f05f-2101-4f1c-ae3d-bde3a90200c0` |
| demo-dbt-fail-12-task-level-2-pipes-sao-a | `79f2ee63-4cb4-40a6-867a-54f3831e5d5a` |
| demo-dbt-fail-12-task-level-2-pipes-sao-b | `a914d0b0-875a-4b7c-a79b-e5fdf0061d8d` |

## Appendix: setup log (Steps 1–4, before the sweep)

Account: Orchestra Demo Account (`7868740d-923c-42fe-b7a5-324c5a32289f`), environment Production.
dbt branch: `demo/failure-sim` (commit `b52fd39`). Project: `dbt_projects/databricks_sao`.

### Setup checks

| Item | Result |
|---|---|
| Source pipeline `8324a0b2…` dbt task | connection `dbt_databricks_demo_54814`, `package_manager: PIP`, `project_dir: dbt_projects/databricks_sao`. It has **no** `python_version` and **no** `repo`/`branch`. I left them unset too, and Orchestra resolved `python_version` to 3.12. |
| Repo is that project | Yes. `dbt_projects/databricks_sao` (`profile: orchestra_dbt_databricks`). |
| dbt version | **dbt-core 1.10.9, dbt-databricks 1.10.10, dbt-orchestra 1.4.0** (from `requirements.txt` and the run logs). This is **< 1.12**, so `on_error` and "on-run-start skips nodes" degrade (see notes). |
| Source pipeline alerts | None, so no alert block on the new pipelines. |

### Smoke test (Step 3)

| pipeline | inputs | task statuses | models ERROR/SKIPPED/REUSED | incident ids | events | merged? | alert? | auto-resolved? |
|---|---|---|---|---|---|---|---|---|
| demo-dbt-fail-00-setup-nsao (run `f29bced7`) | none | `nsao` SUCCEEDED | 8 models OK, 2 tests PASS (PASS=11 incl. 1 hook), 0 / 0 / n/a | none (not queried individually) | n/a | n/a | no | n/a |
| demo-dbt-fail-00-setup-sao R1 (run `a7b6042a`) | demo_vars={}, default touch | `touch` OK, `sao` OK | log not read | none seen | n/a | n/a | no | n/a |
| demo-dbt-fail-00-setup-sao R2 (run `379cfb74`) | demo_vars={}, default touch | `touch` OK, `sao` OK | 8 built, 2 tests PASS, **0 reused** ("0 node(s) to be reused") | none seen | n/a | n/a | no | n/a |
| demo-dbt-fail-00-setup-sao R3 (run `e09f4e5d`) | demo_vars={}, `touch_cmd=dbt run-operation demo_noop` | `touch` OK, `sao` OK | **8/8 reused** ("Nothing to do") | none seen | n/a | n/a | no | n/a |

**SAO reuse confirmed.** After a real source touch, 0 of 8 nodes were reused. After a no-op touch, 8 of 8 were reused. The reuse reasons in the R3 log were "Source … has no new data since last run" for the two staging models and "Upstream node(s) being reused" for the rest.

Incident check: I listed incidents once after R3 and none relate to these pipelines (the ones returned are older, from other pipelines). I did not run `whats_broken` or `diagnose`, since all four runs were green.

### Pipelines created

| name | id | shape |
|---|---|---|
| demo-dbt-fail-00-setup-nsao | `d1bee532-8092-4e46-a7a1-5cf1ebce427e` | N |
| demo-dbt-fail-00-setup-sao | `5b01c1a2-2446-459f-808a-268da8e8108a` | S (inputs `demo_vars`, `touch_cmd`) |

Both are published, retries 0, branch `demo/failure-sim`. The Step 5 scenario pipelines (01 to 12) are **not created yet**.

### Monitors (Step 4), created with `enabled: false` (`demo-dbt-by-asset` later enabled and scoped for the sweep)

| name | id | groupBy | action | order now |
|---|---|---|---|---|
| demo-dbt-by-asset | `5d5e1c24-bcb4-40da-8cf4-ad7d33d78a6a` | asset | incident | 3 |
| demo-dbt-by-task | `548826b9-03e5-4783-8ab6-ffc1684deb56` | task | incident | 4 |
| demo-dbt-by-pipeline | `5936613f-ea8d-416f-ba2e-a952b8f05028` | pipeline | incident | 5 |
| demo-dbt-by-connection | `4bc89ebe-e52c-4bda-9c51-fdb8b2e1bb43` | connection | incident | 6 |
| demo-dbt-one-incident | `0655b8ff-c436-4ed3-be55-71bd16c0022d` | monitor | incident | 7 |
| demo-dbt-mute | `c6094a81-a84e-4777-bd94-d54734b3372e` | monitor | mute | 8 |

All match `{"integrations": ["DBT_CORE"]}`. None have alert destinations. Before each experiment, enable exactly one and move it to order 0 (`reorder_monitors`).

### Warnings

1. **Existing enabled monitors claim DBT_CORE failures.**
   - `All other pipeline failures (catch-all)` (order 2) matches DBT_CORE, so any demo failure with no demo monitor at order 0 becomes a MEDIUM incident and **posts to Slack `#alert-testing`**.
   - `Muted - scratch and test pipelines` (order 0) and `Scheduled pipeline failures (production)` (order 1) only match fixed pipeline id lists, so they won't claim the new pipelines.
   - Each demo monitor needs to sit at order 0 or it loses to the catch-all.
2. **Unpaused dbt pipelines that fire on their own** (schedule or sensor), which could create unrelated DBT_CORE incidents while a demo monitor is at order 0:
   - `Parallel ELT` (schedule 01:00 plus sensors; its latest run on 2026-10-13 ended WARNING)
   - `Snowflake dbt with Python profiling` (daily 08:00)
   - `Daily ELT - Airbyte to dbt (Snowflake) to Sigma` (schedule)
   - `AWS S3 sensor to Glue, Lambda, dbt, Redshift, SageMaker` (sensor)
   - Other unpaused dbt pipelines are manual only (for example `dbt Databricks SAO`, `dbt Core SAO`, `dbt (Incident)`, `DuckDB dbt purposefully failing models`).
   - The two with a 01:00 or 08:00 schedule are the likeliest to collide, so avoid experiments around those times, or pause them.

### Notes and deviations

- **dbt < 1.12.** `on_error` is a 1.12 feature, so on 1.10.9 I expect it to be ignored (my local 1.11 parse flagged it as `CustomKeyInConfigDeprecation`; I have not yet seen what 1.10.9 does with it, since no run has failed). Likewise `on-run-start` is not expected to skip nodes. So the `skip_children` vs `continue` distinction and the hook scenarios (08) may not behave as designed. The smoke runs only show the hook running and passing (`1 of 1 OK hook`). Treat all of this as untested until scenarios 01/04/08 run.
- **Catalog.** Your spec said `+database: "{{ var('demo_catalog', target.database) }}"`. The project already forces `+database: main`, so I used `var('demo_catalog', 'main')` for the demo folder and for the source. Models land in `main.orchestra_demo`, source in `main.orchestra_demo_raw`.
- **`touch_cmd`** holds the whole command (`dbt run-operation …`), not just the macro name, because the spec and the pipeline default disagree. The run-operation commands pass validation as a template.
- The `dbt run-operation demo_touch_source` task runs with `use_state_orchestration: false`, as specified.
- Local parse check ran under dbt 1.11 with a Snowflake dummy profile (no Databricks adapter locally); the real run on Orchestra is the actual test.
- results.md is not committed. The rest of the work is on `demo/failure-sim`.

