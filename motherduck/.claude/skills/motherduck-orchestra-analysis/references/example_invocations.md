# Example invocations

Run Claude Code from this repo root so `.claude/skills/` loads. No slash command is required — plain language triggers `motherduck-orchestra-analysis` when the description matches.

## Full analysis (marts + Dive)

```text
Let's dive into my slowest Orchestra pipelines. I'm ingesting the metadata in this pipeline, so add any work for the full analysis into it: https://app.getorchestra.io/pipelines/<id>
```

```text
Which pipelines failed most in the last 7 days? Append mart and Dive work to alias my_metadata_ingest.
```

```text
Build a MotherDuck Dive for daily success rate by environment. Metadata load is already in pipeline 8e78667d-55f9-4562-9190-18ebdf748861 — extend that pipeline.
```

## Marts only

```text
Profile Orchestra metadata and add mart tables for pipeline duration analysis to https://app.getorchestra.io/pipelines/<id>. Stop after the pipeline passes — no Dive yet.
```

## Dive only (marts already exist)

```text
Marts are already in my_db.orchestra_marts. Dive into the flakiest integrations and publish a Dive; pipeline is my_metadata_ingest for wiring later.
```

## Explicit skill (optional)

```text
/motherduck-orchestra-analysis Let's dive into my slowest Orchestra pipelines … pipeline: <url>
```

If your Claude Code build does not expose project skills as slash commands, ask in natural language or `@` the skill file:

```text
@.claude/skills/motherduck-orchestra-analysis/SKILL.md
Let's dive into my slowest Orchestra pipelines …
```
