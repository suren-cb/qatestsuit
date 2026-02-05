FROM python:3.12-slim

# Install uv for fast dependency management
RUN pip install uv

WORKDIR /app

# Copy dependency files first (cached layer)
COPY pyproject.toml uv.lock README.md ./

# Copy application code
COPY app/ app/
COPY static/ static/
COPY config/ config/
COPY .env.example .env

# Install all dependencies + project
RUN uv sync --frozen --no-dev

# Create data directory for registry persistence
RUN mkdir -p data

EXPOSE 8085

CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8085"]
