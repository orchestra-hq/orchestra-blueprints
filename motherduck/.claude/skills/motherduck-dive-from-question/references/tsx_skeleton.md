# TSX Dive skeleton

Drop into `dives/<slug>/<slug>.tsx`. Tune the SQL, titles, and palette per
question. Follow the KPI strip, chart, and table layout below.

```tsx
import { useSQLQuery } from "@motherduck/react-sql-query";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";

const N = (v: unknown): number => (v != null ? Number(v) : 0);

export default function <ComponentName>() {
  // 1. KPI strip — single-row aggregate
  const headline = useSQLQuery(`
    SELECT
      COUNT(*) AS total,
      SUM(CASE WHEN UPPER(<status_col>) IN ('FAILED','ERROR') THEN 1 ELSE 0 END) AS failed,
      COUNT(DISTINCT <entity_id>) FILTER (
        WHERE UPPER(<status_col>) IN ('FAILED','ERROR')
      ) AS entities_with_failures
    FROM "<db>"."<marts_schema>"."<fct_table>"
    WHERE started_at >= NOW() - INTERVAL 30 DAY
  `);

  // 2. Top-N breakdown — fuels the chart
  const topN = useSQLQuery(`
    SELECT
      COALESCE(<entity_name>, CAST(<entity_id> AS VARCHAR)) AS name,
      COUNT(*) AS failed_runs
    FROM "<db>"."<marts_schema>"."<fct_table>"
    WHERE started_at >= NOW() - INTERVAL 30 DAY
      AND UPPER(<status_col>) IN ('FAILED','ERROR')
    GROUP BY 1
    ORDER BY failed_runs DESC, name
    LIMIT 10
  `);

  // 3. Detail table — optional
  const detail = useSQLQuery(`
    SELECT <cols…>
    FROM "<db>"."<marts_schema>"."<fct_table>"
    WHERE …
    LIMIT 7
  `);

  const headlineRow = (Array.isArray(headline.data) ? headline.data : [])[0];
  const topRows = (Array.isArray(topN.data) ? topN.data : []).map((r: any) => ({
    name: String(r.name),
    failed_runs: N(r.failed_runs),
  }));
  const detailRows = Array.isArray(detail.data) ? detail.data : [];

  return (
    <div className="p-6" style={{ background: "#f8f8f8", color: "#231f20" }}>
      <h1 className="text-2xl font-semibold">{/* question as title */}</h1>
      <p className="text-sm mb-6" style={{ color: "#6a6a6a" }}>
        Trailing 30 days · sourced from <code>{"<db>.<marts_schema>"}</code>
      </p>

      {/* KPI strip */}
      <div className="grid grid-cols-3 gap-8 mb-8">
        <Kpi loading={headline.isLoading} value={N(headlineRow?.total)} label="Total runs" />
        <Kpi loading={headline.isLoading} value={N(headlineRow?.failed)} label="Failed runs" color="#bc1200" />
        <Kpi loading={headline.isLoading} value={N(headlineRow?.entities_with_failures)} label="Entities w/ failures" />
      </div>

      {/* Chart */}
      <h2 className="text-lg font-semibold mb-2">Failed runs by entity</h2>
      {topN.isLoading ? (
        <Skeleton height={280} />
      ) : topRows.length === 0 ? (
        <p style={{ color: "#6a6a6a" }} className="mb-8">No failures in the last 30 days.</p>
      ) : (
        <div className="mb-8">
          <ResponsiveContainer width="100%" height={Math.max(220, topRows.length * 28)}>
            <BarChart data={topRows} layout="vertical" margin={{ left: 140, right: 24, top: 8, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
              <XAxis type="number" stroke="#6a6a6a" fontSize={11} />
              <YAxis dataKey="name" type="category" width={200} stroke="#6a6a6a" fontSize={11} />
              <Tooltip />
              <Bar dataKey="failed_runs" fill="#0777b3" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Detail table */}
      {/* … */}
    </div>
  );
}

function Kpi({ loading, value, label, color }: { loading: boolean; value: number; label: string; color?: string }) {
  return (
    <div>
      {loading ? (
        <div className="h-12 w-24 bg-gray-200 animate-pulse rounded" />
      ) : (
        <p className="text-5xl font-bold" style={color ? { color } : undefined}>{value}</p>
      )}
      <p className="text-sm mt-2" style={{ color: "#6a6a6a" }}>{label}</p>
    </div>
  );
}

function Skeleton({ height }: { height: number }) {
  return <div className="bg-gray-100 animate-pulse rounded mb-8" style={{ height }} />;
}
```

## Palette (match the rest of the repo)

| Use | Hex |
| --- | --- |
| Background | `#f8f8f8` |
| Body text | `#231f20` |
| Muted text / axes | `#6a6a6a` |
| Red (failures, alerts) | `#bc1200` |
| Blue (primary bars / accents) | `#0777b3` |
| Borders / grid | `#e5e5e5` |

## Rules of thumb

- One `useSQLQuery` per logical section. Don't merge unrelated queries.
- Every section needs three render branches: `isLoading`, empty, populated.
- Every numeric goes through `N()` before render or before arithmetic.
- All `SELECT`s use fully-qualified `"<db>"."<schema>"."<table>"` with
  double-quoted identifiers — safer against future renames.
- Trailing windows on `started_at` (or whichever timestamp Step 1 picked).
  Be consistent within a Dive.
