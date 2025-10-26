# Real-Time Speech Transcription - Quick Start Guide

Get up and running with the open-source speech transcription and translation microservices in minutes!

## 🚀 Quick Start (5 minutes)

### Prerequisites
- Docker and Docker Compose
- 4GB+ RAM recommended
- NVIDIA GPU (optional, for faster transcription)

### 1. Clone and Setup
```bash
git clone <repository-url>
cd realtime-speech-microservices
```

### 2. Start All Services
```bash
# Development (with hot reload)
cd backend/infra
docker-compose up --build

# Or for production
docker-compose up --build
```

### 3. Test the System
```bash
# Check service health
curl http://localhost:8080/health  # Gateway
curl http://localhost:8081/health  # STT Worker
curl http://localhost:8082/health  # Translation Worker

# View logs
docker-compose logs -f
```

### 4. Run the Client
```bash
# Build and run the Electron app
cd frontend
npm install
npm run build
npm run electron

# Or use the terminal client for testing
cd backend/terminal_run
python live_transcription.py
```

## 📋 What's Running

- **Redis** (port 6379): Message queue and session storage
- **Gateway** (port 5026): WebSocket server handling audio streams
- **STT Worker** (port 8081): Speech-to-text transcription
- **Translation Worker** (port 8082): Text translation
- **Frontend** (Electron app): User interface

## 🧪 Test Features

1. **Voice Typing**: Press Win+Alt+V, speak, watch text appear in any application
2. **Live Subtitles**: Press Win+Alt+L for overlay subtitles
3. **Audio Selection**: Choose between microphone or system audio
4. **Language Selection**: Source/target language switching
5. **Scaling**: Add more workers with `docker-compose up --scale stt_worker=3`

## 📖 Documentation

- **[DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md)** - Local development guide
- **[CONFIGURATION.md](CONFIGURATION.md)** - Environment variables and settings
- **[GATEWAY_SERVICE.md](GATEWAY_SERVICE.md)** - WebSocket gateway documentation
- **[STT_WORKER.md](STT_WORKER.md)** - Speech-to-text worker details
- **[TRANSLATION_WORKER.md](TRANSLATION_WORKER.md)** - Translation worker details
- **[API_REFERENCE.md](API_REFERENCE.md)** - WebSocket message formats
- **[SHARED_MODULES.md](SHARED_MODULES.md)** - Common utilities and health monitoring

## 🆘 Troubleshooting

### Common Issues
```bash
# Check all service logs
docker-compose logs -f

# Restart services
docker-compose restart

# Clean rebuild
docker-compose down -v
docker-compose up --build

# Check resource usage
docker stats
```

### Performance Tuning
```bash
# Scale STT workers for better performance
docker-compose up --scale stt_worker=3

# Use GPU (if available)
# Edit docker-compose.yml and uncomment runtime: nvidia
```

---

**🎯 Ready to contribute? Check out [DEVELOPMENT_SETUP.md](DEVELOPMENT_SETUP.md) for local development!**

