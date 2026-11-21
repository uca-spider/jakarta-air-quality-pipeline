# Use official lightweight Python 3.12 slim base image
FROM python:3.12-slim

# Install system dependencies (git is required by dbt)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Install uv directly from Astral's official image (fast, reproducible, no curl/pip needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Python and uv environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH="/app" \
    DBT_PROFILES_DIR="/app/dbt"

WORKDIR /app

# 1. Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# 2. Install dependencies with uv (much faster than standard pip)
RUN uv pip install -r requirements.txt

# 3. Create non-root user for security best practices (least privilege)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# 4. Copy configuration, application source code, tests, and dbt models
COPY --chown=appuser:appuser pytest.ini .
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser tests/ ./tests/
COPY --chown=appuser:appuser dbt/ ./dbt/

# Default command: runs the unit test suite
CMD ["pytest", "-v"]
