.PHONY: verify compile lint test consistency

DEFAULT_PYTHON := $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PYTHON ?= $(DEFAULT_PYTHON)

verify: compile lint test consistency

compile:
	@$(PYTHON) -m compileall -q scripts assets/codex_hooks tests

lint:
	@$(PYTHON) -c "import ruff" >/dev/null 2>&1 || { \
		echo "ruff is required. Install it with: $(PYTHON) -m pip install -r requirements-dev.txt"; \
		exit 1; \
	}
	@$(PYTHON) -m ruff check .

test:
	@$(PYTHON) -m unittest discover -s tests

consistency:
	@$(PYTHON) scripts/check_consistency.py
