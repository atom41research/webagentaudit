# Keep this tag aligned with the exact Playwright dependency in pyproject.toml.
# The image includes the matching browsers and their system dependencies.
FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install project dependencies (frozen from lock file)
RUN uv sync --frozen --no-dev --no-editable

# Create output directories accessible from host via volume mount
RUN mkdir -p /data/screenshots /data/output

# Default working directory for output (screenshots, reports)
ENV WEBAGENTAUDIT_SCREENSHOTS_DIR=/data/screenshots

# Use the venv binary directly so WORKDIR can be /data
ENTRYPOINT ["/app/.venv/bin/webagentaudit"]
CMD ["--help"]

WORKDIR /data
