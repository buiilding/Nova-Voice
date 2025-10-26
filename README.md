# Nova Voice - Real-Time Speech Transcription & Translation

A modern desktop application for real-time speech-to-text transcription and translation, featuring voice typing and live subtitle overlays.

## 🎯 Overview

Nova Voice provides two core functionalities:

- **🎤 Voice Typing**: Real-time speech-to-text with automatic keyboard input
- **📺 Live Subtitles**: Transparent overlay for on-screen transcription and translation

The system uses a microservice architecture with:
- **Electron Frontend**: Modern desktop application with glassmorphism UI
- **Backend Services**: Dockerized Python microservices for speech processing
- **Real-time Processing**: WebSocket streaming with GPU-accelerated AI models

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Electron Client │────│    Gateway      │────│     Redis       │
│  (WebSocket)    │    │  (WebSocket)    │    │  (Streams/Queue) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  STT Workers    │────│     Redis       │────│  Translation    │
│ (Faster-Whisper)│    │  (Pub/Sub)      │    │    Workers      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended for backend)
- **Conda/Miniconda** (alternative for backend development)
- **Node.js 18+** (for frontend)
- **4GB+ RAM** (8GB+ recommended)
- **NVIDIA GPU** (optional, for acceleration)

### 1. Start Backend Services

**Option A: Docker (Recommended)**
```bash
# Development setup with hot reload
cd backend/infra
docker-compose up --build

# Or use convenience commands
make up      # Start services
make logs    # View logs
make down    # Stop services
```

**Option B: Conda Environment (Alternative)**
```bash
# Automated conda setup (recommended)
cd backend
./setup-conda.sh

# Or manual setup:
conda env create -f environment.yml
conda activate nova-voice

# Run all services with one command
./run-services.sh dev
```

### 2. Start Frontend Application

```bash
# Install dependencies
cd frontend
npm install

# Launch Electron app
npm run electron
```

### 3. Start Using Nova Voice

The application will automatically connect to the backend services. Choose your mode:

- **Voice Typing**: Click "Voice Typing" to start speech-to-text input
- **Live Subtitles**: Click "Live Subtitle" for overlay display
- **Audio Source**: Select microphone or system audio
- **Languages**: Choose source and target languages

## 🎮 Usage Guide

### Voice Typing Mode
1. Click the **"Voice Typing"** button (turns blue when active)
2. Select your **audio source** (microphone/system audio)
3. Choose **source language** for transcription
4. Start speaking - text appears automatically in your active application

### Live Subtitles Mode
1. Click the **"Live Subtitle"** button (turns blue when active)
2. A **transparent overlay** appears at the bottom of your screen
3. Shows both **transcription** and **translation** in real-time
4. **Click-through design** - doesn't interfere with other applications

### Keyboard Shortcuts
- **`Win+Alt+V`**: Toggle voice typing mode
- **`Win+Alt+L`**: Toggle live subtitles mode
- **`Win+Alt+H`**: Hide application window

## 🔧 Configuration

### Backend Services

Create `backend/infra/.env`:

```bash
# Core settings
REDIS_URL=redis://redis:6379
GATEWAY_PORT=5026
HEALTH_PORT=8080

# Model settings
MODEL_SIZE=base          # tiny, base, small, medium, large-v3
DEVICE=cuda             # cuda/cpu
BEAM_SIZE=5             # Beam search size

# Audio settings
SAMPLE_RATE=16000       # Audio sample rate
SILENCE_THRESHOLD_SECONDS=2.0
```

### Scaling Services

```bash
# Scale STT workers
docker-compose up --scale stt_worker=3

# Scale translation workers
docker-compose up --scale translation_worker=2

# Scale gateways for more users
docker-compose up --scale gateway=2
```

## 🧪 Testing

### Health Checks

```bash
# Check all services
curl http://localhost:8080/health  # Gateway
curl http://localhost:8081/health  # STT Worker
curl http://localhost:8082/health  # Translation Worker
```

### Manual Testing

1. **Start services** (backend/infra)
2. **Launch Electron app** (frontend)
3. **Test voice typing**: Speak and verify text input
4. **Test live subtitles**: Toggle overlay and verify display
5. **Test language switching**: Change languages mid-session

## 📁 Project Structure

```
nova-voice/
├── backend/                    # Backend microservices
│   ├── gateway/               # WebSocket server & VAD
│   ├── stt_worker/            # Speech-to-text (Faster-Whisper)
│   ├── translation_worker/    # Translation (NLLB)
│   ├── shared/                # Shared utilities
│   ├── infra/                 # Docker & deployment
│   └── docs/                  # Backend documentation
├── frontend/                  # Electron desktop app
│   ├── app/                   # Next.js pages
│   ├── components/            # React components
│   ├── electron/              # Main & renderer processes
│   ├── lib/                   # Utilities & services
│   └── docs/                  # Frontend documentation
├── terminal_run/              # Legacy testing scripts
└── docs/                      # Project-wide documentation
```

## 📚 Documentation

### Getting Started
- **[Backend Setup](backend/README.md)** - Backend services quick start
- **[Frontend Setup](frontend/README.md)** - Electron app quick start
- **[Development Setup](docs/DEVELOPMENT_SETUP.md)** - Complete development guide

### Technical Documentation
- **[Architecture](docs/ARCHITECTURE_OVERVIEW.md)** - Technical implementation
- **[Configuration](docs/CONFIGURATION.md)** - Environment variables
- **[Live Subtitles](frontend/docs/LIVE_SUBTITLES.md)** - Subtitle overlay guide

### Services
- **[Gateway Service](backend/docs/TECHNICAL_README.md)** - WebSocket server
- **[STT Worker](backend/docs/STT_WORKER.md)** - Speech transcription
- **[Translation Worker](backend/docs/TRANSLATION_WORKER.md)** - Language translation

## 🛠️ Development

### Local Development

```bash
# Backend development
cd backend/infra
docker-compose up --build

# Frontend development
cd frontend
npm install
npm run electron
```

### Production Deployment

```bash
# Production backend
cd backend/infra
docker-compose up -d

# Build frontend for distribution
cd frontend
npm run build
npm run dist
```

## 🤝 Contributing

1. **Fork** the repository
2. **Create** a feature branch
3. **Make** changes with tests
4. **Submit** a pull request

See **[Development Setup](docs/DEVELOPMENT_SETUP.md)** for detailed contribution guidelines.

## 🌟 Key Features

- ✅ **Real-time Processing**: <200ms latency from speech to text
- ✅ **Multi-language Support**: 15+ languages with auto-detection
- ✅ **GPU Acceleration**: CUDA support for faster processing
- ✅ **Horizontal Scaling**: Scale workers independently
- ✅ **Modern UI**: Glassmorphism design with dynamic windows
- ✅ **Dual Modes**: Voice typing + live subtitle overlays
- ✅ **Audio Flexibility**: Microphone + system audio capture
- ✅ **Cross-platform**: Windows, macOS, Linux support

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)** - Speech transcription
- **[NLLB](https://github.com/facebookresearch/fairseq/tree/nllb)** - Neural translation
- **[Redis](https://redis.io/)** - Message queue and caching
- **[Electron](https://electronjs.org/)** - Desktop application framework

---

**Nova Voice** - Making speech accessible through real-time AI-powered transcription and translation.
