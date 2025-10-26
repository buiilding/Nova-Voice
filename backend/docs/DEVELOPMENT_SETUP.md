# Development Setup Guide

Complete guide for setting up the development environment for the real-time speech transcription and translation microservices.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Electron UI   │────│    Gateway      │────│     Redis       │
│  (WebSocket)    │    │  (WebSocket)    │    │  (Streams/Queue) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  STT Workers    │────│     Redis       │────│  Translation    │
│ (Faster-Whisper)│    │  (Pub/Sub)      │    │    Workers      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Development Start

### Prerequisites
- **Docker & Docker Compose** (required)
- **Python 3.9+** (optional, for local development)
- **Node.js 16+** (for frontend development)
- **4GB+ RAM** recommended
- **NVIDIA GPU** (optional, for faster transcription)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd realtime-speech-microservices
```

### 2. Start Development Environment
```bash
# All services with hot reload (recommended)
cd backend/infra
make up

# Or manually
docker-compose up --build
```

### 3. Start Frontend (Optional)
```bash
# In another terminal
cd frontend
npm install
npm run build
npm run electron
```

## 🔧 Development Workflows

### Hot Reload Development (Recommended)
```bash
cd backend/infra

# Start all services with volume mounts
make up

# View logs in real-time
make logs

# Restart services
make restart

# Stop services
make down
```

**Benefits:**
- ✅ Code changes reflect immediately (no rebuild)
- ✅ Full debugging capabilities
- ✅ Access to all logs and metrics
- ✅ Easy scaling for testing

### Local Python Development
```bash
# Install Python dependencies
pip install -r backend/gateway/requirements.txt
pip install -r backend/stt_worker/requirements.txt
pip install -r backend/translation_worker/requirements.txt

# Start Redis (in another terminal)
docker run -d -p 6379:6379 redis:7-alpine

# Start services (in separate terminals)
python -m backend.gateway.gateway
python -m backend.stt_worker.worker
python -m backend.translation_worker.worker
```

## 🧪 Testing and Debugging

### Health Checks
```bash
# Check all services
curl http://localhost:8080/health  # Gateway
curl http://localhost:8081/health  # STT Worker
curl http://localhost:8082/health  # Translation Worker

# Check Redis
docker-compose exec redis redis-cli ping
```

### Logs and Monitoring
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f gateway
docker-compose logs -f stt_worker

# Monitor Redis streams
docker-compose exec redis redis-cli xlen audio_jobs
```

### Test Clients
```bash
# Terminal client for testing
cd backend/terminal_run
python live_transcription.py

# Generate test audio
cd backend/stt_worker/tests
python generate_audio.py
```

## 🐛 Debugging Common Issues

### Service Won't Start
```bash
# Check if Redis is running
docker-compose ps redis

# Check service logs
docker-compose logs gateway

# Restart specific service
docker-compose restart gateway
```

### Model Download Issues
```bash
# Pre-download Whisper models
docker run --rm -it speech/stt-worker python -c "
import faster_whisper
model = faster_whisper.WhisperModel('base')
print('Model downloaded successfully')
"
```

### Port Conflicts
```bash
# Check what's using ports
netstat -ano | findstr :6379
netstat -ano | findstr :5026

# Change ports in docker-compose.yml
GATEWAY_PORT=5027
HEALTH_PORT=8081
```

### Memory Issues
```bash
# Monitor resource usage
docker stats

# Reduce model size for development
# Edit docker-compose.yml
MODEL_SIZE=small  # instead of base/large
```

## 🔧 Configuration for Development

### Environment Variables
```bash
# Copy example config
cp .env.example .env

# Development settings (lower resource usage)
MODEL_SIZE=small
DEVICE=cpu
MAX_BATCH_SIZE=2
LOG_LEVEL=DEBUG
```

### Scaling for Testing
```bash
# Scale STT workers
docker-compose up --scale stt_worker=2

# Scale translation workers
docker-compose up --scale translation_worker=3
```

## 🏗️ Development Workflow

### Making Code Changes

1. **Edit code** in your IDE
2. **Services auto-restart** (volume mounts)
3. **Check logs** for errors
4. **Test changes** with client
5. **Commit** when working

### Adding New Features

1. **Update relevant service** code
2. **Test locally** with development setup
3. **Add unit tests** if applicable
4. **Update documentation**
5. **Create pull request**

### Performance Testing
```bash
# Load test with multiple clients
cd backend/terminal_run
python demo_client.py --load-test --clients 10 --batches 3

# Monitor performance
docker stats
docker-compose logs -f | grep "latency\|throughput"
```

## 📁 Project Structure

```
backend/
├── gateway/           # WebSocket gateway service
├── stt_worker/        # Speech-to-text worker
├── translation_worker/ # Translation worker
├── shared/           # Common utilities
├── infra/            # Docker configuration
├── terminal_run/     # Test clients
└── docs/             # Documentation

frontend/             # Electron UI application
```

## 🔄 CI/CD Integration

### GitHub Actions Example
```yaml
name: Test Backend
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test with Docker
        run: |
          cd backend/infra
          docker-compose up -d
          sleep 30
          curl http://localhost:8080/health
          docker-compose down
```

## 📚 Additional Resources

- **[QUICK_START.md](../QUICK_START.md)** - Get running in 5 minutes
- **[CONFIGURATION.md](../CONFIGURATION.md)** - Environment variables reference
- **[GATEWAY_SERVICE.md](../GATEWAY_SERVICE.md)** - Gateway service details
- **[STT_WORKER.md](../STT_WORKER.md)** - STT worker documentation
- **[API_REFERENCE.md](../API_REFERENCE.md)** - WebSocket API reference

## 🆘 Need Help?

1. **Check the logs** - `make logs`
2. **Restart services** - `make restart`
3. **Clean rebuild** - `make build`
4. **Check health** - `curl localhost:8080/health`

**Happy coding! 🚀**
