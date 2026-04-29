# Claude Agent MCP Task

This task runs Claude in a non-interactive pipeline mode and connects tools through MCP servers.

The entrypoint is `python/claude_agent_mcp/agent.py`.

## How MCP config works

You can configure MCP servers in two ways:

1. `MCP_SERVERS_JSON` (recommended): pass a JSON object of servers.
2. Built-in fallback: if `MCP_SERVERS_JSON` is not set, the script builds default `lightdash` + `github` servers from env vars.

`ORCHESTRA_API_KEY` is always required for task status updates.

## Add a new MCP server

Use `MCP_SERVERS_JSON` and add a new top-level server key.

Example using remote HTTP/SSE MCP servers (per Claude Agent SDK docs):

```bash
export LIGHTDASH_TOKEN="ld_pat_xxx"
export GITHUB_TOKEN="ghp_xxx"

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
The agent resolves `${ENV_VAR}` placeholders in `MCP_SERVERS_JSON` at runtime, so credentials can come from your pipeline secret environment.

## Tool allowlist behavior

- If `TOOLS` is set, it is used as-is (comma-separated list).
- If `TOOLS` is not set, the script auto-enables one tool namespace per configured MCP server:
  - server `lightdash` -> `mcp__lightdash__*`
  - server `my_custom_server` -> `mcp__my_custom_server__*`

This means new MCPs are available automatically when added to `MCP_SERVERS_JSON`.

## Required env vars

Always required:

- `ORCHESTRA_API_KEY`

Required only when not using `MCP_SERVERS_JSON`:

- `LIGHTDASH_API_KEY`
- `LIGHTDASH_API_URL`
- `GITHUB_TOKEN`

## Optional env vars

- `CLAUDE_PROMPT`: task prompt passed to Claude.
- `TOOLS`: comma-separated allowed tools.
- `CLAUDE_MODEL`: if set, exported to `ANTHROPIC_MODEL`.

Fallback-mode only (when `MCP_SERVERS_JSON` is not provided):

- `LIGHTDASH_MCP_COMMAND` (default: `npx`)
- `LIGHTDASH_MCP_ARGS` (default: `-y,lightdash-mcp-server`)
- `GITHUB_MCP_COMMAND` (default: `npx`)
- `GITHUB_MCP_ARGS` (default: `-y,@modelcontextprotocol/server-github`)

## Notes for pipeline usage

- The agent is configured to run non-interactively (no user questions).
- Keep secrets in pipeline secret storage, not in committed files.
- Prefer `MCP_SERVERS_JSON` for portability across environments.
