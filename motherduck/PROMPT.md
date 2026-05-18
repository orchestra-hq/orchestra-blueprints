# Orchestra metadata → marts → Dive

This workflow is implemented as Claude Code skills under `.claude/skills/`.

**Entry skill:** `motherduck-orchestra-analysis` — question, your pipeline (alias, ID, or URL), live MotherDuck profiling, mart tasks appended after existing ingest, validate/run, Dive, verify, then ask about Dive republish wiring.

**Step skills:** `motherduck-marts-pipeline`, `motherduck-dive-from-question`, `motherduck-dive-publishing`, `orchestra-pipeline-via-api`.

**Examples:** `.claude/skills/motherduck-orchestra-analysis/references/example_invocations.md`

Run from this repo root (`claude`), then ask in plain language — no `@PROMPT.md` required.

```text
Let's dive into my slowest Orchestra pipelines. I'm ingesting the metadata in this pipeline, so add any work for the full analysis into it: https://app.getorchestra.io/pipelines/<id>
```

Marts only: add *stop after the pipeline passes — no Dive yet*.
