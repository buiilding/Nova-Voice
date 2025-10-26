# Configuration Guide

Complete reference for all environment variables and configuration options in the speech transcription microservices.

## 📋 Configuration Files

### Environment File
Create `.env` file in the `backend/infra/` directory:

```bash
cp .env.example .env
```

### Example Configuration
```bash
# Redis Configuration
REDIS_URL=redis://localhost:6379

# Gateway Configuration
GATEWAY_PORT=5026
HEALTH_PORT=8080
SILENCE_THRESHOLD_SECONDS=2.0
SAMPLE_RATE=16000
BUFFER_SIZE=4096
WEBRTC_SENSITIVITY=3
SILERO_SENSITIVITY=0.7
PRE_SPEECH_BUFFER_SECONDS=1.0
MAX_QUEUE_DEPTH=100
LOG_LEVEL=INFO

# STT Worker Configuration
MODEL_SIZE=base
COMPUTE_TYPE=float16
DEVICE=cpu
BEAM_SIZE=5
INITIAL_PROMPT=
NORMALIZE_AUDIO=false
PENDING_ACK_TTL=30
VAD_FILTER=true

# Translation Worker Configuration
USE_STUB_TRANSLATION=true
EASYNMT_MODEL=opus-mt
```

## 🔧 Gateway Service Configuration

### Core Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_PORT` | `5026` | WebSocket port for client connections |
| `HEALTH_PORT` | `8080` | HTTP health check and metrics port |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |

### Audio Processing
| Variable | Default | Description |
|----------|---------|-------------|
| `SAMPLE_RATE` | `16000` | Audio sample rate in Hz |
| `BUFFER_SIZE` | `4096` | Audio buffer size for processing |
| `PRE_SPEECH_BUFFER_SECONDS` | `1.0` | Seconds of audio to keep before speech detection |

### Voice Activity Detection (VAD)
| Variable | Default | Description |
|----------|---------|-------------|
| `WEBRTC_SENSITIVITY` | `3` | WebRTC VAD sensitivity (0-3, lower = more sensitive) |
| `SILERO_SENSITIVITY` | `0.7` | Silero VAD sensitivity (0.0-1.0, lower = more sensitive) |

### Speech Session Management
| Variable | Default | Description |
|----------|---------|-------------|
| `SILENCE_THRESHOLD_SECONDS` | `2.0` | Silence duration to end speech session |
| `MAX_AUDIO_BUFFER_SECONDS` | `30.0` | Maximum audio buffer size before forced flush |
| `MAX_QUEUE_DEPTH` | `100` | Maximum Redis queue depth for backpressure |

## 🎯 STT Worker Configuration

### Model Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_SIZE` | `base` | Whisper model size (tiny, base, small, medium, large-v1, large-v2, large-v3) |
| `COMPUTE_TYPE` | `float16` | Computation precision (int8, float16, float32) |
| `DEVICE` | `cpu` | Computing device (cpu, cuda) |
| `BEAM_SIZE` | `5` | Beam search size for transcription |

### Processing Options
| Variable | Default | Description |
|----------|---------|-------------|
| `INITIAL_PROMPT` | `` | Initial prompt to guide transcription |
| `NORMALIZE_AUDIO` | `false` | Audio normalization before processing |
| `VAD_FILTER` | `true` | Enable voice activity detection filtering |
| `MAX_BATCH_SIZE` | `4` | Maximum audio segments to batch together |

### Performance Tuning
| Variable | Default | Description |
|----------|---------|-------------|
| `PENDING_ACK_TTL` | `30` | Time-to-live for pending acknowledgments (seconds) |
| `BATCH_TIMEOUT_MS` | `100` | Maximum time to wait for batch completion |

## 🌐 Translation Worker Configuration

### Model Settings
| Variable | Default | Description |
|----------|---------|-------------|
| `USE_STUB_TRANSLATION` | `true` | Use stub translation instead of real NLLB (for development) |
| `EASYNMT_MODEL` | `opus-mt` | EasyNMT model for translation |
| `DEVICE` | `cpu` | Computing device (cpu, cuda) |

## 🐳 Docker-Specific Configuration

### Resource Limits
```yaml
# In docker-compose.yml
services:
  stt_worker:
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
        reservations:
          memory: 2G
          cpus: '1.0'
```

