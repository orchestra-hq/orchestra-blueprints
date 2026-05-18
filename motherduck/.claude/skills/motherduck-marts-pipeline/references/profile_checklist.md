# Source profiling checklist (MotherDuck MCP)

Run these in parallel where possible — they're independent reads.

## 1. Inventory

```
mcp__MotherDuck__list_databases
mcp__MotherDuck__list_tables   database=<db>  schema=<source_schema>
```

For each candidate table:

```
mcp__MotherDuck__list_columns  database=<db>  schema=<source_schema>  table=<t>
```

## 2. Per-table sample + shape

```sql
-- Sample
SELECT * FROM <db>.<source_schema>.<t> LIMIT 5;

-- Row count + time window
SELECT COUNT(*) AS rows,
       MIN(created_at) AS first_seen,
       MAX(updated_at) AS last_seen
FROM <db>.<source_schema>.<t>;

-- Candidate primary key uniqueness
SELECT <id>, COUNT(*) AS n
FROM <db>.<source_schema>.<t>
GROUP BY 1
HAVING COUNT(*) > 1
LIMIT 5;
```

## 3. Status / enum distributions

For any `_status` / `_type` / `_state` column:

```sql
SELECT <col>, COUNT(*) AS n
FROM <db>.<source_schema>.<t>
GROUP BY 1
ORDER BY n DESC;
```

This tells you which `COUNT(*) FILTER (WHERE status = 'X')` columns make sense
in the fact rollup. Watch for case-mixing (`'SUCCEEDED'` vs `'Succeeded'`) —
the Dive layer should `UPPER()` to be safe.

## 4. DLT-style child tables

If you see tables named like `<parent>__<list_field>`, they're flattened array
columns. Each row has:

- `_dlt_parent_id` — FK to the parent row's `_dlt_id`
- `_dlt_list_idx` — original list position
- `value` (for scalar lists) or the unnested struct fields

These get folded back into the parent dim with a CTE per child table — see
`mart_patterns.md` for the join shape.

## 5. Date column choice

Pipelines usually have several timestamps (`created_at`, `started_at`,
`completed_at`, `updated_at`). For trailing-window facts (`fct_daily_*`),
`started_at` is usually what you want — it's when the work actually happened,
not when the record was created or last edited.

## 6. Pre-flight before authoring SQL

- [ ] Every fact has a clear grain ("one row per X")
- [ ] Every dim has a unique key
- [ ] Time-window facts use the right timestamp
- [ ] Child tables are folded back via CTE, not left as separate marts
- [ ] Status enums are listed so the Dive layer can filter without surprises
