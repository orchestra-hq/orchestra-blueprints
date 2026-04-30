import asyncio
import json
import os
import re

from claude_agent_sdk import (
    AgentDefinition,
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    query,
)
from orchestra_sdk.enum import TaskRunStatus
from orchestra_sdk.orchestra import OrchestraSDK

SET_OUTPUT_TOOL_NAME = "orchestra_set_outputs"
SET_OUTPUT_TOOL_PATTERN = re.compile(
    r"TOOL_CALL\s+orchestra_set_outputs\s+(\{.*?\})", re.DOTALL
)


def is_set_output_requested(prompt: str) -> bool:
    """Return True only when the prompt explicitly includes the tool name."""
    return SET_OUTPUT_TOOL_NAME in prompt


def try_run_set_output_tool(
    orchestra: OrchestraSDK, text: str, is_enabled: bool
) -> int:
    """
    Parse and execute inline TOOL_CALL invocations from assistant text.

    Expected format:
    TOOL_CALL orchestra_set_outputs {"name":"KEY","value":"VALUE"}
    """
    match_count = 0
    for match in SET_OUTPUT_TOOL_PATTERN.finditer(text):
        payload = match.group(1)
        if not is_enabled:
            print(f"Tool: {SET_OUTPUT_TOOL_NAME} skipped (not requested in prompt)")
            continue

        try:
            params = json.loads(payload)
        except json.JSONDecodeError:
            continue

        name = params.get("name")
        value = params.get("value")
        if not isinstance(name, str) or not name.strip():
            continue

        if isinstance(value, (dict, list)):
            serialized_value = json.dumps(value)
        else:
            serialized_value = "" if value is None else str(value)

        orchestra.set_output(name=name, value=serialized_value)
        print(f"Tool: {SET_OUTPUT_TOOL_NAME} (set '{name}')")
        match_count += 1

    return match_count


async def main(
    prompt: str,
    tools: list[str],
    orchestra_api_key: str,
    mcp_servers: dict[str, dict[str, object]] | None = None,
    agents: dict[str, AgentDefinition] | None = None,
) -> None:
    orchestra = OrchestraSDK(api_key=orchestra_api_key)
    set_output_enabled = is_set_output_requested(prompt)
    options = ClaudeAgentOptions(
        allowed_tools=tools,
        system_prompt=(
            "You are an autonomous non-interactive pipeline agent. "
            "Use configured MCP tools to complete the task. "
            "Do not ask questions. Do not wait for user input. "
            "If critical data is missing, fail with a clear error.\n\n"
            "Custom tool available:\n"
            f"- {SET_OUTPUT_TOOL_NAME}(name: str, value: str|number|bool|object|array)\n"
            "To call this tool, emit one line exactly in this format:\n"
            'TOOL_CALL orchestra_set_outputs {"name":"OUTPUT_NAME","value":"OUTPUT_VALUE"}\n'
            "Only call this when the user's prompt explicitly contains the text "
            "'orchestra_set_outputs'. If it does not, do not call this tool."
        ),
        permission_mode="bypassPermissions",
        mcp_servers=mcp_servers or {},
        agents=agents,
    )

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                    try_run_set_output_tool(
                        orchestra=orchestra,
                        text=block.text,
                        is_enabled=set_output_enabled,
                    )
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")

    orchestra.update_task(status=TaskRunStatus.SUCCEEDED)


if __name__ == "__main__":
    prompt = os.getenv(
        "CLAUDE_PROMPT",
        "Use configured tools to complete the task and return concise machine-readable output.",
    )
    orchestra_api_key = os.getenv("ORCHESTRA_API_KEY")
    if not orchestra_api_key:
        raise RuntimeError("Missing required environment variable: ORCHESTRA_API_KEY")

    mcp_servers_json = os.getenv("MCP_SERVERS_JSON", "").strip()
    mcp_servers: dict[str, dict[str, object]] = {}
    if mcp_servers_json:
        parsed_mcp_servers = json.loads(mcp_servers_json)
        if not isinstance(parsed_mcp_servers, dict):
            raise RuntimeError("MCP_SERVERS_JSON must parse to an object")
        mcp_servers = parsed_mcp_servers

    agents_json = os.getenv("AGENTS_JSON", "").strip()
    agents: dict[str, AgentDefinition] | None = None
    if agents_json:
        parsed_agents = json.loads(agents_json)
        if not isinstance(parsed_agents, dict) or not parsed_agents:
            raise RuntimeError("AGENTS_JSON must parse to a non-empty object")

        agents = {}
        for agent_name, agent_config in parsed_agents.items():
            if not isinstance(agent_name, str) or not agent_name:
                raise RuntimeError("AGENTS_JSON keys must be non-empty strings")
            if not isinstance(agent_config, dict):
                raise RuntimeError(
                    f"AGENTS_JSON['{agent_name}'] must be an object with AgentDefinition fields"
                )

            description = agent_config.get("description")
            prompt_value = agent_config.get("prompt")
            if not isinstance(description, str) or not description.strip():
                raise RuntimeError(
                    f"AGENTS_JSON['{agent_name}'].description must be a non-empty string"
                )
            if not isinstance(prompt_value, str) or not prompt_value.strip():
                raise RuntimeError(
                    f"AGENTS_JSON['{agent_name}'].prompt must be a non-empty string"
                )

            try:
                agents[agent_name] = AgentDefinition(**agent_config)
            except Exception as exc:
                raise RuntimeError(
                    f"Invalid AGENTS_JSON['{agent_name}'] AgentDefinition: {exc}. "
                    "Use SDK field names (camelCase), e.g. disallowedTools, mcpServers, maxTurns, permissionMode."
                ) from exc

    tools = [item.strip() for item in os.getenv("TOOLS", "").split(",") if item.strip()]
    if not tools:
        # If MCP servers are configured, default to MCP namespaces.
        tools = [f"mcp__{server_name}__*" for server_name in mcp_servers.keys()]
    if agents and "Agent" not in tools:
        tools.append("Agent")

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
                agents=agents,
            )
        )
    except Exception:
        orchestra = OrchestraSDK(api_key=orchestra_api_key)
        orchestra.update_task(status=TaskRunStatus.FAILED)
        raise
