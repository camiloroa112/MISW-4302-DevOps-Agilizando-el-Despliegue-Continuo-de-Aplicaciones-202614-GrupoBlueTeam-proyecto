# Base image with the same Python version used locally
FROM python:3.12-slim

# Copy the uv binary from its official image (pin the version you use locally: uv --version)
COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /bin/uv

# Precompile bytecode, copy packages instead of linking, and print logs immediately
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy PYTHONUNBUFFERED=1

# Working directory inside the container
WORKDIR /app

# Copy only the dependency files first so this layer is cached between builds
COPY pyproject.toml uv.lock ./

# Install the exact locked dependencies, without dev tools like pytest
RUN uv sync --frozen --no-dev --no-install-project

# Copy the application source code
COPY application.py ./
COPY app ./app

# Create and switch to a non-root user
RUN useradd --create-home appuser
USER appuser

# Port that Beanstalk's nginx proxy forwards traffic to
EXPOSE 8000

# One worker with threads, so create_all() runs once per instance instead of once per worker
CMD ["/app/.venv/bin/gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "application:application"]