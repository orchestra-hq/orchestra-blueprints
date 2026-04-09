"""Orchestrates autonomous Claude agent execution with GitHub integration for task automation."""
import ast
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

    final_text = None
    async for message in query(
        prompt=f"""{prompt}""",
        options=ClaudeAgentOptions(
            model="claude-haiku-4-5",
            allowed_tools=tools,
            system_prompt="""You are an autonomous agent. Always look for missing info in environment variables. If you lack enough context after this, raise an error. Do not use the AskUserQuestion tool""",
            permission_mode="bypassPermissions",
            env={"CLAUDE_CODE_MAX_OUTPUT_TOKENS": "2048"},
            # max_turns=5,
            setting_sources=[]
        ),
    ):
        if isinstance(message, AssistantMessage):
            print("Usage: ", message.usage)
            for block in message.content:
                if hasattr(block, "text"):
                    print(block.text)
                elif hasattr(block, "name"):
                    print(f"Tool: {block.name}")
        elif isinstance(message, ResultMessage):
            print(f"Done: {message.subtype}")
            final_text = message.result
    return final_text


if __name__ == "__main__":
    
    prompt = os.getenv("CLAUDE_PROMPT", "Lightdash API key in env vars. Using this, " \
    "return a list of Lightdash cahrts with less than 30 views. Return a list of strings of IDs of the charts like ['chart_id1', 'chart_id2'] and set these as an environment variable LIGHTDASH_CHART_IDS.")
    github_repo = os.getenv("GITHUB_REPO", "orchestra-hq/orchestra-blueprints")
    print("The Prompt is:", prompt)
    print("GitHub Repo is:", github_repo)
    try:
        tools = os.getenv("TOOLS").split(",") 
    except:
        tools = ["Read", "Edit", "Glob", "Bash"]
        
    CLAUDE_OUTPUT = asyncio.run(main(prompt=prompt, tools=tools, github_repo=github_repo))
    try:
        CLAUDE_OUTPUT = ast.literal_eval(CLAUDE_OUTPUT)
    except:
        pass
    print(CLAUDE_OUTPUT)
    print(type(CLAUDE_OUTPUT))
    # CLAUDE_OUTPUT = os.getenv("CLAUDE_OUTPUT", "No output found")
    orchestra = OrchestraSDK(api_key=os.getenv("ORCHESTRA_API_KEY"))
    if not CLAUDE_OUTPUT:
        orchestra.update_task(status=TaskRunStatus.WARNING)
    else:
        orchestra.set_output(name='CLAUDE_OUTPUT', value=CLAUDE_OUTPUT)
