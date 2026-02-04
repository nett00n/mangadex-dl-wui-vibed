# Build arguments
ARG PYTHON_VERSION=3.12

# Builder stage
FROM python:${PYTHON_VERSION}-alpine AS builder

WORKDIR /build

# Install build dependencies and uv
RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    curl \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

ENV PATH="/root/.local/bin:${PATH}"

# Copy project files for dependency installation
COPY pyproject.toml .

# Install dependencies using uv
RUN uv pip install --system --no-cache .

# Runtime stage
ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-alpine AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install uv
RUN apk add --no-cache curl && \
    curl -LsSf https://astral.sh/uv/install.sh | sh && \
    apk del curl

ENV PATH="/root/.local/bin:${PATH}"

# Create non-root user
RUN adduser -D -u 1001 -s /bin/sh app

WORKDIR /app

# Copy project files for dependency installation
COPY pyproject.toml .

RUN uv pip install --system --no-cache .

# Copy application code
COPY --chown=app:app app/ ./app/

# Switch to non-root user
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/')"

# Default command (production)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:create_app()"]
