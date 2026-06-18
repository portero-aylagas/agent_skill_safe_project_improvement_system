.PHONY: verify compile lint test

PYTHON ?= python3

verify: compile lint test

compile:
	@$(PYTHON) -m compileall -q src tests

lint:
	@$(PYTHON) -m ruff check .

test:
	@PYTHONPATH=src $(PYTHON) -m unittest discover -s tests
