# STAGE 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Install to a local folder to copy later
RUN pip install --user --no-cache-dir -r requirements.txt

# STAGE 2: Runner
FROM python:3.11-slim

WORKDIR /app

# Install only the runtime library for Postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python packages from builder
COPY --from=builder /root/.local /root/.local
COPY . .

# Ensure scripts in .local/bin are in PATH
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Security: Non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

CMD ["python", "-m", "app.main"]