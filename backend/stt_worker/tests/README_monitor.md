# STT Worker Monitor

A real-time monitoring script for tracking both STT and Translation worker performance metrics.

## Features

- **Dual Worker Type Monitoring**: Separate statistics for STT and Translation workers
- **Real-time Processing Time Tracking**: Monitors each chunk's processing time with worker type identification
- **Statistical Analysis**: Tracks average, minimum, and maximum execution times for each worker type
- **Throughput Metrics**: Shows jobs processed per second for both worker types
- **Individual Worker Performance**: Detailed statistics for each worker instance
- **Percentiles**: Shows 50th, 95th, and 99th percentile processing times
- **Session Statistics**: Rolling statistics for recent performance

## Usage

```bash
cd stt_worker
python stt_monitor.py
```

## Requirements

- Python 3.7+
- Redis server running
- STT workers actively processing jobs

## Configuration

The monitor can be configured using environment variables:

- `REDIS_URL`: Redis connection URL (default: `redis://localhost:6379`)
- `RESULTS_CHANNEL_PREFIX`: Prefix for results channels (default: `results:`)

## Output

The monitor displays real-time statistics including:

- Total jobs processed (successful/failed)
- Processing time statistics (avg/min/max)
- Percentile breakdowns (P50, P95, P99)
- Throughput rates
- Individual worker performance
- Live processing times for each chunk

## Example Output

```
STT WORKER MONITOR - Performance Statistics
================================================================================
Total Jobs Processed: 1299
Successful Jobs: 1299
Failed Jobs: 0
Success Rate: 100.0%
Uptime: 985.8s
Jobs/sec: 1.3

PROCESSING TIME STATISTICS:
Average: 0.304s
Minimum: 0.068s
Maximum: 2.450s
P50 (Median): 0.272s
P95: 0.592s
P99: 0.778s

THROUGHPUT:
Overall: 1.32 jobs/sec
Current: 3.65 jobs/sec

STT WORKERS:
  Total Jobs: 653
  Average: 0.367s
  Minimum: 0.185s
  Maximum: 2.450s
  Throughput: 0.66 jobs/sec

TRANSLATION WORKERS:
  Total Jobs: 646
  Average: 0.240s
  Minimum: 0.068s
  Maximum: 0.836s
  Throughput: 0.66 jobs/sec

INDIVIDUAL WORKER PERFORMANCE (Top 5 by job count):
STT    stt-95029                 653 jobs   avg:0.367s   min:0.185s   max:2.450s
TRANS  translation-56082         646 jobs   avg:0.240s   min:0.068s   max:0.836s
...
```

## Live Chunk Monitoring

As each chunk is processed, the monitor shows worker type:
```
✓ [STT] Chunk completed in 0.53s (119 chars) - stt-95029
✓ [TRANS] Chunk completed in 0.19s (119 chars) - translation-56082
✗ [STT] Chunk failed in 0.023s - stt-67890
```

Press `Ctrl+C` to stop monitoring.
