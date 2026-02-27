import os
import subprocess
import sys
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage


def setup_git_auth(token: str, repo: str):
    """Configure git and gh CLI auth using a token."""
    os.environ["GH_TOKEN"] = token
    subprocess.run(
        ["git", "remote", "set-url", "origin", f"https://{token}@github.com/{repo}.git"],
        check=True
    )

async def main(prompt: str, branch_name: str = "claude/auto-fix", tools: list[str] = ["Read", "Edit", "Glob"], pr_title: str = "Claude: automated fixes"):
    print(f"Using tools: {tools}")
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPO"]
    setup_git_auth(token, repo)

    async for message in query(
        prompt=f"""
{prompt}

After making all necessary changes:
1. Run: git checkout -b {branch_name}
2. Run: git add -u
3. Run: git commit -m "fix: automated fixes by Claude"
4. Run: git push origin {branch_name}
5. Run: gh pr create --title "{pr_title}" --body "## Changes\n\nAutomated fixes applied by Claude agent.\n\n### Files changed\n$(git diff main...HEAD --name-only)" --base main

Use the Bash tool to run each git/gh command.
""",
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
    prompt = os.getenv("PROMPT")
    branch = os.getenv("BRANCH")
    tools = os.getenv("TOOLS").split(",")
    print(tools)
    asyncio.run(main(prompt=prompt, branch_name=branch, tools=tools))
