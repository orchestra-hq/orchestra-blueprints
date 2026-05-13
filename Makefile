.PHONY: validate validate-pipelines lint audit all install-tools

# All Orchestra pipeline YAMLs live under orchestra/. If the audit surfaces
# pipelines elsewhere (e.g. metadata_api/), extend this glob.
PIPELINE_FILES := $(shell find orchestra -type f \( -name '*.yml' -o -name '*.yaml' \) 2>/dev/null)

validate: validate-pipelines
	yamllint orchestra/

validate-pipelines:
	@fail=0; \
	if [ -z "$(PIPELINE_FILES)" ]; then \
		echo "No pipeline YAML files found under orchestra/"; \
	else \
		for f in $(PIPELINE_FILES); do \
			echo "→ orchestra validate $$f"; \
			ok=0; \
			for attempt in 1 2 3; do \
				orchestra validate "$$f" && ok=1 && break; \
				echo "validate failed for $$f (attempt $$attempt), retrying..."; \
				sleep 2; \
			done; \
			if [ "$$ok" -ne 1 ]; then \
				fail=1; \
			fi; \
		done; \
	fi; \
	exit $$fail

lint:
	ruff check . --exclude worktrees
	ruff format --check . --exclude worktrees

audit:
	gitleaks detect --no-banner --redact
	pip-audit -r python/requirements.txt || true

install-tools:
	pipx install orchestra-cli ruff vulture pip-audit yamllint

all: validate lint audit
