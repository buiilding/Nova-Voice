# Real-Time Speech Transcription and Translation Microservices

A horizontally scalable, Dockerized microservice pipeline for real-time speech transcription and translation using Faster-Whisper and NLLB models.

## 🏗️ Architecture Overview

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

### Service Components

- **Gateway Service** (Port 5026): WebSocket server with dual VAD (WebRTC + Silero), session state persistence in Redis, audio chunking and streaming
- **STT Workers** (Port 8081): Consume audio segments from Redis Streams, transcribe using Faster-Whisper with GPU support
- **Translation Workers** (Port 8082): Consume transcriptions from Redis, translate using EasyNMT with memory management
- **Redis** (Port 6379): Message queue with Streams + consumer groups, pub/sub for real-time results, session state storage
- **Client GUI** (PyQt5): Multi-language interface with live subtitles, typing simulation, and audio device selection

### Key Features

- ✅ **Horizontal Scaling**: Scale workers independently with `docker-compose up --scale`
- ✅ **Stateless Gateway**: Session state persisted in Redis for multi-instance deployment
- ✅ **Dual VAD System**: WebRTC + Silero VAD for accurate speech detection
- ✅ **Real-time Streaming**: Progressive audio chunks for low-latency transcription
- ✅ **GPU Support**: CUDA acceleration for Faster-Whisper transcription
- ✅ **Multi-language Support**: 15+ languages with automatic language detection
- ✅ **Live Subtitles**: Semi-transparent overlay with real-time transcription display
- ✅ **Typing Simulation**: Automated keyboard input with smart text replacement
- ✅ **Audio Device Selection**: Microphone and system audio capture support
- ✅ **Health Monitoring**: HTTP endpoints with metrics collection
- ✅ **Memory Management**: Automatic GC and resource cleanup in translation workers

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- 4GB+ RAM for base models
- NVIDIA GPU (optional, for acceleration)

### 1. Clone and Setup

```bash
git clone <repository>
cd realtime-speech-microservices
```

### 2. Start Services

```bash
cd infra
docker-compose up --build
```

This starts:

- Redis (message queue)
- 1 Gateway instance
- 1 STT worker
- 1 Translation worker

### 3. Scale Workers

```bash
# Scale STT workers to 3 instances
docker-compose up --scale stt_worker=3

# Scale translation workers to 2 instances
docker-compose up --scale translation_worker=2

# Scale gateways for more concurrent clients
docker-compose up --scale gateway=2
```

### 4. Test the System

```bash
# Generate test audio files
cd demos
python generate_audio.py

# Run the PyQt5 client GUI
python client_gui.py

# Run concurrent client test
python demo_client.py --clients 10

# Run load test
python demo_client.py --load-test --clients 5 --batches 3
```

## 🖥️ Client GUI

The project includes a full-featured PyQt5 client GUI for easy interaction:

### Features

- **Voice Typing Mode**: Real-time speech-to-text with automated keyboard input
- **Live Subtitle Mode**: Semi-transparent overlay displaying transcription in real-time
- **Audio Device Selection**: Choose between microphone input or system audio capture
- **Multi-language Support**: 15+ languages with source/target language selection
- **Real-time Language Switching**: Change languages during active transcription
- **Dual Output Modes**: Switch between typing simulation and live subtitles without reconnecting

### GUI Usage

```bash
# Launch the client GUI
python client_gui.py
```

1. **Select Audio Source**: Choose microphone or system output device
2. **Choose Languages**: Select source and target languages from dropdown
3. **Start Mode**: Click "Voice Typing" or "Live Subtitle" button
4. **Control**: Click the active button again to stop

### Live Subtitles

