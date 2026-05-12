- This is a public demo/blueprint repo. Every change must keep pipelines
  schema-valid: run `make validate` before committing.
- Do not change pipeline runtime behaviour: no edits to `cron`,
  `integration_job`, `parameters` semantics, or `depends_on` topology, unless
  the branch is `cleanup/pipelines/*` AND the change is listed in CLEANUP_PLAN.md.
- Connection IDs are out of scope — do not rewrite or flag them.
- For unfamiliar `integration` or `integration_job` values, consult the
  Orchestra Docs MCP — never guess.
- You own ONE leaf branch. Do not touch files outside your assigned glob —
  if you find something broken outside it, add an entry to CLEANUP_PLAN.md
  under "Cross-cutting follow-ups" and move on.
- Stage your work as mechanical → structural → semantic PRs on your branch.
  Each PR must independently pass `make validate lint`.
- One logical change per commit. Conventional commits. PRs ≤20 files.
- Treat every file as user-facing: prospects will read this repo.
- Your first action is to create your assigned branch from main and switch to
  it in your worktree. Use the exact branch name from CLEANUP_PLAN.md's
  "Proposed branch plan" table. Do not commit to main.
- For `orchestra/**/*.yml` and `orchestra/**/*.yaml`, do not flag missing top-of-file showcase header comments or missing `configuration.retries`; these checks are intentionally out of scope for cleanup findings.
