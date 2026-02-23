import sys

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

import os
import subprocess

def setup_git_auth(token: str, repo: str):
    """Configure git and gh CLI auth using a token."""
    # gh CLI picks this up automatically, no subprocess needed
    os.environ["GH_TOKEN"] = token

    # Only git remote needs subprocess
    subprocess.run(
        ["git", "remote", "set-url", "origin", f"https://{token}@github.com/{repo}.git"],
        check=True
    )

async def main(prompt: str, branch_name: str = "claude/auto-fix", pr_title: str = "Claude: automated fixes"):
    token = os.environ["GITHUB_TOKEN"]  # or pass as param
    repo = os.environ["GITHUB_REPO"]    # e.g. "owner/repo-name"
    setup_git_auth(token, repo)

    # Agentic loop: streams messages as Claude works
    async for message in query(
        prompt=f"""
{prompt}

After making all necessary changes:
1. Run: git checkout -b {branch_name}
2. Run: git add
3. Run: git commit -m "fix: automated fixes by Claude"
4. Run: git push origin {branch_name}
5. Run: gh pr create --title "{pr_title}" --body "## Changes\n\nAutomated fixes applied by Claude agent.\n\n### Files changed\n$(git diff main...HEAD --name-only)" --base main

Use the Bash tool to run each git/gh command.
""",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob", "Bash"],  # Tools Claude can use
            permission_mode="acceptEdits",  # Auto-approve file edits
        ),
    ):
        # Print human-readable output
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)  # Claude's reasoning
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")  # Tool being called
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")  # Final result


if __name__ == "__main__":
    prompt = sys.argv[1]
    branch = sys.argv[2]
    asyncio.run(main(prompt=prompt, branch_name=branch))
 