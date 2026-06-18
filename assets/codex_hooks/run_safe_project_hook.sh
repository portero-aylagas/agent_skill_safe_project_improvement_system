#!/usr/bin/env sh
set -eu

if [ -n "${SAFE_PROJECT_PYTHON:-}" ]; then
    exec "$SAFE_PROJECT_PYTHON" assets/codex_hooks/safe_project_hook.py "$@"
fi

if [ -n "${PYTHON:-}" ]; then
    exec "$PYTHON" assets/codex_hooks/safe_project_hook.py "$@"
fi

if [ -n "${VIRTUAL_ENV:-}" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
    exec "$VIRTUAL_ENV/bin/python" assets/codex_hooks/safe_project_hook.py "$@"
fi

for candidate in .venv/bin/python venv/bin/python env/bin/python .env/bin/python; do
    if [ -x "$candidate" ]; then
        exec "$candidate" assets/codex_hooks/safe_project_hook.py "$@"
    fi
done

if command -v uv >/dev/null 2>&1 && [ -f uv.lock ]; then
    exec uv run python assets/codex_hooks/safe_project_hook.py "$@"
fi

if command -v poetry >/dev/null 2>&1 && { [ -f poetry.lock ] || grep -q '^\[tool\.poetry\]' pyproject.toml 2>/dev/null; }; then
    exec poetry run python assets/codex_hooks/safe_project_hook.py "$@"
fi

if command -v pipenv >/dev/null 2>&1 && [ -f Pipfile ]; then
    exec pipenv run python assets/codex_hooks/safe_project_hook.py "$@"
fi

if command -v hatch >/dev/null 2>&1 && grep -q '^\[tool\.hatch' pyproject.toml 2>/dev/null; then
    exec hatch run python assets/codex_hooks/safe_project_hook.py "$@"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 assets/codex_hooks/safe_project_hook.py "$@"
fi

if command -v python >/dev/null 2>&1; then
    exec python assets/codex_hooks/safe_project_hook.py "$@"
fi

echo "No Python interpreter found. Set SAFE_PROJECT_PYTHON or PYTHON." >&2
exit 127
