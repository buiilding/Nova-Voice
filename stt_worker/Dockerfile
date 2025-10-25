FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    portaudio19-dev \
    python3-dev \
    libxcb-xinerama0 \
    libxcb1 \
    libx11-xcb1 \
    libglu1-mesa \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .

# Install with retry mechanism and timeout for large packages
RUN pip install --no-cache-dir --timeout=300 --retries=10 -r requirements.txt

# Alternative: Install large packages first with more aggressive retry
# RUN pip install --no-cache-dir --timeout=600 --retries=20 torch torchaudio
# RUN pip install --no-cache-dir --timeout=300 --retries=10 -r requirements.txt

# Set CUDNN library path for PyTorch
ENV CUDNN_LIBRARY_PATH=/usr/local/lib/python3.10/site-packages/nvidia/cudnn/lib
ENV LD_LIBRARY_PATH=$CUDNN_LIBRARY_PATH:$LD_LIBRARY_PATH

# Copy application code
COPY worker.py .

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

# Run the application
CMD ["python", "worker.py"]

