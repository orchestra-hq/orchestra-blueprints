# Cleanup Plan

> Filled in by the Auditor agent. Specialist agents read their assigned section
> and only act on items tagged for their branch. Check items off as PRs land.

**Status:** 🟢 audit complete — awaiting review
**Auditor commit:** 61e6143
**Last updated:** 2026-05-12 10:41 UTC

---

## Connection IDs — not in scope

Orchestra connection IDs (e.g. `snowflake_12345`, connection names referenced
from `connection:` fields in pipeline YAMLs) are NOT considered secrets or
findings for this cleanup pass. Security agent: do not flag them. Pipelines
agent: do not rewrite them. They are opaque references, not credentials.

---

## Scope freeze

This cleanup pass does NOT include: adding new blueprints, changing pipeline
runtime behaviour, migrating between Orchestra schema versions, refactoring
dbt models, or touching connection IDs. Findings in those categories go to
"Cross-cutting follow-ups" for later work.

---

## How to read this file

Each finding is one checkbox line:

`- [ ] <tag> <file:line> — <finding> — <suggested fix> — <branch>`

Tags: `structure | pipelines | python | dbt | security | docs | ci | deps`
Branches: `cleanup/security`, `cleanup/structure`, `cleanup/pipelines/*`,
`cleanup/python/*`, `cleanup/ci`, `cleanup/docs`

Impact ranking inside each section: high → medium → low.

---

## 1. Security  → `cleanup/security`

_Leaked secrets, credential hygiene, `.gitignore` gaps. Connection IDs are
out of scope (see top of file)._

