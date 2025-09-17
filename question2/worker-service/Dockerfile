# Multi-stage build for Python worker service
FROM python:3.11-alpine AS builder

# Install build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    python3-dev

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-alpine AS production

# Install runtime dependencies
RUN apk add --no-cache \
    postgresql-libs \
    dumb-init && \
    rm -rf /var/cache/apk/*

# Create non-root user for security
RUN addgroup -g 1001 -S python && \
    adduser -S pyuser -u 1001 -G python

# Set working directory
WORKDIR /app

# Copy dependencies from builder stage
COPY --from=builder --chown=pyuser:python /root/.local /home/pyuser/.local

# Copy application code
COPY --chown=pyuser:python src/ ./src/

# Switch to non-root user
USER pyuser

# Add local Python packages to PATH
ENV PATH=/home/pyuser/.local/bin:$PATH
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import psycopg2; import os; \
    conn = psycopg2.connect( \
      host=os.getenv('DB_HOST', 'localhost'), \
      port=int(os.getenv('DB_PORT', '5432')), \
      database=os.getenv('DB_NAME', 'microservices_db'), \
      user=os.getenv('DB_USER', 'postgres'), \
      password=os.getenv('DB_PASSWORD', 'password') \
    ); conn.close()" || exit 1

# Start application with dumb-init for proper signal handling
ENTRYPOINT ["dumb-init", "--"]
CMD ["python", "src/worker.py"]
