import subprocess
import sys

cwd = '/c/repos/orchestra-blueprints/python/claude_agent'

# Step 1: Create and checkout branch
result = subprocess.run(
    ['git', 'checkout', '-b', 'fix/utils-crash-bugs'],
    cwd=cwd,
    capture_output=True,
    text=True
)
print("branch:", result.stdout.strip(), result.stderr.strip())
print("rc:", result.returncode)
