#!/usr/bin/env bash
# Idempotently register a git-backed pipeline YAML with an Orchestra workspace.
#
# `orchestra import` creates a NEW pipeline on every call, so running it twice
# with the same alias leaves you with duplicates:
#   https://docs.getorchestra.io/docs/core-concepts/pipelines
# This wrapper looks the alias up in the workspace first and only imports when
# it is genuinely missing, which makes the step safe to re-run and safe to use
# for promotion into a second workspace.
#
# The workspace is chosen entirely by the ORCHESTRA_API_KEY in the environment.
#
# Usage:
#   ORCHESTRA_API_KEY=... bash scripts/orchestra_register_pipeline.sh \
#     --alias my-pipeline \
#     --path orchestra/my_pipeline.yml \
#     --working-branch main \
#     --workspace-label source
set -euo pipefail

ALIAS=""
PATH_TO_YAML=""
WORKING_BRANCH=""
WORKSPACE_LABEL="Orchestra"

while [ $# -gt 0 ]; do
  case "$1" in
    -a | --alias)
      ALIAS="$2"
      shift 2
      ;;
    -p | --path)
      PATH_TO_YAML="$2"
      shift 2
      ;;
    -w | --working-branch)
      WORKING_BRANCH="$2"
      shift 2
      ;;
    --workspace-label)
      WORKSPACE_LABEL="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [ -z "$ALIAS" ] || [ -z "$PATH_TO_YAML" ]; then
  echo "Both --alias and --path are required" >&2
  exit 2
fi

if [ -z "${ORCHESTRA_API_KEY:-}" ]; then
  echo "ORCHESTRA_API_KEY is not set - cannot talk to the $WORKSPACE_LABEL workspace" >&2
  exit 2
fi

if [ ! -f "$PATH_TO_YAML" ]; then
  echo "Pipeline YAML not found: $PATH_TO_YAML" >&2
  exit 2
fi

echo "Checking whether alias '$ALIAS' already exists in the $WORKSPACE_LABEL workspace..."

# fetch-pipelines prints the raw API payload; the exact envelope has varied, so
# accept either a bare list or a dict wrapping the list.
if ! orchestra fetch-pipelines > pipelines.json; then
  echo "Could not list pipelines in the $WORKSPACE_LABEL workspace" >&2
  exit 1
fi

set +e
python3 - "$ALIAS" <<'PY' < pipelines.json
import json
import sys

wanted = sys.argv[1]
payload = json.load(sys.stdin)

if isinstance(payload, dict):
    for key in ("results", "pipelines", "data", "items"):
        value = payload.get(key)
        if isinstance(value, list):
            payload = value
            break

if not isinstance(payload, list):
    # Unrecognised shape: refuse to guess rather than risk a duplicate import.
    print(f"Unexpected fetch-pipelines payload: {type(payload).__name__}", file=sys.stderr)
    sys.exit(2)

for pipeline in payload:
    if isinstance(pipeline, dict) and pipeline.get("alias") == wanted:
        print(pipeline.get("id", ""))
        sys.exit(0)

sys.exit(1)
PY
LOOKUP_STATUS=$?
set -e
rm -f pipelines.json

case "$LOOKUP_STATUS" in
  0)
    echo "Alias '$ALIAS' already registered in the $WORKSPACE_LABEL workspace - skipping import."
    echo "Git-backed pipelines read their definition from the repo, so the latest YAML is picked up automatically."
    ;;
  1)
    echo "Alias '$ALIAS' not found - importing into the $WORKSPACE_LABEL workspace."
    if [ -n "$WORKING_BRANCH" ]; then
      orchestra import --alias "$ALIAS" --path "$PATH_TO_YAML" --working-branch "$WORKING_BRANCH"
    else
      orchestra import --alias "$ALIAS" --path "$PATH_TO_YAML"
    fi
    ;;
  *)
    echo "Alias lookup failed - refusing to import in case it would create a duplicate." >&2
    exit 1
    ;;
esac
