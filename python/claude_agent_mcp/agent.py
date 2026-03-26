import os
import asyncio

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

from orchestra_sdk.enum import TaskRunStatus
from orchestra_sdk.orchestra import OrchestraSDK


async def main(prompt: str, tools: list[str], orchestra_api_key: str):
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=tools,
            system_prompt="""You are an autonomous data orchestration agent with access to Orchestra via MCP.
Always look for missing info in environment variables. If you lack enough context after this, raise an error.
Do not use the AskUserQuestion tool.""",
            permission_mode="bypassPermissions",
            mcp_servers={
                "orchestra": {
                    "command": "npx",
                    "args": ["@orchestra-hq/orchestra-mcp@latest"],
                    "env": {
                        "ORCHESTRA_API_KEY": orchestra_api_key,
                    },
                }
            },
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")


if __name__ == "__main__":
    prompt = os.getenv(
        "CLAUDE_PROMPT",
        "Use the Orchestra MCP to list all pipelines in the workspace and summarise their recent run statuses.",
    )
    try:
        tools = os.getenv("TOOLS").split(",")
    except Exception:
        tools = ["Read", "Glob", "Bash"]

    orchestra_api_key = os.environ["ORCHESTRA_API_KEY"]

    print("The Prompt is:", prompt)

    asyncio.run(main(prompt=prompt, tools=tools, orchestra_api_key=orchestra_api_key))

    orchestra = OrchestraSDK(api_key=orchestra_api_key)
    orchestra.update_task(status=TaskRunStatus.SUCCESS)
