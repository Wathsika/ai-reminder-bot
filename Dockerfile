# 1. Use a slim Python image to keep the size small
FROM python:3.11-slim

# 2. Set environment variables
# Prevents Python from writing .pyc files to disk
ENV PYTHONDONTWRITEBYTECODE=1
# Ensures console output is sent straight to logs (useful for Docker logs)
ENV PYTHONUNBUFFERED=1

# 3. Set the working directory inside the container
WORKDIR /app

# 4. Install system dependencies
# We need 'libpq-dev' and 'gcc' so Python can talk to PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 5. Install Python dependencies
# We copy requirements.txt FIRST to take advantage of Docker layer caching.
# If you change your code but not your requirements, Docker skips this step.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your application code
COPY . .

# 7. Security: Create a non-root user
# Running as "root" is a security risk. We create a user named 'appuser'.
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser /app
USER appuser

# 8. Start the bot
# This assumes your main script is inside a folder named 'app'
CMD ["python", "app/main.py"]