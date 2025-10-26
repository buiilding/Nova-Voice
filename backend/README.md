# Backend Services - Nova Voice

Microservice backend for real-time speech transcription and translation using Faster-Whisper and NLLB models.

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose (recommended)
- Conda/Miniconda (for local development)
- Python 3.10+ (via conda environment)
- 4GB+ RAM (8GB+ recommended)
- NVIDIA GPU (optional)

### Option 1: Docker (Recommended)

```bash
# Development with hot reload
cd backend/infra
docker-compose up --build
```

### Option 2: Local Python with Conda (Alternative)

```bash
# Automated conda setup (recommended)
cd backend
./setup-conda.sh

# Or manual setup:
conda env create -f environment.yml
conda activate nova-voice

# Install additional pip packages (if needed)
pip install -r requirements.txt

# Run all services at once (recommended)
./run-services.sh dev

# Or run services individually
python -m gateway.gateway &
python -m stt_worker.worker &
python -m translation_worker.worker &
```

### Option 3: Manual Conda Setup

```bash
# Create conda environment manually
conda create -n nova-voice python=3.10
conda activate nova-voice

# Install PyTorch (choose CPU or CUDA)
# CPU version:
conda install pytorch torchaudio -c pytorch

# CUDA version (if you have NVIDIA GPU):
conda install pytorch torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia

# Install remaining dependencies
pip install -r requirements.txt

# Run services
./run-services.sh dev
```

## 📋 Services

| Service | Port | Description |
|---------|------|-------------|
| **Gateway** | 5026 | WebSocket server, VAD, audio streaming |
| **STT Worker** | 8081 | Speech-to-text using Faster-Whisper |
| **Translation Worker** | 8082 | Language translation using NLLB |
| **Redis** | 6379 | Message queue and state storage |

## 🧪 Health Checks

```bash
curl http://localhost:8080/health  # Gateway
curl http://localhost:8081/health  # STT Worker
curl http://localhost:8082/health  # Translation Worker
```

## 🎮 Service Runner Script

Use the `run-services.sh` script to manage all services. It automatically:

- ✅ Detects and activates conda environment (`nova-voice`)
- ✅ Creates `.env` file from `.env_example` if missing
- ✅ Starts Redis if not running
- ✅ Launches all three services in background
- ✅ Provides health monitoring and logs

```bash
cd backend

# Start all services (development mode with conda)
./run-services.sh dev

# Start all services (Docker mode)
./run-services.sh prod

# Check status of all services
./run-services.sh status

# View logs from all services
./run-services.sh logs

# Stop all services cleanly
./run-services.sh stop

# Restart all services
./run-services.sh restart
```

### Makefile Commands

For quick Docker management:

```bash
cd backend

# Start services with hot reload
make up

# View logs
make logs

# Restart services
make restart

# Stop services
make down

# Rebuild containers
make build
```

### Environment Setup

The script automatically handles conda environments:

1. **Looks for `nova-voice` conda environment**
2. **Activates it if found**
3. **Provides setup instructions if not found**
4. **Falls back to virtual environments or system Python**

**Recommended setup:**
```bash
# Create conda environment once
cd backend
conda env create -f environment.yml

# Then just run the script
./run-services.sh dev
```

## 📚 Documentation

- **[Configuration](docs/CONFIGURATION.md)** - Environment variables
- **[Development Setup](docs/DEVELOPMENT_SETUP.md)** - Development workflow
- **[Technical Details](docs/TECHNICAL_README.md)** - Architecture & implementation
