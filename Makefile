.PHONY: validate validate-pipelines lint audit all install-tools

# Example pipeline YAMLs that the public docs link to.
PIPELINE_FILES := metadata_api/orchestra_pipeline.yaml $(wildcard python/data_assets/*/*.yaml)

validate: validate-pipelines
	yamllint $(PIPELINE_FILES)

validate-pipelines:
	@fail=0; \
	if [ -z "$(PIPELINE_FILES)" ]; then \
		echo "No pipeline YAML files found"; \
	else \
		for f in $(PIPELINE_FILES); do \
			echo "→ orchestra validate $$f"; \
			orchestra validate "$$f" || fail=1; \
		done; \
	fi; \
	exit $$fail

lint:
	ruff check . --exclude worktrees
	ruff format --check . --exclude worktrees

audit:
	find . -name requirements.txt -not -path '*/.venv/*' -exec pip-audit -r {} \; || true

install-tools:
	pipx install orchestra-cli ruff vulture pip-audit yamllint

all: validate lint audit
