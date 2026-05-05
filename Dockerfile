# ── Stage 1: dependency builder ──────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: runtime image ───────────────────────────────────
FROM python:3.11-slim

# tini: proper PID-1 signal handling (Ctrl-C / docker stop works cleanly)
RUN apt-get update && apt-get install -y --no-install-recommends tini curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source (respects .dockerignore)
COPY . .

# Ensure data / output dirs exist inside the container
RUN mkdir -p data output \
    # Create a non-root user for security
    && useradd -m -u 1001 bizradar \
    && chown -R bizradar:bizradar /app

USER bizradar

EXPOSE 8000

# Health check – hits the public /health endpoint every 30 s
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
