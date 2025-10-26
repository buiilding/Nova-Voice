# Shared Modules Documentation

Documentation for the shared utility modules used across all speech transcription microservices.

## 📁 Module Overview

The `backend/shared/` directory contains reusable components that provide common functionality across all services (Gateway, STT Worker, Translation Worker).

```
backend/shared/
├── __init__.py
├── health_server.py     # HTTP health check and metrics server
├── redis_consumer.py     # Redis Streams consumer with consumer groups
└── metrics.py           # Metrics collection and reporting utilities
```

## 🏥 Health Server (`health_server.py`)

### Purpose
Provides standardized HTTP health check and metrics endpoints for all worker services. Handles CORS setup, server lifecycle management, and standardized response formats.

### Features
- **Health Checks**: `/health` endpoint with service status
- **Metrics**: `/metrics` endpoint with detailed performance data
- **CORS Support**: Automatic CORS header handling
- **Async/Await**: Full asyncio support for non-blocking operations
- **Error Handling**: Comprehensive exception handling with proper HTTP status codes

### Usage

```python
from shared.health_server import HealthServer
import logging

# Initialize health server
health_server = HealthServer(
    instance_id="gateway-001",
    port=8080,
    logger=logging.getLogger("gateway"),
    get_health_data=lambda: {
        "clients_connected": 5,
        "redis_connected": True,
        "uptime_seconds": 3600
    },
    get_metrics_data=lambda: {
        "requests_processed": 1500,
        "avg_response_time_ms": 45.2,
        "error_rate": 0.02
    }
)

# Start server (typically in main())
await health_server.start_server()
```

### Endpoints

#### `/health` (GET)
Returns basic health status information.

**Response:**
```json
{
  "status": "healthy",
  "instance_id": "gateway-001",
  "timestamp": 1640995200.789,
  "clients_connected": 5,
  "redis_connected": true,
  "uptime_seconds": 3600
}
```

#### `/metrics` (GET)
Returns detailed performance metrics.

**Response:**
```json
{
  "instance_id": "gateway-001",
  "timestamp": 1640995200.789,
  "clients_connected": 5,
  "total_clients_served": 150,
  "jobs_sent": 500,
  "results_received": 495,
  "errors": 2,
  "uptime_seconds": 3600,
  "redis_operations": 1200,
  "audio_bytes_processed": 5242880,
  "avg_processing_latency_ms": 45.2
}
```

### Health Status Values
- `"healthy"`: Service is functioning normally
- `"unhealthy"`: Service has critical issues (returns HTTP 500)

## 🔄 Redis Consumer (`redis_consumer.py`)

### Purpose
Provides a standardized way to consume jobs from Redis Streams using consumer groups. Handles connection management, message processing, error handling, and automatic reconnection.

### Features
- **Consumer Groups**: Load balancing across multiple worker instances
- **Stream Processing**: Reliable message processing with ACK/NACK
- **Error Handling**: Automatic retry logic and error reporting
- **Connection Management**: Auto-reconnection on Redis failures
- **Async Processing**: Full asyncio support for high performance

### Key Concepts

#### Consumer Groups
Redis Streams use consumer groups to distribute work across multiple consumers. Each worker instance joins a consumer group and receives a subset of messages.

#### Message Processing
Messages are processed asynchronously with proper error handling. Failed messages can be retried or moved to a dead letter queue.

### Usage

```python
from shared.redis_consumer import RedisStreamConsumer
import logging

async def process_transcription_job(message_id, message_data):
    """Process a single transcription job"""
    audio_data = message_data['audio']
    client_id = message_data['client_id']

    # Process audio and return result
    transcription = await transcribe_audio(audio_data)
    return transcription

# Initialize consumer
consumer = RedisStreamConsumer(
    redis_url="redis://localhost:6379",
    stream_name="audio_jobs",
    consumer_group="stt_workers",
    consumer_id="stt-worker-001",
    logger=logging.getLogger("stt-consumer"),
    message_processor=process_transcription_job
)

# Connect and start consuming
await consumer.connect()
await consumer.start_consuming()
```

### Message Flow

```
Redis Stream ── Consumer Group ── Worker Instances
     │                │                │
     ├─ Message 1 ── Consumer A ── Instance 1
     ├─ Message 2 ── Consumer B ── Instance 2
     ├─ Message 3 ── Consumer A ── Instance 1
     └─ Message 4 ── Consumer C ── Instance 3
```

### Error Handling

The consumer automatically handles:
- **Connection Failures**: Auto-reconnection with exponential backoff
- **Message Processing Errors**: Logging and optional retry logic
- **Consumer Group Issues**: Automatic group creation and management
- **Stream Issues**: Pending message handling and recovery

## 📊 Metrics (`metrics.py`)

### Purpose
Provides standardized metrics collection and reporting utilities. Tracks performance indicators, error rates, and operational statistics across all services.

### Features
- **Counter Metrics**: Incrementing counters for events
- **Timing Metrics**: Duration tracking for operations
- **Gauge Metrics**: Point-in-time measurements
- **Error Tracking**: Exception counting and categorization
- **Memory Usage**: Automatic memory monitoring
- **Custom Metrics**: Extensible metric collection

### Usage

```python
from shared.metrics import WorkerMetrics
import time

# Initialize metrics
metrics = WorkerMetrics(instance_id="stt-worker-001")

# Track job processing
metrics.increment_counter("jobs_processed")
start_time = time.time()

try:
    # Process job
    result = await process_job(job_data)
    metrics.increment_counter("jobs_successful")

    # Track processing time
    duration = time.time() - start_time
    metrics.record_duration("job_processing_time", duration)

except Exception as e:
    metrics.increment_counter("jobs_failed")
    metrics.increment_counter(f"errors.{type(e).__name__}")
    raise

# Get metrics data for health endpoints
metrics_data = metrics.get_metrics_data()
```

