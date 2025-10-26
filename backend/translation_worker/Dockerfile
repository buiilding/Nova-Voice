FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout=300 --retries=10 -r requirements.txt
# RUN pip install -r requirements.txt

# Copy shared modules
COPY ../../shared ./shared/

# Copy application code
COPY *.py .
COPY entrypoint.sh .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8082/health || exit 1

# Set CUDNN library path for PyTorch
ENV CUDNN_LIBRARY_PATH=/usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib
ENV LD_LIBRARY_PATH=$CUDNN_LIBRARY_PATH:$LD_LIBRARY_PATH

# Run the application
CMD ["./entrypoint.sh"]