- Displays transcription in a semi-transparent overlay
- Click-through enabled (doesn't interfere with other applications)
- Single sentence display to prevent text accumulation
- Positioned at bottom-center of screen

### Typing Simulation

- Automatically types transcribed text into active application
- Smart text replacement (undoes previous text before pasting new)
- Handles punctuation and spacing intelligently
- Works with any application that accepts keyboard input

## 📋 Configuration

### Environment Variables

Create `.env` file in `infra/` directory:

```bash
# Copy example configuration
cp env.example .env

# Edit as needed
nano .env
```

Key settings:

| Variable                      | Default  | Description                                              |
| ----------------------------- | -------- | -------------------------------------------------------- |
| **Gateway Configuration**    |         |                                                         |
| `GATEWAY_PORT`               | `5026` | WebSocket port for client connections                   |
| `HEALTH_PORT`                | `8080` | HTTP health check port                                  |
| `REDIS_URL`                  | `redis://localhost:6379` | Redis connection URL                    |
| `SILENCE_THRESHOLD_SECONDS`  | `2.0`  | Silence duration to end speech                          |
| `SAMPLE_RATE`                | `16000` | Audio sample rate                                       |
| `WEBRTC_SENSITIVITY`         | `3`    | WebRTC VAD sensitivity (0-3, lower=more sensitive)     |
| `SILERO_SENSITIVITY`         | `0.7`  | Silero VAD sensitivity (0.0-1.0, lower=more sensitive) |
| `PRE_SPEECH_BUFFER_SECONDS`  | `1.0`  | Audio buffer before speech detection                    |
| `MAX_QUEUE_DEPTH`            | `100`  | Maximum Redis queue depth for backpressure             |
| **STT Worker Configuration** |         |                                                         |
| `MODEL_SIZE`                 | `large-v3` | Whisper model size (tiny, base, small, medium, large-v3) |
| `DEVICE`                     | `cuda` | Computing device (cuda/cpu)                             |
| `BEAM_SIZE`                  | `5`    | Beam search size for transcription                      |
| `VAD_FILTER`                 | `true` | Enable VAD filtering                                    |
| `NORMALIZE_AUDIO`            | `false`| Audio normalization                                     |
| **Translation Worker Configuration** |     |                                                         |
| `EASYNMT_MODEL`              | `opus-mt` | EasyNMT model for translation                          |
| `DEVICE`                     | `cuda` | Computing device (cuda/cpu)                             |

### GPU Support

For GPU acceleration:

1. **Using docker-compose.override.yml:**

   ```yaml
   services:
     stt_worker:
       runtime: nvidia
       environment:
         - NVIDIA_VISIBLE_DEVICES=all
   ```
2. **Using --gpus flag:**

   ```bash
   docker-compose up
   # Then scale with GPU
   docker run --gpus all <stt_worker_image>
   ```

## 🔧 Usage Examples

### Basic Client Connection

```python
import asyncio
import websockets
import json

async def test_client():
    async with websockets.connect("ws://localhost:5026") as ws:
        # Send audio data (implement audio streaming logic)
        # Receive transcription results in real-time
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "realtime":
                print(f"Transcription: {data['text']}")
                print(f"Translation: {data['translation']}")

asyncio.run(test_client())
```

### Monitoring

```bash
# Check service health
curl http://localhost:8080/health  # Gateway health
curl http://localhost:8081/health  # STT Worker health
curl http://localhost:8082/health  # Translation Worker health

# Check service metrics
curl http://localhost:8080/metrics  # Gateway metrics
curl http://localhost:8081/metrics  # STT Worker metrics
curl http://localhost:8082/metrics  # Translation Worker metrics

# View logs
docker-compose logs -f gateway
docker-compose logs -f stt_worker
docker-compose logs -f translation_worker

# Monitor Redis
docker-compose exec redis redis-cli xlen audio_jobs
docker-compose exec redis redis-cli xinfo stream audio_jobs
```

## 🧪 Testing

### Demo Scripts

```bash
cd demos

# Generate test audio
python generate_audio.py

# Single client test
python demo_client.py --clients 1

# Concurrent clients test
python demo_client.py --clients 10

# Load test with batches
python demo_client.py --load-test --clients 5 --batches 5
```

### Performance Metrics

The demo client reports:

- **Latency**: Time from audio send to first result
- **Throughput**: Results per second across all clients
- **Success Rate**: Percentage of successful transcriptions
- **Worker Distribution**: Which workers processed jobs

## 🔍 Architecture Details

### Message Flow

1. **Client → Gateway**: WebSocket audio streaming
2. **Gateway → Redis**: Audio segments published to `audio_jobs` stream
3. **STT Worker → Redis**: Consumes jobs, publishes transcription to pub/sub
4. **Translation Worker → Redis**: Consumes transcriptions, publishes translations
5. **Gateway → Client**: Forwards results via WebSocket

### Redis Usage

- **Streams**: `audio_jobs` for reliable job queuing
- **Consumer Groups**: `stt_workers`, `translation_workers` for load balancing
- **Pub/Sub**: `results:{client_id}` for result delivery
- **Hashes**: `session:{client_id}` for gateway session state

### Scaling Strategy

| Service            | Scaling Factor     | Resource Usage            |
| ------------------ | ------------------ | ------------------------- |
| Gateway            | Client connections | Low CPU, low memory       |
| STT Worker         | Audio processing   | High CPU/GPU, high memory |
| Translation Worker | Text processing    | Medium CPU, low memory    |
| Redis              | Message throughput | Medium CPU, high memory   |

## 🚀 Production Deployment

### Prerequisites for Production

**CRITICAL: Your codebase is NOT ready for production deployment.** Before proceeding with any production setup, you must implement the following security and operational requirements:

#### 🔴 BLOCKERS (Must Fix Before Production)

1. **Implement Proper Authentication & Authorization**
   - Current JWT implementation is incomplete and insecure
   - No rate limiting on authentication endpoints
   - Missing token refresh mechanism
   - No account lockout or password policies

2. **Add TLS/SSL Encryption**
   - All WebSocket connections must use WSS (not WS)
   - All HTTP endpoints must use HTTPS
   - Implement proper SSL certificate management

3. **Security Hardening**
   - Environment variables exposed in logs and error messages
   - No input validation on WebSocket messages
   - Missing CSRF protection
   - No security headers (CSP, HSTS, etc.)

4. **Database/Data Persistence**
   - Redis is used for both caching and data storage - not suitable for production
   - No backup strategy for user data
   - No data retention policies
   - Missing database migrations and schema versioning

5. **Error Handling & Monitoring**
   - No centralized logging system
   - Missing error tracking (Sentry, etc.)
   - No alerting system for failures
   - Insufficient metrics collection

#### 🟡 HIGH PRIORITY (Fix Before Beta)

6. **Add Comprehensive Testing**
   - No unit tests found in codebase
   - No integration tests
   - No load testing framework
   - No CI/CD pipeline

7. **Resource Management**
   - No memory limits on containers
   - No CPU limits on containers
   - No auto-scaling policies
   - Missing resource monitoring

8. **Operational Requirements**
   - No health check endpoints on all services
   - Missing graceful shutdown handling
   - No configuration management system
   - Missing secret management (Vault, etc.)

### Recommended Production Architecture

```
Internet → Cloudflare (WAF + DDoS) → Load Balancer → Gateway Services
                                      ↓
                               Redis Cluster (with persistence)
                                      ↓
                            STT Workers ←→ Translation Workers
```

### Kubernetes Production Deployment

```yaml
# Gateway Deployment with proper security
apiVersion: apps/v1
kind: Deployment
metadata:
  name: speech-gateway
  labels:
    app: speech-gateway
spec:
  replicas: 3
  selector:
    matchLabels:
      app: speech-gateway
  template:
    metadata:
      labels:
        app: speech-gateway
    spec:
      containers:
      - name: gateway
        image: your-registry/speech-gateway:latest
        ports:
        - containerPort: 5026
          name: websocket
        - containerPort: 8080
          name: health
        env:
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: redis-secret
              key: redis-url
        - name: JWT_SECRET
          valueFrom:
            secretKeyRef:
              name: jwt-secret
              key: jwt-secret
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
            - ALL
```

### Redis Production Configuration

```yaml
# Redis with persistence and clustering
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
spec:
  serviceName: redis
  replicas: 3
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        command:
        - redis-server
        - /etc/redis/redis.conf
        volumeMounts:
        - name: redis-config
          mountPath: /etc/redis
        - name: redis-data
          mountPath: /data
        resources:
          limits:
            memory: "1Gi"
            cpu: "500m"
          requests:
            memory: "512Mi"
            cpu: "250m"
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
      - name: redis-data
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
data:
  redis.conf: |
    # Production Redis configuration
    bind 0.0.0.0
    port 6379
    timeout 300
    tcp-keepalive 300
    maxmemory 512mb
    maxmemory-policy allkeys-lru
    appendonly yes
    appendfilename "appendonly.aof"
    auto-aof-rewrite-percentage 50
    save 900 1
    save 300 10
    save 60 10000
    cluster-enabled yes
    cluster-config-file nodes.conf
    cluster-node-timeout 5000
```

## 🔒 Security Considerations

### CURRENT SECURITY STATUS: INADEQUATE FOR PRODUCTION

**Your application currently has critical security vulnerabilities that must be addressed before any production deployment.**

### Immediate Security Requirements

#### 1. **Transport Layer Security (TLS/SSL)**
```python
# REQUIRED: Update WebSocket connections to use WSS
const ws = new WebSocket('wss://your-domain.com:5026');  # Not ws://

# REQUIRED: Update HTTP endpoints to use HTTPS
const response = await fetch('https://your-domain.com:8080/auth');
```

#### 2. **Authentication & Authorization**
- **Current Issue**: JWT implementation is incomplete and insecure
- **Required**: Implement proper OAuth 2.0 flow with PKCE
- **Required**: Add token refresh mechanism
- **Required**: Implement rate limiting on auth endpoints

#### 3. **Input Validation & Sanitization**
- **Current Issue**: No validation on WebSocket messages
- **Required**: Validate all incoming data structures
- **Required**: Implement message size limits
- **Required**: Add content-type validation

#### 4. **Security Headers**
```javascript
// REQUIRED: Add security headers to all HTTP responses
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  res.setHeader('Content-Security-Policy', "default-src 'self'");
  next();
});
```

#### 5. **Environment Variable Security**
- **Current Issue**: Sensitive data logged in debug output
- **Required**: Never log secrets or tokens
- **Required**: Use secret management system (Vault, AWS Secrets Manager, etc.)
- **Required**: Implement environment variable validation

#### 6. **Database Security**
- **Current Issue**: Redis used for both caching and data storage
- **Required**: Use proper database (PostgreSQL/MySQL) for user data
- **Required**: Implement database encryption at rest
- **Required**: Add database backup and recovery procedures

### Network Security Architecture

```
Internet → Cloudflare WAF → Load Balancer → API Gateway → Services
                      ↓              ↓              ↓
                DDoS Protection  TLS Termination  Authentication
```

### Access Control Implementation

```python
# REQUIRED: Implement proper token validation
from flask_limiter import Limiter
from flask_jwt_extended import JWTManager, jwt_required

limiter = Limiter(app)
jwt = JWTManager(app)

@app.route('/auth/login', methods=['POST'])
@limiter.limit("10 per minute")
def login():
    # Implement proper OAuth flow with PKCE
    pass

@app.route('/api/speech', methods=['POST'])
@jwt_required()
@limiter.limit("100 per minute")
def speech_endpoint():
    # Validate authenticated user
    current_user = get_jwt_identity()
    # Implement authorization checks
    pass
```

### Container Security

```yaml
# REQUIRED: Security context for all containers
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-gateway
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 2000
      containers:
      - name: gateway
        securityContext:
          allowPrivilegeEscalation: false
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        resources:
          limits:
            memory: "512Mi"
            cpu: "500m"
          requests:
            memory: "256Mi"
            cpu: "250m"
```

### Monitoring & Incident Response

#### Required Security Monitoring
- **Log all authentication attempts** (success/failure)
- **Monitor for suspicious patterns** (brute force, unusual traffic)
- **Implement audit logging** for all user actions
- **Set up alerting** for security events

#### Incident Response Plan
1. **Detection**: Automated monitoring alerts
2. **Assessment**: Security team investigates
3. **Containment**: Isolate affected systems
4. **Recovery**: Restore from backups
5. **Lessons Learned**: Update security measures

## 🐛 Troubleshooting

### Common Issues

1. **Broken Pipe Error During Docker Build**

   This typically occurs when downloading large packages like PyTorch. The fixes applied include:
   - Added `--timeout=300 --retries=10` to pip installs
   - Enabled Docker BuildKit for better network handling
   - Switched to CPU-only PyTorch versions for smaller downloads

   **Manual Fix:**
   ```bash
   # Enable BuildKit
   export DOCKER_BUILDKIT=1
   COMPOSE_DOCKER_CLI_BUILD=1

   # Build with increased memory
   docker build --memory=4g --build-arg BUILDKIT_INLINE_CACHE=1 stt_worker/

   # Alternative: Build step by step
   docker build --target base stt_worker/
   docker build stt_worker/
   ```

2. **Model Download Failures**

   ```bash
   # Pre-download models
   docker run --rm speech/stt-worker python -c "import faster_whisper; faster_whisper.WhisperModel('base')"
   ```

3. **GPU Memory Issues**

   ```bash
   # Reduce batch size
   export MAX_BATCH_SIZE=2
   # Or use smaller model
   export MODEL_SIZE=small
   ```

4. **Redis Connection Issues**

   ```bash
   # Check Redis health
   docker-compose ps redis
   docker-compose logs redis
   ```

5. **Port Conflicts**

   ```bash
   # Change ports in .env
   GATEWAY_PORT=5027
   HEALTH_PORT=8081
   ```

### Debug Commands

```bash
# View all logs
docker-compose logs -f

# Check container resource usage
docker stats

# Inspect Redis streams
docker-compose exec redis redis-cli xinfo stream audio_jobs

# Monitor Redis commands
docker-compose exec redis redis-cli monitor
```

## 📊 Performance Tuning

### STT Worker Optimization

```bash
# Increase batch size for GPU efficiency
export MAX_BATCH_SIZE=8

# Adjust batch timeout
export BATCH_TIMEOUT_MS=200

# Use larger model for better accuracy
export MODEL_SIZE=medium
```

### Gateway Optimization

```bash
# Adjust silence threshold
export SILENCE_THRESHOLD_SECONDS=0.8

# Change audio chunk size
export STT_SEND_INTERVAL=0.5
```

### Redis Optimization

```yaml
# Redis configuration
maxmemory 1gb
maxmemory-policy allkeys-lru
tcp-keepalive 300
```

## 📋 Production Readiness Checklist

### 🔴 CRITICAL BLOCKERS (Must Fix)

- [ ] **Implement proper authentication system**
  - Replace incomplete JWT with OAuth 2.0 + PKCE
  - Add token refresh mechanism
  - Implement rate limiting on auth endpoints
  - Add account lockout policies

- [ ] **Add TLS/SSL encryption**
  - Convert all WS connections to WSS
  - Convert all HTTP to HTTPS
  - Implement SSL certificate management
  - Update all client code to use secure protocols

- [ ] **Security hardening**
  - Remove environment variables from logs
  - Add input validation on all endpoints
  - Implement security headers (CSP, HSTS, etc.)
  - Add CSRF protection

- [ ] **Database migration**
  - Replace Redis data storage with proper database
  - Implement user data persistence
  - Add backup and recovery procedures
  - Create data migration scripts

- [ ] **Error handling & monitoring**
  - Implement centralized logging (ELK stack)
  - Add error tracking (Sentry/DataDog)
  - Create alerting system
  - Add comprehensive metrics collection

### 🟡 HIGH PRIORITY (Fix Before Beta)

- [ ] **Add comprehensive testing**
  - Unit tests for all components
  - Integration tests for microservices
  - Load testing framework
  - CI/CD pipeline with automated testing

- [ ] **Resource management**
  - Add memory/CPU limits to containers
  - Implement auto-scaling policies
  - Add resource monitoring and alerting
  - Performance optimization and profiling

- [ ] **Operational requirements**
  - Implement graceful shutdown handling
  - Add configuration management system
  - Implement secret management (Vault/KMS)
  - Create deployment automation scripts

### 🟢 MEDIUM PRIORITY (Nice to Have)

- [ ] **Documentation updates**
  - API documentation (OpenAPI/Swagger)
  - Deployment guides for different platforms
  - Troubleshooting runbooks
  - Performance tuning guides

- [ ] **Advanced features**
  - Multi-region deployment support
  - Advanced caching strategies
  - API rate limiting per user
  - Advanced analytics and reporting

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

### Development Setup

```bash
# ⚠️  WARNING: This setup is for DEVELOPMENT ONLY
# ⚠️  DO NOT use this configuration in production

# Install Python dependencies
pip install -r gateway/requirements.txt
pip install -r stt_worker/requirements.txt
pip install -r translation_worker/requirements.txt

# Install client GUI dependencies
pip install PyQt5 pyperclip pyaudio

# Start Redis (development only - not for production)
docker run -d -p 6379:6379 redis:7-alpine

# Run services locally (development only)
python gateway/gateway.py              # WebSocket gateway on port 5026
python stt_worker/worker.py           # STT worker on port 8081
python translation_worker/worker.py   # Translation worker on port 8082

# Run the client GUI
python client_gui.py

# Or run demo client
cd demos && python demo_client.py --clients 1
```

### Production Development Guidelines

**NEVER deploy the development setup to production.** Production requires:

1. **Container orchestration** (Kubernetes/Docker Swarm)
2. **Load balancing** with health checks
3. **TLS termination** at the edge
4. **Secret management** system
5. **Monitoring and alerting** stack
6. **Backup and disaster recovery** procedures
7. **Security hardening** of all components
8. **Comprehensive testing** pipeline

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) for speech transcription
- [NLLB](https://github.com/facebookresearch/fairseq/tree/nllb) for translation
- [Redis](https://redis.io/) for reliable messaging
- [WebSockets](https://websockets.readthedocs.io/) for real-time communication

