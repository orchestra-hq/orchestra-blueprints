# Python workers

`python/` contains Python modules used by this repo’s demos.

Most subfolders are intended to be executed by Orchestra via Python task
integrations (i.e., Orchestra launches the Python code as part of a pipeline
run).

Platform interaction patterns live under `patterns/`.

## Contents

- Worker modules for integrations and data movement.
- Subfolders with targeted examples (for example `integration_a/`,
  `integration_b/`, and `claude_agent/`).
- Shared dependencies in `requirements.txt`.
