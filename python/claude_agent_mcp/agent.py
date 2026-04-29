import asyncio
import json
import os
import re

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ResultMessage, query
from orchestra_sdk.enum import TaskRunStatus
from orchestra_sdk.orchestra import OrchestraSDK


def _interpolate_env_vars(value: object) -> object:
    if isinstance(value, dict):
        return {k: _interpolate_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_interpolate_env_vars(item) for item in value]
    if isinstance(value, str):
        pattern = re.compile(r"\$\{([A-Z0-9_]+)\}")

        def replace(match: re.Match[str]) -> str:
            env_name = match.group(1)
            env_value = os.getenv(env_name)
            if env_value is None:
                raise RuntimeError(
                    f"MCP_SERVERS_JSON references unset environment variable: {env_name}"
                )
            return env_value

        return pattern.sub(replace, value)
    return value


async def main(
    prompt: str,
    tools: list[str],
    orchestra_api_key: str,
    mcp_servers: dict[str, dict[str, object]],
) -> None:
    options = ClaudeAgentOptions(
        allowed_tools=tools,
        system_prompt=(
            "You are an autonomous non-interactive pipeline agent. "
            "Use configured MCP tools to complete the task. "
            "Do not ask questions. Do not wait for user input. "
            "If critical data is missing, fail with a clear error."
        ),
        permission_mode="bypassPermissions",
        mcp_servers=mcp_servers,
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")

    orchestra = OrchestraSDK(api_key=orchestra_api_key)
    orchestra.update_task(status=TaskRunStatus.SUCCESS)


if __name__ == "__main__":
    prompt = os.getenv(
        "CLAUDE_PROMPT",
        "Use configured MCP servers to complete the task and return concise machine-readable output.",
    )
    orchestra_api_key = os.getenv("ORCHESTRA_API_KEY")
    if not orchestra_api_key:
        raise RuntimeError("Missing required environment variable: ORCHESTRA_API_KEY")

    mcp_servers_json = os.getenv("MCP_SERVERS_JSON")
    if mcp_servers_json:
        try:
            parsed_mcp_servers = json.loads(mcp_servers_json)
        except json.JSONDecodeError as error:
            raise RuntimeError(
                f"MCP_SERVERS_JSON must be valid JSON: {error.msg}"
            ) from error
        if not isinstance(parsed_mcp_servers, dict) or not parsed_mcp_servers:
            raise RuntimeError("MCP_SERVERS_JSON must be a non-empty JSON object")
        interpolated_mcp_servers = _interpolate_env_vars(parsed_mcp_servers)
        if not isinstance(interpolated_mcp_servers, dict):
            raise RuntimeError("MCP_SERVERS_JSON must decode into an object")
        mcp_servers: dict[str, dict[str, object]] = interpolated_mcp_servers
    else:
        lightdash_api_key = os.getenv("LIGHTDASH_API_KEY")
        if not lightdash_api_key:
            raise RuntimeError("Missing required environment variable: LIGHTDASH_API_KEY")

        lightdash_api_url = os.getenv("LIGHTDASH_API_URL")
        if not lightdash_api_url:
            raise RuntimeError("Missing required environment variable: LIGHTDASH_API_URL")

        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise RuntimeError("Missing required environment variable: GITHUB_TOKEN")

        lightdash_command = os.getenv("LIGHTDASH_MCP_COMMAND", "npx")
        lightdash_args = [
            item.strip()
            for item in os.getenv(
                "LIGHTDASH_MCP_ARGS", "-y,lightdash-mcp-server"
            ).split(",")
            if item.strip()
        ]
        github_command = os.getenv("GITHUB_MCP_COMMAND", "npx")
        github_args = [
            item.strip()
            for item in os.getenv(
                "GITHUB_MCP_ARGS", "-y,@modelcontextprotocol/server-github"
            ).split(",")
            if item.strip()
        ]

        mcp_servers = {
            "lightdash": {
                "type": "stdio",
                "command": lightdash_command,
                "args": lightdash_args,
                "env": {
                    "LIGHTDASH_API_KEY": lightdash_api_key,
                    "LIGHTDASH_API_URL": lightdash_api_url,
                },
            },
            "github": {
                "type": "stdio",
                "command": github_command,
                "args": github_args,
                "env": {
                    "GITHUB_TOKEN": github_token,
                },
            },
        }

    tools = [item.strip() for item in os.getenv("TOOLS", "").split(",") if item.strip()]
    if not tools:
        # Keep this MCP-only by default for deterministic automation.
        tools = [f"mcp__{server_name}__*" for server_name in mcp_servers.keys()]

    claude_model = os.getenv("CLAUDE_MODEL")

    if claude_model:
        os.environ["ANTHROPIC_MODEL"] = claude_model

    print("The Prompt is:", prompt)
    print("Enabled tools:", ",".join(tools))

    try:
        asyncio.run(
            main(
                prompt=prompt,
                tools=tools,
                orchestra_api_key=orchestra_api_key,
                mcp_servers=mcp_servers,
            )
        )
    except Exception:
        orchestra = OrchestraSDK(api_key=orchestra_api_key)
        orchestra.update_task(status=TaskRunStatus.FAILED)
        raise
