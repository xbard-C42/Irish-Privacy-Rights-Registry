# Privacy Rights Registry - Production Docker Image
# Built for Irish government deployment requirements

FROM python:3.11-slim

# Metadata
LABEL maintainer="Matthew Cummins <xbard@protonmail.com>"
LABEL description="Privacy Rights Registry - Irish-hosted infrastructure preventing stalking/doxxing"
LABEL version="1.0.0"
LABEL repository="https://github.com/xbard-C42/privacy-rights-registry"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    redis-tools \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash privacy && \
    chown -R privacy:privacy /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set proper permissions
RUN chown -R privacy:privacy /app && \
    chmod +x scripts/*.sh

# Switch to non-root user
USER privacy

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/v1/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]