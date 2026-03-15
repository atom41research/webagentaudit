# Playwright base image includes Chromium, Firefox, WebKit + system deps
FROM mcr.microsoft.com/playwright/python:v1.58.0-noble

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src/ src/

# Install project dependencies (frozen from lock file)
RUN uv sync --frozen --no-dev --no-editable

# Install Playwright browsers matching the pinned version
RUN uv run playwright install --with-deps chromium

# Create output directories accessible from host via volume mount
RUN mkdir -p /data/screenshots /data/output

# Default working directory for output (screenshots, reports)
ENV WEBAGENTAUDIT_SCREENSHOTS_DIR=/data/screenshots

# Use the venv binary directly so WORKDIR can be /data
ENTRYPOINT ["/app/.venv/bin/webagentaudit"]
CMD ["--help"]

WORKDIR /data
