# Dive plan template

Drop into `dive_drafts/dive_plan_<slug>.md` before authoring TSX. The plan is
for the user to react to — keep it short and concrete. Match the headings
below; consistency makes diffs across iterations readable.

```markdown
# Dive plan: <Human title — usually the user's question>

**Question:** <verbatim user question>
**Marts source:** <db>.<marts_schema>
**Time window:** trailing 30 days on `started_at`
**Dive UUID:** <existing uuid, or "new">

## Direct answer (text)

<2–4 sentences with the headline numbers — what the data says right now>

## Layout

1. **KPI strip (3–4 metrics)**
   - Total runs (30d)
   - Failed runs (30d)
   - Distinct <entities> with failures
   - <optional 4th — top failing integration as a string>
2. **Top-N chart**
   - Horizontal `BarChart`, top 10 <entities> by failed runs
3. **Detail table** (optional)
   - 7 rows: top <breakdown> per <entity>, with % share

## SQL per section

### Section 1: headline KPIs
\`\`\`sql
SELECT
  COUNT(*) AS total_runs,
  SUM(CASE WHEN UPPER(run_status) IN ('FAILED','ERROR') THEN 1 ELSE 0 END) AS failed_runs,
  COUNT(DISTINCT pipeline_id) FILTER (WHERE UPPER(run_status) IN ('FAILED','ERROR')) AS pipelines_with_failures
FROM "my_db"."orchestra_marts"."fct_pipeline_run"
WHERE started_at >= NOW() - INTERVAL 30 DAY;
\`\`\`

### Section 2: top-10 by failed runs
\`\`\`sql
SELECT
  COALESCE(pipeline_name, CAST(pipeline_id AS VARCHAR)) AS pipeline_name,
  env_name,
  COUNT(*) AS failed_runs
FROM "my_db"."orchestra_marts"."fct_pipeline_run"
WHERE started_at >= NOW() - INTERVAL 30 DAY
  AND UPPER(run_status) IN ('FAILED','ERROR')
GROUP BY 1, 2
ORDER BY failed_runs DESC, pipeline_name
LIMIT 10;
\`\`\`

### Section 3: top integration per pipeline
<paste SQL>

## Open questions for the user

- <anything ambiguous about the question — e.g. "Should this include WARNING
  status too?">
- <anything about scope — e.g. "All envs or just prod?">

## Next step

If the plan looks right, I'll author `dives/<slug>/<slug>.tsx` and publish via
`MD_CREATE_DIVE` (new) / `MD_UPDATE_DIVE_CONTENT` (existing).
```

## When to skip the plan

- The user already accepted a plan in this session and is iterating on it.
- The change is a one-line tweak (window, status filter, palette).
- The user said "just ship it" — respect that. Save the plan to disk anyway
  for future reference but don't block on confirmation.

## When to insist on it

- New Dive (no `.dive_id` file yet).
- Adding a section to an existing Dive.
- Switching from one mart table to another.
- Anything where you're guessing at intent.
