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

Example:

```bash
export MCP_SERVERS_JSON='{
  "lightdash": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "lightdash-mcp-server"],
    "env": {
      "LIGHTDASH_API_KEY": "your-lightdash-key",
      "LIGHTDASH_API_URL": "https://your-lightdash-instance/api/v1"
    }
  },
  "github": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "env": {
      "GITHUB_TOKEN": "your-github-token"
    }
  },
  "my_custom_server": {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "my-mcp-server-package"],
    "env": {
      "MY_API_KEY": "your-api-key"
    }
  }
}'
```

## Tool allowlist behavior

- If `TOOLS` is set, it is used as-is (comma-separated list).
- If `TOOLS` is not set, the script auto-enables one tool namespace per configured MCP server:
  - server `lightdash` -> tool prefix `mcp__lightdash`
  - server `my_custom_server` -> tool prefix `mcp__my_custom_server`

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
