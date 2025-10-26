# Technical Documentation: Real-Time Speech Transcription and Translation Microservices

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Technical Specifications](#technical-specifications)
6. [Configuration](#configuration)
7. [Deployment](#deployment)
8. [Monitoring and Observability](#monitoring-and-observability)
9. [Performance Characteristics](#performance-characteristics)
10. [Troubleshooting](#troubleshooting)

## System Overview

This is a horizontally scalable, Dockerized microservice pipeline for real-time speech transcription and translation. The system processes live audio streams through multiple worker services, providing low-latency speech-to-text transcription with optional translation capabilities.

### Key Features

- **Real-time Processing**: Sub-500ms end-to-end latency for speech transcription
- **Horizontal Scaling**: Independent scaling of STT, translation, and gateway services
- **Dual VAD System**: WebRTC + Silero VAD for robust speech detection
- **Multi-language Support**: 15+ languages with automatic language detection
- **GPU Acceleration**: CUDA support for Faster-Whisper transcription
- **Event-Driven Architecture**: Redis Streams + Consumer Groups for reliable job distribution
- **Session Persistence**: Redis-backed session state for gateway horizontal scaling
- **Health Monitoring**: Comprehensive metrics and health checks for all services

## Architecture

### Service Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Clients   │────│    Gateway      │────│     Redis       │
│  (WebSocket)    │    │  (WebSocket)    │    │  (Streams/Queue) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                │                        │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  STT Workers    │────│     Redis       │────│  Translation    │
│ (Faster-Whisper)│    │  (Pub/Sub)      │    │    Workers      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                │
                       ┌─────────────────┐
                       │   Results to    │
                       │    Clients      │
                       └─────────────────┘
```

#### Gateway Service (Port 5026)
- **Purpose**: WebSocket server handling client connections and audio streaming
- **Technology**: Python asyncio, websockets library
- **Key Features**:
  - Dual Voice Activity Detection (WebRTC + Silero VAD)
  - Session state persistence in Redis
  - Audio chunking and streaming to workers
  - Flow control with per-client job-in-flight tracking
  - Language settings management

#### STT Worker Service (Port 8081)
- **Purpose**: Speech-to-text transcription using Faster-Whisper
- **Technology**: Python, Faster-Whisper, PyTorch
- **Key Features**:
  - GPU-accelerated transcription with CUDA support
  - Consumer group-based job distribution
  - Base64 audio decoding and normalization
  - VAD filtering and beam search optimization

#### Translation Worker Service (Port 8082)
- **Purpose**: Text translation using EasyNMT
- **Technology**: Python, EasyNMT, PyTorch
- **Key Features**:
  - ThreadPoolExecutor for memory leak prevention
  - Automatic language mapping and detection
  - Memory monitoring with periodic garbage collection
  - Controlled thread pool to prevent resource exhaustion

#### Redis (Port 6379)
- **Purpose**: Message queuing and state storage
- **Configuration**:
  - Append-only file persistence
  - Memory optimization with LRU eviction
  - Stream node limits for performance
  - Pub/Sub channel management

### Client Applications

#### PyQt5 GUI Client
- **Purpose**: Desktop interface for voice typing and live subtitles
- **Technology**: PyQt5, pyaudio, websockets
- **Features**:
  - Voice typing mode with automated keyboard input
  - Live subtitle overlay with semi-transparent display
  - Audio device selection (microphone/system audio)
  - Multi-language support with real-time switching

#### Demo/Test Clients
- **Purpose**: Load testing and system validation
- **Technology**: Python asyncio, websockets, numpy
- **Features**:
  - Concurrent client simulation
  - Synthetic audio generation
  - Performance metrics collection
  - Load testing capabilities

## Component Details

### Gateway Service (`gateway/`)

#### Core Classes

**GatewayService** (`gateway.py`)
```python
class GatewayService:
    def __init__(self):
        self.redis_client = RedisClient(self.instance_id, self.logger)
        self.vad_detector = VoiceActivityDetector()
        self.audio_processor = AudioProcessor()
        self.websocket_handler = WebSocketHandler(self, self.redis_client, self.audio_processor)
        self.health_monitor = HealthMonitor(self.instance_id, self.logger, self.redis_client, self)
```

**SpeechSession** (`session.py`)
- Manages per-client speech state (INACTIVE → ACTIVE → SILENCE → INACTIVE)
- Handles audio buffer accumulation with pre-speech buffering
- Redis-backed persistence for horizontal scaling
- Base64 encoding/decoding for audio data serialization

**VoiceActivityDetector** (`vad.py`)
- Dual VAD implementation using WebRTC + Silero models
- WebRTC VAD: Fast, lightweight speech detection (10ms frames)
- Silero VAD: Accurate neural network-based detection
- Threaded execution to prevent blocking main event loop

#### Audio Processing Pipeline

1. **Audio Reception**: Binary WebSocket messages with metadata headers
2. **Resampling**: All audio normalized to 16kHz, 16-bit PCM
3. **Speech Detection**: Dual VAD with majority voting
4. **Buffer Management**: Rolling pre-speech buffer (1 second) + active speech accumulation
5. **Job Publishing**: Event-driven publishing to Redis Streams (not interval-based)

#### Session State Management

```python
@dataclass
class SpeechSession:
    state: SpeechState = SpeechState.INACTIVE
    audio_buffer: bytearray = None
    pre_speech_buffer: bytearray = None
    silence_start_time: Optional[float] = None
    accumulated_audio_bytes: int = 0
    last_published_len: int = 0
    source_lang: str = "en"
    target_lang: str = "vi"
    translation_enabled: bool = True
```

#### WebSocket Message Protocol

**Client → Gateway**:
```json
{
  "type": "set_langs",
  "source_language": "en",
  "target_language": "vi"
}
```

**Gateway → Client**:
```json
{
  "type": "realtime",
  "text": "Hello world",
  "translation": "Xin chào thế giới",
  "segment_id": "1699123456789",
  "processing_time": 0.234
}
```

### STT Worker Service (`stt_worker/`)

#### Core Implementation

**STTWorker** (`worker.py`)
- Consumer group-based job processing with Redis Streams
- Faster-Whisper model with configurable parameters
- GPU acceleration with CUDA device selection
- Comprehensive error handling and metrics collection

#### Audio Processing

```python
def transcribe_audio(self, audio_data: bytes, language: str = "", use_vad_filter: bool = True) -> Dict[str, Any]:
    # Convert bytes to numpy array
    audio_array = np.frombuffer(audio_data, dtype=np.int16)
    audio_float = audio_array.astype(np.float32) / 32768.0

    # Normalize audio to -0.95 dBFS
    if NORMALIZE_AUDIO:
        audio_float = self.normalize_audio(audio_float)

    # Transcribe with Faster-Whisper
    segments, info = self.model.transcribe(
        audio_float,
        language=language if language else None,
        beam_size=BEAM_SIZE,
        vad_filter=use_vad_filter
    )
```

#### Job Processing Flow

1. **Job Consumption**: Redis Stream consumer group reading
2. **Audio Decoding**: Base64 decoding of audio data
3. **Transcription**: Faster-Whisper processing with GPU acceleration
4. **Result Publishing**: Pub/Sub to client-specific channels
5. **Translation Triggering**: Publishing to transcriptions stream when translation enabled

### Translation Worker Service (`translation_worker/`)

#### Core Implementation

**TranslationWorker** (`worker.py`)
- EasyNMT model with automatic language detection
- ThreadPoolExecutor to prevent memory leaks
- Language code mapping for compatibility
- Memory monitoring with periodic GC

#### Language Mapping System

```python
LANGUAGE_MAPPING = {
    "en": "english", "vi": "vietnamese", "ja": "japanese",
    "zh": "chinese", "ko": "korean", "fr": "french",
    # ... 100+ language mappings
}
```

#### Translation Processing

```python
async def process_translation_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
    # Map language codes to EasyNMT format
    mapped_source_lang = get_mapped_language(source_lang)
    mapped_target_lang = get_mapped_language(target_lang)

    # Execute translation in thread pool
    translation = await asyncio.get_event_loop().run_in_executor(
        self.executor,
        lambda: self.model.translate(text, source_lang=mapped_source_lang, target_lang=mapped_target_lang)
    )
```

### Redis Integration

#### Stream Usage
- **audio_jobs**: Gateway → STT Workers (job queuing)
- **transcriptions**: STT Workers → Translation Workers (translation pipeline)

#### Consumer Groups
- **stt_workers**: Load balancing across STT worker instances
- **translation_workers**: Load balancing across translation worker instances

#### Pub/Sub Channels
- **results:{client_id}**: Worker results → Gateway → Clients
- Per-client channels for secure result delivery

#### Session Storage
- **session:{client_id}**: Gateway session state persistence
- 1-hour expiration for cleanup

## Data Flow

### Normal Operation Flow

1. **Client Connection**
   - WebSocket connection established to Gateway
   - Client ID assigned, session initialized
   - Redis pub/sub channel subscribed for results

2. **Audio Streaming**
   - Client sends binary audio chunks with metadata
   - Gateway resamples audio to 16kHz PCM
   - Dual VAD detects speech activity
   - Audio accumulated during active speech periods

3. **Speech Detection & Job Creation**
   - Speech state transitions: INACTIVE → ACTIVE → SILENCE
   - Pre-speech buffer (1s) prepended to active speech
   - Audio segments published to Redis `audio_jobs` stream
   - Job-in-flight tracking prevents flooding

4. **STT Processing**
   - STT workers consume jobs via consumer groups
   - Base64 audio decoded and normalized
   - Faster-Whisper transcription with GPU acceleration
   - Results published to client-specific pub/sub channels

5. **Translation Processing** (if enabled)
   - Transcription results published to `transcriptions` stream
   - Translation workers process via consumer groups
   - EasyNMT translation with language mapping
   - Translated results published to client channels

6. **Result Delivery**
   - Gateway receives results via pub/sub
   - Results forwarded to appropriate WebSocket clients
   - Flow control ensures proper sequencing

### Error Handling Flow

- **Network Disconnection**: Graceful cleanup, session preservation
- **Worker Failure**: Job retry via Redis Stream consumer groups
- **Model Errors**: Logged, job marked as failed, metrics updated
- **Memory Issues**: Periodic GC, thread pool limits, resource monitoring

## Technical Specifications

### Performance Targets

| Metric | Target | Current Implementation |
|--------|--------|------------------------|
| End-to-end Latency | <500ms | ~200-400ms typical |
| STT Processing | <200ms | Faster-Whisper optimized |
| Translation Processing | <100ms | EasyNMT cached models |
| Concurrent Clients | 100+ | Horizontal scaling |
| Audio Buffer Size | 10s max | Configurable limits |

### Resource Requirements

#### Minimum Hardware
- **CPU**: 4 cores (for gateway + workers)
- **RAM**: 4GB (base models)
- **Storage**: 10GB (models + logs)
- **Network**: 10Mbps stable connection

#### Recommended Hardware
- **CPU**: 8+ cores
- **RAM**: 16GB+
- **GPU**: NVIDIA with 4GB+ VRAM (for acceleration)
- **Storage**: 50GB SSD

### Supported Audio Formats

- **Sample Rate**: 16kHz (resampled if different)
- **Bit Depth**: 16-bit PCM
- **Channels**: Mono
- **Format**: Raw PCM or WAV container

### Language Support

#### STT Languages (Faster-Whisper)
- English, Spanish, French, German, Italian, Portuguese, Russian
- Japanese, Chinese, Korean, Arabic, Hindi, Thai
- Vietnamese, Dutch, Swedish, Czech, Polish + auto-detection

#### Translation Languages (EasyNMT)
- 100+ languages via Opus-MT models
- Automatic source language detection
- Custom language code mapping system

## Configuration

### Environment Variables

#### Gateway Configuration
```bash
GATEWAY_PORT=5026
HEALTH_PORT=8080
REDIS_URL=redis://localhost:6379
SILENCE_THRESHOLD_SECONDS=2.0
SAMPLE_RATE=16000
WEBRTC_SENSITIVITY=3
SILERO_SENSITIVITY=0.7
PRE_SPEECH_BUFFER_SECONDS=1.0
MAX_QUEUE_DEPTH=100
```

#### STT Worker Configuration
```bash
MODEL_SIZE=large-v3
DEVICE=cuda
BEAM_SIZE=5
VAD_FILTER=true
NORMALIZE_AUDIO=false
HEALTH_PORT=8081
```

#### Translation Worker Configuration
```bash
EASYNMT_MODEL=opus-mt
DEVICE=cuda
HEALTH_PORT=8082
```

### Docker Configuration

#### docker-compose.yml Structure
```yaml
services:
  gateway:
    build: ./gateway
    ports: ["5026:5026", "8080:8080"]
    environment: {...}
    depends_on: [redis]

  stt_worker:
    build: ./stt_worker
    environment: {...}
    runtime: nvidia  # GPU support
    deploy: {replicas: 1}

  translation_worker:
    build: ./translation_worker
    environment: {...}
    deploy: {replicas: 1}

  redis:
    image: redis:7-alpine
    volumes: [redis_data:/data]
```

### Redis Configuration (`infra/redis.conf`)

```redis
# Persistence
appendonly yes
appendfilename "appendonly.aof"
auto-aof-rewrite-percentage 50

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Performance optimization
stream-node-max-bytes 4096
stream-node-max-entries 100
activedefrag yes
```

## Deployment

### Local Development

```bash
# Clone repository
git clone <repository>
cd realtime-speech-microservices

# Start infrastructure
cd infra
docker-compose up --build

# Run client GUI
python client_gui.py

# Run demo tests
cd demos
python demo_client.py --clients 5
```

### Production Deployment

#### Docker Compose Scaling

```bash
# Scale workers horizontally
docker-compose up --scale stt_worker=3 --scale translation_worker=2 --scale gateway=2
```

#### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stt-worker
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: stt-worker
        resources:
          limits:
            nvidia.com/gpu: 1
```

#### GPU Support

```yaml
# docker-compose.override.yml
services:
  stt_worker:
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
      - DEVICE=cuda
```

### Health Checks

All services expose health endpoints:
- **Gateway**: `http://localhost:8080/health`
- **STT Worker**: `http://localhost:8081/health`
- **Translation Worker**: `http://localhost:8082/health`

Health checks include:
- Service uptime and responsiveness
- Redis connectivity
- Model loading status
- Processing metrics and error counts

## Monitoring and Observability

### Metrics Collection

Each service exposes comprehensive metrics:

```json
{
  "instance_id": "gateway-abc123",
  "queue_depth": 5,
  "max_queue_depth": 100,
  "metrics": {
    "clients_connected": 12,
    "audio_chunks_processed": 15420,
    "jobs_published": 234,
    "results_forwarded": 228,
    "errors": 2
  },
  "timestamp": 1699123456.789
}
```

### Logging

#### Log Levels
- **INFO**: Normal operations, client connections, job processing
- **WARNING**: Recoverable errors, retries, resource warnings
- **ERROR**: Critical failures, model loading issues, connection failures
- **DEBUG**: Detailed processing information, state transitions

#### Log Format
```
%(asctime)s [%(name)s] %(levelname)s: %(message)s
```

### Monitoring Commands

```bash
# Service health checks
curl http://localhost:8080/health
curl http://localhost:8081/health
curl http://localhost:8082/health

# View logs
docker-compose logs -f gateway
docker-compose logs -f stt_worker

# Redis monitoring
docker-compose exec redis redis-cli xlen audio_jobs
docker-compose exec redis redis-cli xinfo stream audio_jobs
```

## Performance Characteristics

### Latency Breakdown

| Component | Typical Latency | Notes |
|-----------|-----------------|-------|
| Audio Reception | 5-10ms | WebSocket processing |
| VAD Detection | 10-20ms | Dual VAD processing |
| Job Publishing | 5-15ms | Redis Stream write |
| STT Processing | 100-300ms | GPU: 100ms, CPU: 300ms |
| Translation | 50-150ms | Cached model inference |
| Result Delivery | 5-10ms | Pub/Sub forwarding |
| **Total E2E** | **200-400ms** | **Real-time performance** |

### Throughput Scaling

| Service | Base Throughput | Scaling Factor |
|---------|-----------------|----------------|
| Gateway | 50 concurrent clients | Linear with CPU cores |
| STT Worker | 10-20 jobs/sec | GPU acceleration |
| Translation Worker | 20-50 jobs/sec | CPU-bound |

### Memory Usage

| Service | Base Memory | Scaling Factor |
|---------|-------------|----------------|
| Gateway | 200MB | +50MB per 100 clients |
| STT Worker | 2-4GB | +1GB per GPU worker |
| Translation Worker | 1-2GB | +500MB per worker |

### CPU Usage

| Service | Base CPU | Scaling Notes |
|---------|----------|---------------|
| Gateway | 20-50% | Event-driven, low overhead |
| STT Worker | 80-100% | GPU offload recommended |
| Translation Worker | 50-80% | CPU intensive, scale horizontally |

## Troubleshooting

### Common Issues

#### 1. Broken Pipe During Docker Build
**Symptoms**: Large package downloads fail during build
**Solution**:
```bash
# Enable BuildKit
export DOCKER_BUILDKIT=1
# Use increased timeout and retries
docker build --memory=4g --build-arg BUILDKIT_INLINE_CACHE=1 stt_worker/
```

#### 2. Model Download Failures
**Symptoms**: Faster-Whisper model download hangs or fails
**Solution**:
```bash
# Pre-download models
docker run --rm speech/stt-worker python -c "import faster_whisper; faster_whisper.WhisperModel('base')"
```

#### 3. GPU Memory Issues
**Symptoms**: CUDA out of memory errors
**Solutions**:
- Reduce `MAX_BATCH_SIZE` in environment
- Use smaller model: `MODEL_SIZE=small`
- Scale to fewer concurrent workers

#### 4. Redis Connection Issues
**Symptoms**: Connection timeouts, lost messages
**Solutions**:
- Check Redis container health: `docker-compose ps redis`
- Verify network connectivity
- Check Redis logs: `docker-compose logs redis`
- Adjust Redis `timeout` and `tcp-keepalive` settings

#### 5. High Latency Issues
**Symptoms**: End-to-end latency >500ms
**Solutions**:
- Scale STT workers: `docker-compose up --scale stt_worker=3`
- Check GPU utilization and memory
- Monitor Redis queue depth
- Adjust silence threshold for more frequent job sending

#### 6. Memory Leaks in Translation Worker
**Symptoms**: Increasing memory usage over time
**Solutions**:
- Translation worker automatically runs GC every 5 minutes
- Monitor with `psutil` integration
- Restart workers periodically if needed
- Check thread pool executor usage

### Debug Commands

```bash
# View all service logs
docker-compose logs -f

# Check container resource usage
docker stats

# Inspect Redis streams
docker-compose exec redis redis-cli xinfo stream audio_jobs
docker-compose exec redis redis-cli xlen audio_jobs

# Monitor Redis commands
docker-compose exec redis redis-cli monitor

# Check service connectivity
curl -f http://localhost:8080/health
curl -f http://localhost:8081/health
curl -f http://localhost:8082/health
```

### Performance Tuning

#### STT Worker Optimization
```bash
# Increase batch size for GPU efficiency
export MAX_BATCH_SIZE=8

# Adjust beam size (accuracy vs speed tradeoff)
export BEAM_SIZE=3

# Use smaller model for faster processing
export MODEL_SIZE=medium
```

#### Gateway Optimization
```bash
# Reduce silence threshold for more responsive processing
export SILENCE_THRESHOLD_SECONDS=0.8

# Adjust pre-speech buffer
export PRE_SPEECH_BUFFER_SECONDS=0.5
```

#### Redis Optimization
```redis
# Increase memory limit
maxmemory 1gb

# Adjust persistence settings
auto-aof-rewrite-min-size 128mb
```

This technical documentation provides comprehensive coverage of the real-time speech transcription and translation microservices system. The architecture is designed for horizontal scalability, low-latency processing, and robust error handling in production environments.
