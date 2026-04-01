# Build stage
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

# Runtime stage
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy files BEFORE switching to non-root user
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

COPY alembic/ alembic/
COPY alembic.ini ./
COPY docker/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

RUN pip install playwright && playwright install chromium --with-deps

# Non-root user
RUN useradd --create-home --shell /bin/bash listingjet && \
    chown -R listingjet:listingjet /app
USER listingjet

EXPOSE ${PORT:-8000}

ENTRYPOINT ["./entrypoint.sh"]
CMD ["api"]
