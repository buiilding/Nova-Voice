# Infrastructure Setup

This directory contains the Docker and infrastructure configuration for the speech microservices.

## Quick Start

1. **Build and start all services:**
   ```bash
   cd infra
   docker-compose up --build
   ```

2. **Scale workers horizontally:**
   ```bash
   # Scale STT workers to 3 instances
   docker-compose up --scale stt_worker=3

   # Scale translation workers to 2 instances
   docker-compose up --scale translation_worker=2

   # Scale gateways to 2 instances
   docker-compose up --scale gateway=2
   ```

3. **Check service health:**
   ```bash
   # Gateway health
   curl http://localhost:8080/health

   # STT worker health (first instance)
   curl http://localhost:8081/health

   # Translation worker health
   curl http://localhost:8082/health

   # Redis info
   docker-compose exec redis redis-cli info
   ```

## Configuration

### Environment Variables

Copy `env.example` to `.env` and modify as needed:

```bash
cp env.example .env
```

Key configuration options:

- **MODEL_SIZE**: Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v1`)
- **DEVICE**: Computing device (`cuda` for GPU, `cpu` for CPU)
- **MAX_BATCH_SIZE**: Number of audio segments to batch together
- **SILENCE_THRESHOLD_SECONDS**: How long of silence ends a speech session
- **USE_STUB_TRANSLATION**: Use stub translation instead of real NLLB

### GPU Support

For GPU acceleration of STT workers:

1. **Using docker-compose.override.yml:**
   ```yaml
   services:
     stt_worker:
       runtime: nvidia
       environment:
         - NVIDIA_VISIBLE_DEVICES=all
         - DEVICE=cuda
   ```

2. **Using --gpus flag:**
   ```bash
   docker-compose up
   # Then scale with GPU support
   docker run --gpus all <stt_worker_image>
   ```

## Service Architecture

```
Clients (WebSocket) → Gateway → Redis Streams → STT Workers
                                      ↓
                           Redis Pub/Sub → Translation Workers
                                      ↓
                           Redis Pub/Sub → Gateway → Clients
```

### Redis Streams Usage

- **audio_jobs**: Audio segments from gateway to STT workers
- **Consumer Groups**: `stt_workers` and `translation_workers` for load balancing
- **Pub/Sub Channels**: `results:{client_id}` for forwarding results

### Scaling Strategy

- **Gateway**: Stateless, scale horizontally for more concurrent clients
- **STT Workers**: CPU/GPU intensive, scale based on transcription load
- **Translation Workers**: CPU intensive, scale based on translation load
- **Redis**: Single instance with persistence for development

## Monitoring and Debugging

### Logs

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f gateway
docker-compose logs -f stt_worker
docker-compose logs -f translation_worker
```

### Redis Monitoring

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Monitor Redis commands
docker-compose exec redis redis-cli monitor

# Check stream lengths
docker-compose exec redis redis-cli xlen audio_jobs

# Check consumer groups
docker-compose exec redis redis-cli xinfo groups audio_jobs
```

### Performance Tuning

1. **STT Worker Batching:**
   - Increase `MAX_BATCH_SIZE` for better GPU utilization
   - Adjust `BATCH_TIMEOUT_MS` based on latency requirements

2. **Gateway Backpressure:**
   - Monitor `MAX_QUEUE_DEPTH` to prevent memory issues
   - Scale gateways if queue depth consistently high

3. **Redis Memory:**
   - Monitor Redis memory usage with `INFO memory`
   - Adjust `maxmemory` in `redis.conf` as needed

## Troubleshooting

### Common Issues

1. **Model Download Failures:**
   ```
   # Pre-download models locally
   pip install faster-whisper
   python -c "import faster_whisper; faster_whisper.WhisperModel('base')"
   ```

2. **GPU Memory Issues:**
   ```
   # Reduce batch size or model size
   export MAX_BATCH_SIZE=2
   export MODEL_SIZE=small
   ```

3. **Port Conflicts:**
   ```
   # Change ports in docker-compose.yml or .env
   export GATEWAY_PORT=5027
   export HEALTH_PORT=8081
   ```

4. **Redis Connection Issues:**
   ```
   # Check Redis health
   docker-compose ps redis
   docker-compose logs redis
   ```

### Health Checks

All services expose health endpoints:
- Gateway: `http://localhost:8080/health`
- STT Worker: `http://localhost:8081/health`
- Translation Worker: `http://localhost:8082/health`

Health checks include:
- Service uptime
- Redis connectivity
- Model loading status
- Processing metrics
- Error counts

## Production Considerations

1. **Redis Cluster**: Use Redis Cluster for high availability
2. **Load Balancing**: Use external load balancer for gateways
3. **Monitoring**: Integrate with Prometheus/Grafana
4. **Security**: Add TLS, authentication, and network policies
5. **Resource Limits**: Set CPU/memory limits in docker-compose.yml
6. **Backup**: Implement Redis backup strategy

