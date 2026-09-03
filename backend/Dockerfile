FROM python:3.12-slim-bookworm

# System deps: libmagic for MIME detection, curl for healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy everything first (needed for editable install to resolve the package)
COPY . .

# Install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e "."

# Create non-root user and uploads directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/uploads && \
    chmod 777 /app/uploads && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
