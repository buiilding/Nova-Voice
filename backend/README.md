# Backend Services - Nova Voice

Microservice backend for real-time speech transcription and translation using Faster-Whisper and NLLB models.

## 🚀 Quick Start

### Configuration Setup

```bash
# Copy environment configuration from example
cp .env_example infra/.env

# Edit as needed (optional - defaults are production-ready)
# nano infra/.env
```

### Prerequisites
- Docker & Docker Compose (recommended)
- Conda/Miniconda (for local development)
- Python 3.10+ (via conda environment)
- 4GB+ RAM (8GB+ recommended)
- GPU (optional, but highly recommended for 10x faster performance)
  - **Windows**: [GPU Setup Guide for Windows](docs/GPU_SETUP_WINDOWS.md)
  - **Linux**: [GPU Setup Guide for Linux](docs/GPU_SETUP_LINUX.md)
  - **macOS**: [GPU Setup Guide for macOS](docs/GPU_SETUP_MAC.md)

### Option 1: Docker (Recommended)

```bash
# Development with hot reload
cd backend/infra
docker-compose up --build
```

**⏱️ First-time setup:**
- **Model downloads** may take **1-5 minutes** depending on your network speed
- Models being downloaded:
  - Whisper large-v3: ~3GB
  - NLLB-200-distilled-600M: ~2.5GB
- **Monitor progress**: 
  - Docker Desktop → Containers → Select `stt_worker` or `translation_worker` → View logs
  - Or terminal: `docker compose logs -f stt_worker translation_worker`
- **Look for**: "Loading model..." and "Model loaded successfully" messages

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

---

## 🔍 Troubleshooting First Run

### Services Taking Long to Start?

**This is normal!** On first run:
- **STT Worker** downloads Whisper model (~3GB): 1-3 minutes
- **Translation Worker** downloads NLLB model (~2.5GB): 1-3 minutes
- Total first-run time: **3-5 minutes** on average internet

**Monitor progress:**
   ```bash
# Watch logs in real-time
docker compose logs -f stt_worker
docker compose logs -f translation_worker

# Or in Docker Desktop:
# Containers → stt_worker/translation_worker → Logs
```

**What you'll see:**
```
stt_worker-1      | Loading Faster-Whisper model: large-v3...
stt_worker-1      | Downloading model files... (this takes time!)
stt_worker-1      | ✓ Model loaded successfully on GPU
```

### Services Ready When:
- ✅ Gateway: `Starting Gateway Service on port 5026`
- ✅ STT Worker: `Model loaded successfully`
- ✅ Translation Worker: `Model loaded successfully`
- ✅ Health checks: All return `"status": "healthy"`

### Check Health:
```bash
curl http://localhost:8080/health  # Gateway
curl http://localhost:8081/health  # STT Worker
curl http://localhost:8082/health  # Translation Worker
```

### ⚠️ Audio Quality Considerations

**Background Music/Noise:**
- **Speech detection (VAD) works best with clean speech**
- Background music, loud noise, or multiple speakers may:
  - Cause false speech detections
  - Reduce transcription accuracy
  - Split speech segments incorrectly
- **Best results**: Quiet environment with clear speech
- **Tip**: Use headset/microphone close to mouth for better isolation

**Recommended Audio Sources:**
- 🎤 **Best**: Close-mic headset or lapel mic
- ✅ **Good**: Desktop microphone in quiet room
- ⚠️ **Fair**: System audio with minimal background music
- ❌ **Poor**: System audio with loud music or multiple speakers

---

## 📚 Documentation

### GPU Setup Guides (⚡ 10x Faster Performance)
- **[Windows GPU Setup](docs/GPU_SETUP_WINDOWS.md)** - WSL2 + NVIDIA Container Toolkit
- **[Linux GPU Setup](docs/GPU_SETUP_LINUX.md)** - Native Docker + NVIDIA drivers
- **[macOS GPU Setup](docs/GPU_SETUP_MAC.md)** - Apple Silicon MPS or Remote GPU

### Core Documentation
- **[Configuration](docs/CONFIGURATION.md)** - Environment variables
- **[Development Setup](docs/DEVELOPMENT_SETUP.md)** - Development workflow
- **[Technical Details](docs/TECHNICAL_README.md)** - Architecture & implementation
