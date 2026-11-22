# Multi-stage build for Python backend
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpcap-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install uv (pinned to the version that generated uv.lock)
RUN pip install --no-cache-dir uv==0.10.9

# Export exact pins from the lockfile and install them
COPY pyproject.toml uv.lock ./
RUN uv export --frozen --no-dev --no-emit-project --format requirements-txt \
        --no-header -o /tmp/requirements.txt \
    && pip install --no-cache-dir --user -r /tmp/requirements.txt

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap \
    libpcap0.8 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 scanner && \
    mkdir -p /app && \
    chown -R scanner:scanner /app

WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/scanner/.local

# Copy application code
COPY --chown=scanner:scanner . .

# Set environment variables
ENV PATH=/home/scanner/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER scanner

# Expose port
EXPOSE 8000

# Health check (stdlib only: `requests` is not a runtime dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/health', timeout=5)"

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