### GPU Support
```yaml
# For NVIDIA GPU support
services:
  stt_worker:
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=cuda
```

### Scaling Configuration
```bash
# Scale individual services
docker-compose up --scale stt_worker=3
docker-compose up --scale translation_worker=2
docker-compose up --scale gateway=2
```

## 🔍 Configuration Validation

### Health Checks
All services expose health endpoints that validate configuration:

```bash
# Gateway health
curl http://localhost:8080/health

# STT Worker health
curl http://localhost:8081/health

# Translation Worker health
curl http://localhost:8082/health
```

Health responses include:
- Service status
- Configuration validation
- Model loading status
- Redis connectivity
- Resource usage metrics

## 🎛️ Development vs Production

### Development Configuration
```bash
# Lower resource usage for development
MODEL_SIZE=small
DEVICE=cpu
MAX_BATCH_SIZE=1
LOG_LEVEL=DEBUG
USE_STUB_TRANSLATION=true
```

### Production Configuration
```bash
# Optimized for performance
MODEL_SIZE=large-v3
DEVICE=cuda
MAX_BATCH_SIZE=8
LOG_LEVEL=INFO
USE_STUB_TRANSLATION=false
```

## 📊 Monitoring Configuration

### Metrics Endpoints
```bash
# Detailed metrics
curl http://localhost:8080/metrics  # Gateway
curl http://localhost:8081/metrics  # STT Worker
curl http://localhost:8082/metrics  # Translation Worker
```

### Log Levels
```bash
# Available levels
LOG_LEVEL=DEBUG    # Detailed debugging info
LOG_LEVEL=INFO     # General operational info
LOG_LEVEL=WARNING  # Warning conditions
LOG_LEVEL=ERROR    # Error conditions only
```

## 🔐 Security Configuration

### Network Security
```yaml
# In production docker-compose.yml
services:
  gateway:
    networks:
      - internal
    # No external port exposure
    expose:
      - "5026"
      - "8080"
```

### Environment Security
```bash
# Never log sensitive data
LOG_LEVEL=WARN

# Use secure Redis connections in production
REDIS_URL=rediss://username:password@redis.example.com:6380
```

## 🚀 Performance Tuning

### Memory Optimization
```bash
# For limited RAM systems
MODEL_SIZE=small
MAX_BATCH_SIZE=1
PRE_SPEECH_BUFFER_SECONDS=0.5
SILENCE_THRESHOLD_SECONDS=1.0
```

### GPU Optimization
```bash
# Maximize GPU utilization
MODEL_SIZE=large-v3
DEVICE=cuda
COMPUTE_TYPE=float16
MAX_BATCH_SIZE=16
BEAM_SIZE=1  # Reduce for speed
```

### Latency vs Accuracy Trade-offs
```bash
# Low latency (faster response)
SILENCE_THRESHOLD_SECONDS=0.8
MODEL_SIZE=small
BEAM_SIZE=1
MAX_BATCH_SIZE=1

# High accuracy (slower response)
SILENCE_THRESHOLD_SECONDS=3.0
MODEL_SIZE=large-v3
BEAM_SIZE=5
MAX_BATCH_SIZE=8
```

## 📋 Configuration Checklist

- [ ] `.env` file created from `.env.example`
- [ ] Redis URL configured and accessible
- [ ] Ports not conflicting with other services
- [ ] Model size appropriate for available RAM/GPU
- [ ] Device setting matches available hardware
- [ ] Health endpoints responding correctly
- [ ] Log levels set appropriately for environment

## 🆘 Troubleshooting Configuration

### Common Issues

**Redis Connection Failed**
```bash
# Check Redis is running
docker-compose ps redis

# Test connection
docker-compose exec redis redis-cli ping
```

**Model Download Issues**
```bash
# Pre-download models
pip install faster-whisper
python -c "import faster_whisper; faster_whisper.WhisperModel('base')"
```

**GPU Not Detected**
```bash
# Check GPU availability
nvidia-smi

# Verify Docker GPU support
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

**Port Conflicts**
```bash
# Find conflicting processes
netstat -ano | findstr :5026

# Change ports in .env
GATEWAY_PORT=5027
HEALTH_PORT=8081
```

**Memory Issues**
```bash
# Monitor memory usage
docker stats

# Reduce memory footprint
MODEL_SIZE=small
MAX_BATCH_SIZE=1
```
