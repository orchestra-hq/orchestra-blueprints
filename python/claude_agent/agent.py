import os
import subprocess
import asyncio

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


def setup_git_auth(token: str, repo: str):
    """Configure git and gh CLI auth using a token."""
    os.environ["GH_TOKEN"] = token
    subprocess.run(
        ["git", "remote", "set-url", "origin", f"https://{token}@github.com/{repo}.git"],
        check=True
    )

async def main(prompt: str, tools: list[str] = ["Read", "Edit", "Glob"], use_github: bool = false):
    if use_github:
        token = os.environ["GITHUB_TOKEN"]
        repo = os.environ["GITHUB_REPO"]
        setup_git_auth(token, repo)

    async for message in query(
        prompt=f"""{prompt}""",
        options=ClaudeAgentOptions(
            allowed_tools=tools,
            permission_mode="acceptEdits",
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
    prompt = os.environ["PROMPT"]
    tools = os.environ["TOOLS"].split(",")
    asyncio.run(main(prompt=prompt, tools=tools))
