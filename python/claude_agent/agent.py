import sys

import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async def main(prompt: str, branch_name: str = "claude/auto-fix", pr_title: str = "Claude: automated fixes"):
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
 