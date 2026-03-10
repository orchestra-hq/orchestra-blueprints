import os
import subprocess
import asyncio

from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

from orchestra_sdk.enum import TaskRunStatus
from orchestra_sdk.orchestra import OrchestraSDK

def run_lightdash_cli(command: str) -> str:
    """Run a Lightdash CLI command."""
    
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        return f"Error: {result.stderr}"

    return result.stdout

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
        system_prompt="""You are an autonomous agent. Always look for missing info in environment variables. If you lack enough context after this, raise an error. Do not use the AskUserQuestion tool"""
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
    
    prompt = os.getenv("CLAUDE_PROMPT", "Lightdash API key in env vars. Using this, " \
    "return a list of Lightdash cahrts with less than 30 views. Return a list of strings of IDs of the charts like ['chart_id1', 'chart_id2'] and set these as an environment variable LIGHTDASH_CHART_IDS.")
    github_repo = os.getenv("GITHUB_REPO", "orchestra-hq/orchestra-blueprints")
    print("The Prompt is:", prompt)
    print("GitHub Repo is:", github_repo)
    try:
        tools = os.getenv("TOOLS").split(",") 
    except:
        tools = "Read,Edit,Glob,Bash"
        
    asyncio.run(main(prompt=prompt, tools=tools, github_repo=github_repo))
    LIGHTDASH_CHART_IDS = os.getenv("LIGHTDASH_CHART_IDS", "No charts found or Lightdash API key not set.")
    orchestra = OrchestraSDK(api_key=os.getenv("ORCHESTRA_API_KEY"))
    if not LIGHTDASH_CHART_IDS:
        orchestra.update_task(status=TaskRunStatus.WARNING)
    else:
        orchestra.set_output(name='LIGHTDASH_CHART_IDS', value=LIGHTDASH_CHART_IDS)
