FROM python:3.12-slim

WORKDIR /app

# Install system deps for asyncpg and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy source + deps manifest, then install
COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e ".[dev]"

# Copy remaining app files
COPY alembic/ alembic/
COPY alembic.ini ./
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
CMD ["api"]
