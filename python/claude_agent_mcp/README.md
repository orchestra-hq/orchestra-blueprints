# Claude Agent MCP Task

This task runs Claude in a non-interactive pipeline mode and connects tools through MCP servers.

The entrypoint is `python/claude_agent_mcp/agent.py`.

## How MCP config works

You can configure MCP servers in two ways:

1. `MCP_SERVERS_JSON`: pass a JSON object of servers.

`ORCHESTRA_API_KEY` is always required for task status updates.

## Add a new MCP server

Use `MCP_SERVERS_JSON` and add a new top-level server key.

Example using remote HTTP/SSE MCP servers (per Claude Agent SDK docs):

```bash
export LIGHTDASH_TOKEN="ld_pat_xxx"
export GITHUB_TOKEN="ghp_xxx"
export ORCHESTRA_API_KEY="orch_xxx"

export MCP_SERVERS_JSON='{
  "lightdash": {
    "type": "http",
    "url": "https://your-lightdash-mcp.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${LIGHTDASH_TOKEN}"
    }
  },
  "github": {
    "type": "sse",
    "url": "https://your-github-mcp.example.com/sse",
    "headers": {
      "Authorization": "Bearer ${GITHUB_TOKEN}"
    }
  },
  "orchestra": {
    "type": "stdio",
    "command": "python",
    "args": ["-m", "orchestramcp.server"],
    "env": {
      "ORCHESTRA_API_KEY": "${ORCHESTRA_API_KEY}"
    }
  },
  "my_custom_server": {
    "type": "http",
    "url": "https://my-custom-mcp.example.com/mcp",
    "headers": {
      "Authorization": "Bearer ${MY_CUSTOM_TOKEN}"
    }
  }
}'
```

For non-streaming remote servers, use `"type": "http"`. For streaming endpoints, use `"type": "sse"`.
Set credentials in your pipeline environment and inject them into the `MCP_SERVERS_JSON` string before execution.

## Tool allowlist behavior

- If `TOOLS` is set, it is used as-is (comma-separated list).
- If `TOOLS` is not set, the script auto-enables one tool namespace per configured MCP server:
  - server `lightdash` -> `mcp__lightdash__*`
  - server `my_custom_server` -> `mcp__my_custom_server__*`

This means new MCPs are available automatically when added to `MCP_SERVERS_JSON`.

## Built-in custom output tool

`python/claude_agent_mcp/agent.py` includes a custom tool shim named `orchestra_set_outputs`
that writes task outputs with the Orchestra Python SDK (`OrchestraSDK.set_output`).

Invocation format (from Claude output text):

```text
TOOL_CALL orchestra_set_outputs {"name":"OUTPUT_NAME","value":"OUTPUT_VALUE"}
```

Notes:

- `name` must be a non-empty string.
- `value` accepts string/number/bool/object/array.
- Objects/arrays are JSON-serialized before being saved as the task output value.
- The tool call is parsed during assistant streaming output, so outputs are set immediately.
- The tool is only enabled when the incoming `CLAUDE_PROMPT` contains the exact text `orchestra_set_outputs`.

## Configure subagents with `AGENTS_JSON`

You can define Claude SDK subagents as a JSON object and pass it via `AGENTS_JSON`.
Each top-level key is the subagent name, and each value is an `AgentDefinition` object.

Example:

```bash
export ORCHESTRA_API_KEY="orch_xxx"
export MCP_SERVERS_JSON='{
  "orchestra": {
    "type": "stdio",
    "command": "python",
    "args": ["-m", "orchestramcp.server"],
    "env": {
      "ORCHESTRA_API_KEY": "${ORCHESTRA_API_KEY}"
    }
  }
}'

export AGENTS_JSON='{
  "code-reviewer": {
    "description": "Expert code review specialist for quality and security checks.",
    "prompt": "Review code for correctness, security issues, and maintainability risks. Return concise findings.",
    "tools": ["Read", "Grep", "Glob"],
    "model": "sonnet"
  },
  "test-runner": {
    "description": "Runs test commands and summarizes failures.",
    "prompt": "Run test commands, analyze output, and suggest likely fixes for failing tests.",
    "tools": ["Bash", "Read", "Grep"]
  }
}'
```

Notes:

- `AGENTS_JSON` is optional. If unset, no custom subagents are configured.
- If `AGENTS_JSON` is set, the script automatically adds the `Agent` tool to the allowlist if it is missing.
- At minimum, each subagent must include non-empty `description` and `prompt` fields.

## Required env vars

Always required:

- `ORCHESTRA_API_KEY`

## Optional env vars

- `CLAUDE_PROMPT`: task prompt passed to Claude.
- `TOOLS`: comma-separated allowed tools.
- `CLAUDE_MODEL`: if set, exported to `ANTHROPIC_MODEL`.
- `MCP_SERVERS_JSON`: optional JSON object of MCP servers.
- `AGENTS_JSON`: optional JSON object of subagent definitions (`AgentDefinition` per key).

## Notes for pipeline usage

- The agent is configured to run non-interactively (no user questions).
- Keep secrets in pipeline secret storage, not in committed files.
- Prefer `MCP_SERVERS_JSON` for portability across environments.
