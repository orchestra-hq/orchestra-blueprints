import sys
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

import os
import subprocess

def setup_git_auth(token: str, repo: str):
    """Configure git and gh CLI auth using a token."""
    os.environ["GH_TOKEN"] = token
    subprocess.run(
        ["git", "remote", "set-url", "origin", f"https://{token}@github.com/{repo}.git"],
        check=True
    )

def open_pr(edited_files: set, branch_name: str, pr_title: str):
    if not edited_files:
        print("No files were edited, skipping PR.")
        return

    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    subprocess.run(["git", "add", "--", *edited_files], check=True)
    subprocess.run(["git", "commit", "-m", "fix: automated fixes by Claude"], check=True)
    subprocess.run(["git", "push", "origin", branch_name], check=True)

    changed = "\n".join(edited_files)
    body = f"## Changes\n\nAutomated fixes applied by Claude agent.\n\n### Files changed\n{changed}"
    subprocess.run(
        ["gh", "pr", "create", "--title", pr_title, "--body", body, "--base", "main"],
        check=True
    )

async def main(prompt: str, branch_name: str = "claude/auto-fix", pr_title: str = "Claude: automated fixes"):
    token = os.environ["GITHUB_TOKEN"]
    repo = os.environ["GITHUB_REPO"]
    setup_git_auth(token, repo)

    edited_files = set()

    async for message in query(
        prompt=f"""
{prompt}

After making all necessary changes using the Read, Edit, and Glob tools, your work is done.
Git staging, commits, and PR creation will be handled automatically — do not run any git commands.
""",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Edit", "Glob"],
            permission_mode="acceptEdits",
            cwd=os.getcwd(),
        ),
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")
                    if block.name == "Edit" and hasattr(block, "input"):
                        path = block.input.get("file_path") or block.input.get("path")
                        if path:
                            edited_files.add(path)
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")

    open_pr(edited_files, branch_name, pr_title)


if __name__ == "__main__":
    prompt = sys.argv[1]
    branch = sys.argv[2]
    asyncio.run(main(prompt=prompt, branch_name=branch))