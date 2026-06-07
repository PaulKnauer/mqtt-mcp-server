# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder

WORKDIR /app
COPY --link pyproject.toml uv.lock README.md ./
COPY --link src/ src/

RUN pip install --no-cache-dir uv \
    && uv sync --frozen --no-dev --no-install-project \
    && uv build --wheel \
    && uv export --frozen --no-dev --no-emit-project --format=requirements.txt > requirements.txt

FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r mqttmcp && useradd -r -g mqttmcp -d /app -s /sbin/nologin mqttmcp

# Copy only runtime dependencies + built wheel
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=builder /app/dist/*.whl dist/

RUN pip install --no-cache-dir dist/*.whl && rm -rf dist requirements.txt

USER mqttmcp

# stdio transport — container runs as a subprocess for MCP hosts
# For HTTP transport enable port 8000
EXPOSE 8000

ENTRYPOINT ["python", "-m", "mqtt_mcp"]
