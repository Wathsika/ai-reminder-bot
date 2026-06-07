# Use a slim image for building
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install dependencies globally in the builder stage
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# FINAL STAGE
FROM python:3.11-slim

WORKDIR /app

# Install runtime library for Postgres
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the installed libraries from the builder
COPY --from=builder /install /usr/local
COPY . .

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Create a non-root user and give them access to /app
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# Run the bot
CMD ["python", "-m", "app.main"]