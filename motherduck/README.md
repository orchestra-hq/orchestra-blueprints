# MotherDuck + Orchestra analytics

Ask an Orchestra metadata question and name the pipeline that already ingests the source data. Claude Code skills profile live MotherDuck data, append mart SQL tasks downstream, run the pipeline, then publish and verify a MotherDuck Dive.

## Start here

- Entry skill: `.claude/skills/motherduck-orchestra-analysis/SKILL.md`
- Optional slash command: `/motherduck-analysis`
- Example phrasing: `.claude/skills/motherduck-orchestra-analysis/references/example_invocations.md`

Run from this directory so `.claude/skills/` loads.

## Generated artefacts

The agent writes outputs as it works; nothing is checked in up front.

| Path | Purpose |
| ---- | ------- |
| `sql/` | Mart DDL/CTAS aligned with deployed tasks |
| `pipelines/` | Full Orchestra YAML kept in sync with the target pipeline |
| `dives/<slug>/` | Dive TSX and `.dive_id` |
| `dive_drafts/` | Text answer and dive plan before TSX |

## Related skills

- `motherduck-marts-pipeline` — mart profiling and Orchestra tasks
- `motherduck-dive-from-question` — Dive authoring and verification
- `motherduck-dive-publishing` — `MD_*_DIVE` and base64 mechanics
- `orchestra-pipeline-via-api` — REST fallback and large YAML updates