### Available Metrics Types

#### Counters
```python
metrics.increment_counter("jobs_processed")        # Increment by 1
metrics.increment_counter("bytes_processed", 1024) # Increment by value
```

#### Timings
```python
start = time.time()
# ... operation ...
duration = time.time() - start
metrics.record_duration("operation_time", duration)
```

#### Gauges
```python
metrics.set_gauge("active_connections", 5)        # Set absolute value
metrics.update_gauge("memory_usage_mb", 256)      # Update current value
```

### Predefined Metrics by Service

#### Gateway Service
- `clients_connected`: Current active WebSocket connections
- `jobs_sent`: Total audio jobs published to Redis
- `results_received`: Total transcription results received
- `audio_bytes_processed`: Total audio data processed
- `avg_processing_latency_ms`: Average job processing latency

#### STT Worker
- `jobs_processed`: Total transcription jobs completed
- `successful_transcriptions`: Jobs completed without errors
- `failed_transcriptions`: Jobs that failed
- `avg_transcription_time_ms`: Average transcription duration
- `model_inference_time_ms`: Time spent in model inference
- `audio_duration_processed_seconds`: Total audio duration processed

#### Translation Worker
- `jobs_processed`: Total translation jobs completed
- `successful_translations`: Jobs completed without errors
- `failed_translations`: Jobs that failed
- `avg_translation_time_ms`: Average translation duration
- `text_chars_processed`: Total characters translated
- `cache_hit_ratio`: Translation cache effectiveness

## 🔧 Integration Examples

### Gateway Service Integration

```python
from shared.health_server import HealthServer
from shared.metrics import WorkerMetrics

class GatewayService:
    def __init__(self):
        self.metrics = WorkerMetrics("gateway-001")
        self.health_server = HealthServer(
            instance_id="gateway-001",
            port=8080,
            logger=self.logger,
            get_health_data=self._get_health_data,
            get_metrics_data=self.metrics.get_metrics_data
        )

    def _get_health_data(self):
        return {
            "clients_connected": len(self.connected_clients),
            "redis_connected": self.redis_connected,
            "uptime_seconds": time.time() - self.start_time,
            **self.metrics.get_basic_health_data()
        }
```

### Worker Service Integration

```python
from shared.redis_consumer import RedisStreamConsumer
from shared.health_server import HealthServer
from shared.metrics import WorkerMetrics

class STTWorker:
    def __init__(self):
        self.metrics = WorkerMetrics("stt-worker-001")

        # Initialize Redis consumer
        self.consumer = RedisStreamConsumer(
            redis_url=os.getenv("REDIS_URL"),
            stream_name="audio_jobs",
            consumer_group="stt_workers",
            consumer_id=f"stt-{uuid.uuid4().hex[:8]}",
            logger=self.logger,
            message_processor=self.process_job
        )

        # Initialize health server
        self.health_server = HealthServer(
            instance_id="stt-worker-001",
            port=int(os.getenv("HEALTH_PORT", 8081)),
            logger=self.logger,
            get_health_data=self._get_health_data,
            get_metrics_data=self.metrics.get_metrics_data
        )

    async def process_job(self, message_id, message_data):
        """Process transcription job"""
        self.metrics.increment_counter("jobs_processed")
        start_time = time.time()

        try:
            # Process audio
            result = await self.transcribe_audio(message_data["audio"])

            # Record success
            self.metrics.increment_counter("successful_transcriptions")
            duration = time.time() - start_time
            self.metrics.record_duration("transcription_time", duration)

            return result

        except Exception as e:
            self.metrics.increment_counter("failed_transcriptions")
            raise
```

## 🧪 Testing Shared Modules

### Health Server Testing
```python
import asyncio
from shared.health_server import HealthServer

async def test_health_server():
    server = HealthServer(
        instance_id="test",
        port=8080,
        logger=logging.getLogger("test"),
        get_health_data=lambda: {"test": "ok"}
    )

    await server.start_server()
    # Server runs until interrupted
```

### Redis Consumer Testing
```python
import asyncio
from shared.redis_consumer import RedisStreamConsumer

async def test_consumer():
    async def mock_processor(message_id, data):
        print(f"Processing message {message_id}: {data}")
        return "processed"

    consumer = RedisStreamConsumer(
        redis_url="redis://localhost:6379",
        stream_name="test_stream",
        consumer_group="test_group",
        consumer_id="test-consumer",
        logger=logging.getLogger("test"),
        message_processor=mock_processor
    )

    await consumer.connect()
    # Consumer will process messages until stopped
```

## 🚀 Best Practices

### Health Checks
- Keep health checks lightweight and fast
- Include critical dependency status (Redis, model loading)
- Use appropriate HTTP status codes (200 for healthy, 500 for unhealthy)

### Metrics Collection
- Use descriptive metric names
- Include units in metric names where applicable (`_ms`, `_bytes`, `_count`)
- Track both success and failure rates
- Monitor resource usage (memory, CPU)

### Error Handling
- Log errors with appropriate severity levels
- Include contextual information in error messages
- Track error rates by type/category
- Implement circuit breakers for external service failures

### Performance Monitoring
- Track latency percentiles (P50, P95, P99)
- Monitor queue depths and processing backlogs
- Alert on unusual patterns or threshold violations
- Use histograms for detailed performance analysis
