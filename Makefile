.PHONY: verify compile lint test consistency

PYTHON ?= python3

verify: compile lint test consistency

compile:
	@$(PYTHON) -m compileall -q scripts assets/codex_hooks tests

lint:
	@$(PYTHON) -c "import ruff" >/dev/null 2>&1 || { \
		echo "ruff is required. Install it with: python -m pip install ruff"; \
		exit 1; \
	}
	@$(PYTHON) -m ruff check .

test:
	@$(PYTHON) -m unittest discover -s tests

consistency:
	@$(PYTHON) scripts/check_consistency.py
