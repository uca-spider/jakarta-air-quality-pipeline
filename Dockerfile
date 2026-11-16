# Use official lightweight Python 3.12 slim base image
FROM python:3.12-slim

# Install uv directly from Astral's official image (fast, reproducible, no curl/pip needed)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Python and uv environment variables
# - PYTHONUNBUFFERED: Ensure log messages are immediately dumped to stream
# - PYTHONDONTWRITEBYTECODE: Prevent .pyc files generation inside container
# - UV_SYSTEM_PYTHON: Allow uv to install packages directly into the container's environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH="/app"

WORKDIR /app

# 1. Copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# 2. Install dependencies with uv (much faster than standard pip)
RUN uv pip install -r requirements.txt

# 3. Create non-root user for security best practices (least privilege)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# 4. Copy configuration, application source code and tests
COPY --chown=appuser:appuser pytest.ini .
COPY --chown=appuser:appuser src/ ./src/
COPY --chown=appuser:appuser tests/ ./tests/

# Default command: runs the test suite
CMD ["python", "-m", "pytest", "-v"]
