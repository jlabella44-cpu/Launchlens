# ListingJet dev tasks.
#
# POSIX shell recipes — run with `just <recipe>` after installing `just`
# (https://github.com/casey/just). Windows users without a POSIX `just`
# runtime can just call the underlying commands directly using the venv
# binaries, e.g. `.venv/Scripts/python.exe -m pytest -q` or
# `.venv/Scripts/ruff.exe check src tests alembic`.

set shell := ["bash", "-euo", "pipefail", "-c"]

# Fast local gate: lint + the non-DB, non-ffmpeg test subset.
check:
    ruff check src tests alembic scripts
    pytest -m "not db and not ffmpeg" -q

# Full test suite (needs Postgres on 5433 and ffmpeg on PATH for full green).
test:
    pytest -q

# Run the API with autoreload.
dev:
    uvicorn listingjet.main:app --reload --port 8000

# Run the pipeline worker standalone.
worker:
    python -m listingjet.pipeline.worker

# Regenerate .env.example from listingjet.config.Settings.
env-example:
    python scripts/gen_env_example.py

# Fail if .env.example is out of date with Settings.
env-check:
    python scripts/gen_env_example.py --check
