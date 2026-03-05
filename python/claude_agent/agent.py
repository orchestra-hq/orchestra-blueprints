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

async def main(prompt: str, tools: list[str] = ["Read", "Edit", "Glob"], github_repo: str = None):
    if github_repo:
        token = os.environ["GITHUB_TOKEN"]
        setup_git_auth(token, github_repo)

    async for message in query(
        prompt=f"""{prompt}""",
        options=ClaudeAgentOptions(
            allowed_tools=tools,
            permission_mode="bypassPermissions",
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
    
    prompt = os.getenv("CLAUDE_PROMPT", "Add docstrings to all functions in utils.py. Create a branch and a PR to add them into the main branch")
    github_repo = os.getenv("GITHUB_REPO", "orchestra-hq/orchestra-blueprints")
    print("The Prompt is:", prompt)
    print("GitHub Repo is:", github_repo)
    try:
        tools = os.getenv("TOOLS").split(",") 
    except:
        tools = "Read,Edit,Glob,Bash"
        
    asyncio.run(main(prompt=prompt, tools=tools, github_repo=github_repo))