### High
- [ ] security orchestra/novat.yml:50 — gitleaks flagged secret-shaped string (generic-api-key: orchestra_api_key": "REDACTED") — Replace token-like literal with non-sensitive placeholder and rotate if real
- [ ] security metadata_api/README.md:14 — gitleaks flagged secret-shaped string (generic-api-key: DESTINATION__SNOWFLAKE__CREDENTIALS__HOST": "REDACTED") — Replace token-like literal with non-sensitive placeholder and rotate if real
- [ ] security dbt_projects/postgres/db/scripts/create_db_insert_data.py:66 — semgrep python.sqlalchemy.security.sqlalchemy-execute-raw-query.sqlalchemy-execute-raw-query — Refactor to safe subprocess usage / parameterized SQL
- [ ] security python/claude_agent/agent.py:15 — semgrep python.lang.security.audit.subprocess-shell-true.subprocess-shell-true — Refactor to safe subprocess usage / parameterized SQL

### Medium
- [ ] security dbt_projects/postgres/db/dockerfile:9 — semgrep dockerfile.security.missing-user.missing-user container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:4 — semgrep yaml.docker-compose.security.no-new-privileges.no-new-privileges container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:4 — semgrep yaml.docker-compose.security.writable-filesystem-service.writable-filesystem-service container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:14 — semgrep yaml.docker-compose.security.no-new-privileges.no-new-privileges container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:14 — semgrep yaml.docker-compose.security.writable-filesystem-service.writable-filesystem-service container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:20 — semgrep yaml.docker-compose.security.no-new-privileges.no-new-privileges container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:20 — semgrep yaml.docker-compose.security.writable-filesystem-service.writable-filesystem-service container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:25 — semgrep yaml.docker-compose.security.no-new-privileges.no-new-privileges container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:25 — semgrep yaml.docker-compose.security.writable-filesystem-service.writable-filesystem-service container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:30 — semgrep yaml.docker-compose.security.no-new-privileges.no-new-privileges container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security dbt_projects/postgres/jaffle_shop_postgres/dbt_packages/dbt_utils/docker-compose.yml:30 — semgrep yaml.docker-compose.security.writable-filesystem-service.writable-filesystem-service container hardening gap — Apply non-root user, read-only FS, and no-new-privileges where applicable
- [ ] security patterns/run_multiple_pipelines/.env.example:1 — Committed .env-style file detected — Keep example values non-sensitive and document secret sourcing

### Low
- [ ] security azure/ml/config.json:1 — semgrep reported syntax parse error for this file — Fix file format so static scanners can parse it

---

## 2. Structure  → `cleanup/structure`

_Directory layout, naming conventions, redundant nesting, stale paths._

### High
- [ ] structure README.md:5 — Top-level dirs missing from root README index: azure, estuary, hybrid_deploy, multi_workspace_test — Add sections and links in Codebase Structure
- [ ] structure README.md:29 — README section 'Analytics' has no matching top-level directory — Add analytics directory docs or remove the section
- [ ] structure README.md:67 — README section 'Sensors' has no matching top-level directory — Add sensors directory docs or remove the section
- [ ] structure README.md:43 — README calls out flattening dbt nesting, but nested layout remains (e.g. dbt_projects/postgres/jaffle_shop_postgres) — Align folder structure or update README guidance

### Medium
- [ ] structure orchestra/test git .pipeline.yml:1 — Filename breaks sibling naming convention (contains spaces) — Rename to snake_case without spaces
- [ ] structure orchestra/postgres_demo_25012026__.yaml:1 — Filename contains double underscore unlike siblings — Normalize to single-underscore snake_case
- [ ] structure dbt_projects/snowflake/readme.md:1 — README filename casing differs from sibling convention — Normalize to README.md
- [ ] structure dbt_projects/motherduck_s3/readme.md:1 — README filename casing differs from sibling convention — Normalize to README.md
- [ ] structure dbt_projects/duckdb_example/readme.md:1 — README filename casing differs from sibling convention — Normalize to README.md
- [ ] structure dbt_projects/motherduck_postgres/readme.md:1 — README filename casing differs from sibling convention — Normalize to README.md

### Low
- [ ] structure dbt_projects/README.md:1 — dbt_projects root lacks a local README for naming/layout convention — Add dbt_projects/README.md with expected structure

---

## 3. Pipelines  → `cleanup/pipelines/*`

_Orchestra YAML: schema validity, missing alerts/retries/tags, missing header
comments. Connection IDs are out of scope. Split by subtree below._

_Policy note: for `orchestra/*.yml|yaml`, missing top-of-file showcase header comments and missing `configuration.retries` are intentionally ignored._

### `cleanup/pipelines/orchestra-core` — `orchestra/**/*.yml`
- [ ] pipelines orchestra/:1 — orchestra validate passed for all 52 YAML files; no schema validation failures — Keep validator enforced in CI
- [ ] pipelines orchestra/07112025_demo.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/071125_oliver.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/0711demo_2.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/25033036.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/2711_demo.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/agentic_analytics_demo.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/ai_agent_bigquery.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/aws_postgres_dbt.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/claude_agent.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/claude_agent_mcp.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/cli_demo.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/databricks_connections.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/databricks_metadata.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/dbt_snowflake.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/demo.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/demo03022026.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/dlt_demo.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/dq_metaengine.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/end_to_end.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/fivetran_elt.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/gcp.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/gcp_data_pipeline.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/gcp_iceberg.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/gcp_on_variant.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/grc_test.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/hl2e.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/hl2e_file1.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/lmr_test.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/matrices.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/novat.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/org_settings.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/pc_demo.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/pmc.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/postgres_demo.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/postgres_demo_25012026__.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/postgres_demo_27012026.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/postgres_fivetran_dbt.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/postgres_pipeline.yaml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/ps_demo.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/river.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/river_copy.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/sg.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/stellantis.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/studio_a.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/test git .pipeline.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/tm.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/townhall.yml:1 — Missing alerts — add alerts block for failure notification
- [ ] pipelines orchestra/wl_demo.yml:1 — Missing alerts — add alerts block for failure notification
### `cleanup/pipelines/dbt-blueprints` — `dbt_projects/**/*.yml`
- [ ] pipelines dbt_projects/:1 — No Orchestra pipeline YAML files under dbt_projects/**/*.yml|yaml for validator run — No validate action required in this subtree

### `cleanup/pipelines/metadata-api` — `metadata_api/**/*.yml`
- [ ] pipelines metadata_api/orchestra_pipeline.yaml:1 — Pipeline YAML lacks top-of-file showcase header comment, alerts, and configuration.retries — Add header comment, alerts block, and retry policy

### `cleanup/pipelines/patterns` — `patterns/**/*.yml`
- [ ] pipelines patterns/:1 — No pipeline YAML files found under patterns/**/*.yml|yaml — No validate action required in this subtree

---

## 4. Python  → `cleanup/python/*`

_Ruff/format, type hints, dedup, parameter handling. Split by subtree below._

### `cleanup/python/workers` — `python/**/*.py`
- [ ] python python/:1 — ruff check reported 31 issues (F401=15, E722=9, F811=3, F841=2, E402=1, F821=1); ruff format --check would reformat 22 files — Run ruff fix + format pass across scoped Python trees
- [ ] python python/:1 — Top offenders by file (descending): dlt/hubspot/__init__.py(5), dlt/run_dlt_pipelines_snowflake.py(5), dlt/run_dlt_pipelines.py(4), python/integration_a/example_entrypoint.py(4), python/anomalies.py(3), python/reverse_etl.py(3), azure/ml/pipeline_script.py(2), bauplan/scan.py(1), dlt/google_sheets_pipeline.py(1), dlt/snowflake_pipeline.py(1), python/claude_agent/agent.py(1), python/postgres/postgres_connector.py(1) — Prioritize cleanup by this order
- [ ] python python/postgres/postgres_connector.py:1 — Public functions missing type hints (10) — Add parameter and return annotations for public APIs
- [ ] python python/integration_a/sftp.py:1 — Public functions missing type hints (7) — Add parameter and return annotations for public APIs
- [ ] python python/integration_a/sftp_snowflake.py:1 — Public functions missing type hints (7) — Add parameter and return annotations for public APIs
- [ ] python python/integration_a/example_entrypoint.py:1 — Public functions missing type hints (6) — Add parameter and return annotations for public APIs
- [ ] python python/reverse_etl.py:13 — Ad-hoc os.getenv parameter wiring used for runtime inputs — Consolidate runtime parameter parsing in one typed config object
- [ ] python python/integration_a/example_entrypoint.py:22 — Ad-hoc os.getenv parameter wiring used for runtime inputs — Replace scattered env access with structured runtime inputs

### `cleanup/python/metadata-api` — `metadata_api/**/*.py`
- [ ] python metadata_api/run.py:1 — Scoped lint/dead-code scans found no direct violations, but dependency hygiene is unpinned — Add version pins and enable lint gate for metadata_api subtree
- [ ] python metadata_api/requirements.txt:1 — pip-audit blocked because dependencies are not pinned — Pin all dependencies with exact versions

### `cleanup/python/bauplan-estuary-dlt` — `bauplan/**`, `estuary/**`, `dlt/**`
- [ ] python dlt/hubspot/__init__.py:40 — Ruff reports unused imports (5x F401) — Remove unused imports or export intentionally via __all__
- [ ] python dlt/run_dlt_pipelines.py:8 — Bare except blocks (E722) mask failures — Catch specific exceptions and handle/report explicitly
- [ ] python dlt/run_dlt_pipelines_snowflake.py:8 — Bare except blocks (E722) mask failures — Catch specific exceptions and handle/report explicitly
- [ ] python patterns/run_multiple_pipelines/run_multiple_pipelines.py:1 — Module exceeds 300 lines (428) — Split into smaller focused modules
- [ ] python patterns/warehouse_savings/graph.py:1 — Module exceeds 300 lines (504) — Split plotting/data prep/CLI responsibilities
- [ ] python dlt/google_sheets/helpers/data_processing.py:1 — Module exceeds 300 lines (349) — Decompose helper into smaller units
- [ ] python bauplan/models.py:20 — vulture flagged multiple unused functions — Remove dead code or wire functions into execution flow
- [ ] python bauplan/scan.py:95 — vulture flagged unused helper delete_branch_if_exists — Remove helper or integrate it where needed
- [ ] python bauplan/:1 — Duplicate helper scan found no cross-folder identical helper bodies — Keep shared helpers centralized as code evolves

### `cleanup/python/azure-hybrid` — `azure/ml/**`, `hybrid_deploy/**`, `multi_workspace_test/**`
- [ ] python azure/ml/pipeline_script.py:2 — Unused imports reported by ruff — Remove dead imports
- [ ] python azure/ml/scripts/prep_data.py:14 — Public functions missing type hints — Add parameter/return annotations
- [ ] python azure/ml/scripts/train.py:14 — Public functions missing type hints — Add parameter/return annotations
- [ ] python hybrid_deploy/README.md:1 — hybrid_deploy included in Python scope but has no .py files — Confirm intended scope or add code/docs clarifying purpose

---

## 5. CI  → `cleanup/ci`

_GitHub Actions, Makefile, pre-commit. Reserved files: anyone wanting a CI
change adds a request under "Cross-cutting follow-ups" below._

### High
- [ ] ci .github/workflows/24032026.yaml:20 — Pipeline workflow does not run make validate — Add validation job for YAML schema/lint gates
- [ ] ci .github/workflows/27012026.yaml:24 — Import workflow does not run ruff check/format — Add Python lint/format gates before import
- [ ] ci .github/workflows/gcp.yaml:16 — Pipeline workflow does not run gitleaks — Add secret scanning stage
- [ ] ci .github/workflows/orchestra_trigger.yaml:16 — Pipeline workflow does not run pip-audit — Add dependency vulnerability audit stage

### Medium
- [ ] ci .github/workflows/24032026.yaml:1 — Workflow purpose: run Orchestra impact-analysis and dbt stage pipeline on selected path changes — Pair runtime trigger with quality gates
- [ ] ci .github/workflows/27012026.yaml:1 — Workflow purpose: import newly added orchestra YAML files to Orchestra on push — Add pre-import safety checks
- [ ] ci .github/workflows/gcp.yaml:1 — Workflow purpose: run a specific Orchestra pipeline when orchestra/gcp.yml changes — Add repository-level validation/lint/security jobs
- [ ] ci .github/workflows/orchestra_trigger.yaml:1 — Workflow purpose: run dq_metaengine pipeline when matching YAML changes — Add repository-level validation/lint/security jobs

---

## 6. Docs  → `cleanup/docs`

_Root README, per-dir READMEs, generated PIPELINES.md. Reserved files:
README.md and PIPELINES.md — only this agent edits them. Merges last._

### High
- [ ] docs README.md:5 — Root README omits top-level dirs: azure, estuary, hybrid_deploy, multi_workspace_test — Add sections and links for each
- [ ] docs README.md:29 — README 'Analytics' section has no matching top-level directory — Add directory or remove stale section
- [ ] docs README.md:67 — README 'Sensors' section has no matching top-level directory — Add directory or remove stale section
- [ ] docs metadata_api/orchestra_pipeline.yaml:1 — Pipeline YAML has no description key/header — Add description key or top header comment

### Medium
- [ ] docs azure/:1 — Top-level documentation coverage: has README=no, mentioned in root README=no — add top-level README, add root README mention
- [ ] docs bauplan/:1 — Top-level documentation coverage: has README=no, mentioned in root README=yes — add top-level README
- [ ] docs dbt_projects/:1 — Top-level documentation coverage: has README=no, mentioned in root README=yes — add top-level README
- [ ] docs dlt/:1 — Top-level documentation coverage: has README=no, mentioned in root README=yes — add top-level README
- [ ] docs estuary/:1 — Top-level documentation coverage: has README=no, mentioned in root README=no — add top-level README, add root README mention
- [ ] docs hybrid_deploy/:1 — Top-level documentation coverage: has README=yes, mentioned in root README=no — add root README mention
- [ ] docs metadata_api/:1 — Top-level documentation coverage: has README=yes, mentioned in root README=yes — No change required
- [ ] docs multi_workspace_test/:1 — Top-level documentation coverage: has README=no, mentioned in root README=no — add top-level README, add root README mention
- [ ] docs orchestra/:1 — Top-level documentation coverage: has README=no, mentioned in root README=yes — add top-level README
- [ ] docs patterns/:1 — Top-level documentation coverage: has README=no, mentioned in root README=yes — add top-level README
- [ ] docs python/:1 — Top-level documentation coverage: has README=no, mentioned in root README=yes — add top-level README

---

## 7. Deps  → folded into `cleanup/python/*`

_Unpinned, unused, vulnerable. Each Python sub-agent handles deps for its
own subtree._

- [ ] deps bauplan/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement bauplan is not pinned: bauplan (from RequirementLine(line_number=1, line='bauplan', filename=PosixPath('bauplan/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps dbt_projects/azure_fabric/requirements.txt:1 — Version pinning state: fully pinned; pip-audit result: 0 known vulnerabilities — Keep pins fresh and run in CI
- [ ] deps dbt_projects/databricks/requirements.txt:1 — Version pinning state: fully pinned; pip-audit result: 0 known vulnerabilities — Keep pins fresh and run in CI
- [ ] deps dbt_projects/postgres/db/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement pandas is not pinned: pandas (from RequirementLine(line_number=1, line='pandas', filename=PosixPath('dbt_projects/postgres/db/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps dbt_projects/postgres/jaffle_shop_postgres/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement dbt-core is not pinned: dbt-core (from RequirementLine(line_number=1, line='dbt-core', filename=PosixPath('dbt_projects/postgres/jaffle_shop_postgres/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps dbt_projects/snowflake/requirements.txt:1 — Version pinning state: fully pinned; pip-audit result: 0 known vulnerabilities — Keep pins fresh and run in CI
- [ ] deps dlt/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement orchestra-sdk is not pinned: orchestra-sdk (from RequirementLine(line_number=1, line='orchestra-sdk', filename=PosixPath('dlt/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps metadata_api/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement dlt is not pinned: dlt (from RequirementLine(line_number=1, line='dlt', filename=PosixPath('metadata_api/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps patterns/run_multiple_pipelines/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement dotenv is not pinned: dotenv (from RequirementLine(line_number=1, line='dotenv', filename=PosixPath('patterns/run_multiple_pipelines/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps patterns/warehouse_savings/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement matplotlib is not pinned: matplotlib (from RequirementLine(line_number=1, line='matplotlib', filename=PosixPath('patterns/warehouse_savings/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps python/integration_a/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement orchestra-sdk is not pinned: orchestra-sdk (from RequirementLine(line_number=1, line='orchestra-sdk', filename=PosixPath('python/integration_a/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps python/postgres/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement gspread is not pinned: gspread (from RequirementLine(line_number=1, line='gspread', filename=PosixPath('python/postgres/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps python/requirements.txt:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement gspread is not pinned: gspread (from RequirementLine(line_number=2, line='gspread', filename=PosixPath('python/requirements.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps dbt_projects/duckdb_example/pyproject.toml:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement duckdb is not pinned: duckdb (from RequirementLine(line_number=1, line='duckdb', filename=PosixPath('/tmp/pip_audit_duckdb_example.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps dbt_projects/motherduck_postgres/pyproject.toml:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement duckdb is not pinned: duckdb (from RequirementLine(line_number=1, line='duckdb', filename=PosixPath('/tmp/pip_audit_motherduck_postgres.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps dbt_projects/motherduck_s3/pyproject.toml:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement duckdb is not pinned: duckdb (from RequirementLine(line_number=1, line='duckdb', filename=PosixPath('/tmp/pip_audit_motherduck_s3.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps dbt_projects/state_management/pyproject.toml:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement dbt-core is not pinned: dbt-core (from RequirementLine(line_number=1, line='dbt-core', filename=PosixPath('/tmp/pip_audit_state_management.txt')))) — Pin all dependencies to exact versions before auditing
- [ ] deps python/uv_support/pyproject.toml:1 — Version pinning state: unpinned/partial; pip-audit result: blocked (ERROR:pip_audit._cli:requirement pandas is not pinned: pandas (from RequirementLine(line_number=1, line='pandas', filename=PosixPath('/tmp/pip_audit_uv_support.txt')))) — Pin all dependencies to exact versions before auditing

---

## Cross-cutting follow-ups

_Findings that don't fit a single branch, or that one agent surfaces while
working in someone else's territory. Owner agent picks these up after their
main PRs land._

- [ ] ci Makefile:7 — make validate/lint/audit targets exist but are not enforced by any workflow end-to-end — Add shared CI workflow gating PRs on validate + lint + security + dependency audit

---

## Proposed branch plan

_Auditor lists the leaf branches it recommends spawning, with rough item
counts so you can decide whether to split further or merge sub-branches._

| Branch | Items | Est. PRs | Notes |
|---|---|---|---|
| cleanup/security | 17 | 1 | Keep security as one branch (per instruction); includes gitleaks + semgrep + env-file hygiene. |
| cleanup/structure | 11 | 1 | README/index alignment + naming normalization. |
| cleanup/pipelines/orchestra-core-a-m | 18 | 1 | Split orchestra-core by filename bands for reviewability. |
| cleanup/pipelines/orchestra-core-n-z | 18 | 1 | Second orchestra-core leaf split. |
| cleanup/pipelines/orchestra-core-special | 16 | 1 | Special/date-named pipelines and metadata gaps. |
| cleanup/pipelines/metadata-api | 1 | 1 | metadata_api pipeline metadata gaps. |
| cleanup/python/workers-core | 12 | 1 | ruff/type-hint/os.getenv cleanup in core workers. |
| cleanup/python/workers-integration-a | 10 | 1 | integration_a/postgres/reverse_etl focused cleanup. |
| cleanup/python/bauplan-estuary-dlt | 9 | 1 | dlt/bauplan lint, dead-code, large modules. |
| cleanup/python/azure-hybrid | 4 | 1 | azure/ml typing/lint plus scope sanity. |
| cleanup/ci | 8 | 1 | Add make validate, ruff, gitleaks, pip-audit checks. |
| cleanup/docs | 15 | 1 | Docs stays one final merge branch (per instruction). |

---

## Done

_Move completed items here with the merging PR number, so the live sections
stay focused on remaining work._

- [x] _example: pipelines — orchestra/snowflake_demo.yml missing alerts — #42_
