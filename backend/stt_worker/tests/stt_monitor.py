#!/usr/bin/env python3
"""
STT Worker Monitor - Real-time monitoring of STT and Translation worker performance

This script monitors both STT and Translation worker performance by tracking:
- Average, minimum, and maximum execution times for all workers
- Separate statistics for STT vs Translation workers
- Individual worker performance with throughput metrics
- Real-time processing time for each chunk with worker type identification
- Comprehensive processing statistics and throughput analysis

Usage: python stt_monitor.py
"""

import asyncio
import json
import os
import time
import logging
from typing import Dict, List
from collections import defaultdict
import redis.asyncio as redis
from redis.exceptions import ConnectionError
import statistics

# === Configuration ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
RESULTS_CHANNEL_PREFIX = os.getenv("RESULTS_CHANNEL_PREFIX", "results:")
MONITOR_UPDATE_INTERVAL = 5.0  # Update stats every 5 seconds

class STTMonitor:
    def __init__(self):
        self.redis = None
        self.logger = logging.getLogger("STT-Monitor")

        # Processing time tracking
        self.processing_times: List[float] = []
        self.worker_times: Dict[str, List[float]] = defaultdict(list)
        self.client_times: Dict[str, List[float]] = defaultdict(list)

        # Real-time stats
        self.total_jobs = 0
        self.successful_jobs = 0
        self.failed_jobs = 0
        self.start_time = time.time()

        # Current session stats
        self.session_start_time = time.time()
        self.session_jobs = 0

    async def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(REDIS_URL)
            await self.redis.ping()
            self.logger.info("Connected to Redis")
        except ConnectionError as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def monitor_results(self):
        """Monitor STT results in real-time"""
        pubsub = self.redis.pubsub()

        # Subscribe to all result channels with pattern
        await pubsub.psubscribe(f"{RESULTS_CHANNEL_PREFIX}*")
        self.logger.info(f"Subscribed to result channels: {RESULTS_CHANNEL_PREFIX}*")

        print("\n" + "="*80)
        print("STT WORKER MONITOR - Real-time Performance Tracking")
        print("="*80)
        print("Monitoring STT worker performance...")
        print("Press Ctrl+C to stop monitoring")
        print("-" * 80)

        try:
            async for message in pubsub.listen():
                if message['type'] == 'pmessage':
                    await self.process_result(message['data'])
                    await self.display_stats()

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")
        finally:
            await pubsub.punsubscribe(f"{RESULTS_CHANNEL_PREFIX}*")
            await pubsub.close()

    async def process_result(self, data: bytes):
        """Process a single result message"""
        try:
            result = json.loads(data.decode('utf-8'))

            # Extract relevant data
            processing_time = result.get('processing_time', 0.0)
            audio_duration_str = result.get('audio_duration')
            try:
                audio_duration = float(audio_duration_str) if audio_duration_str is not None else 0.0
            except (ValueError, TypeError):
                audio_duration = 0.0
            status = result.get('status', 'unknown')
            worker_id = result.get('worker_id', 'unknown')
            client_id = result.get('client_id', 'unknown')
            job_id = result.get('job_id', 'unknown')
            text_length = len(result.get('text', ''))

            # Debug logging
            self.logger.info(f"Monitor received result: audio_duration={audio_duration}, processing_time={processing_time}, status={status}, text_len={text_length}")

            # Warn if audio_duration is 0 or missing but text exists
            if text_length > 0 and audio_duration < 0.001:
                self.logger.warning(f"Transcription produced {text_length} chars but audio_duration is {audio_duration}!")

            # Update counters
            self.total_jobs += 1
            self.session_jobs += 1

            if status == 'ok' and processing_time > 0:
                self.successful_jobs += 1
                self.processing_times.append(processing_time)
                self.worker_times[worker_id].append(processing_time)
                self.client_times[client_id].append(processing_time)

                # Real-time display for this chunk
                worker_type = "STT" if worker_id.startswith('stt-') else "TRANS" if worker_id.startswith('translation-') else "UNKWN"
                duration_display = f"{audio_duration:.4f}s" if audio_duration < 0.01 else f"{audio_duration:.2f}s"
                print(f"✓ [{worker_type}] Input: {duration_display} audio, Output: {processing_time:.2f}s processing ({text_length} chars) - {worker_id}")

            elif status == 'error':
                self.failed_jobs += 1
                worker_type = "STT" if worker_id.startswith('stt-') else "TRANS" if worker_id.startswith('translation-') else "UNKWN"
                print(f"✗ [{worker_type}] Input: {audio_duration:.2f}s audio, Failed after {processing_time:.2f}s processing - {worker_id}")

        except Exception as e:
            self.logger.error(f"Error processing result: {e}")

    async def display_stats(self):
        """Display current statistics"""
        current_time = time.time()

        # Only update display every MONITOR_UPDATE_INTERVAL seconds
        if current_time - getattr(self, '_last_display_time', 0) < MONITOR_UPDATE_INTERVAL:
            return

        self._last_display_time = current_time

        if not self.processing_times:
            return

        # Calculate statistics
        avg_time = statistics.mean(self.processing_times) if self.processing_times else 0
        min_time = min(self.processing_times) if self.processing_times else 0
        max_time = max(self.processing_times) if self.processing_times else 0

        # Calculate throughput
        uptime = current_time - self.start_time
        jobs_per_second = self.successful_jobs / uptime if uptime > 0 else 0

        # Session stats (last 5 seconds)
        session_time = current_time - self.session_start_time
        if session_time >= MONITOR_UPDATE_INTERVAL:
            session_throughput = self.session_jobs / session_time
            self.session_start_time = current_time
            self.session_jobs = 0
        else:
            session_throughput = 0

        # Clear screen and display stats
        print("\033[2J\033[H", end="")  # Clear screen and move cursor to top
        print("="*80)
        print("STT WORKER MONITOR - Performance Statistics")
        print("="*80)
        success_rate = (self.successful_jobs / self.total_jobs * 100) if self.total_jobs > 0 else 0

        print(f"Total Jobs Processed: {self.total_jobs}")
        print(f"Successful Jobs: {self.successful_jobs}")
        print(f"Failed Jobs: {self.failed_jobs}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Uptime: {uptime:.1f}s")
        print(f"Jobs/sec: {jobs_per_second:.1f}")
        print()

        # Processing Time Statistics
        print("PROCESSING TIME STATISTICS:")
        print(f"Average: {avg_time:.3f}s")
        print(f"Minimum: {min_time:.3f}s")
        print(f"Maximum: {max_time:.3f}s")

        # Calculate percentiles
        if len(self.processing_times) >= 10:
            p50 = statistics.median(self.processing_times)
            p95 = statistics.quantiles(self.processing_times, n=20)[18]  # 95th percentile
            p99 = statistics.quantiles(self.processing_times, n=100)[98]  # 99th percentile
            print(f"P50 (Median): {p50:.3f}s")
            print(f"P95: {p95:.3f}s")
            print(f"P99: {p99:.3f}s")

        print()

        # Throughput
        print("THROUGHPUT:")
        print(f"Overall: {jobs_per_second:.2f} jobs/sec")
        print(f"Current: {session_throughput:.2f} jobs/sec")
        print()

        # Separate STT and Translation workers
        stt_workers = {}
        translation_workers = {}

        for worker_id, times in self.worker_times.items():
            if worker_id.startswith('stt-'):
                stt_workers[worker_id] = times
            elif worker_id.startswith('translation-'):
                translation_workers[worker_id] = times

        # STT Worker Statistics
        if stt_workers:
            stt_times = [time for times in stt_workers.values() for time in times]
            if stt_times:
                stt_avg = statistics.mean(stt_times)
                stt_min = min(stt_times)
                stt_max = max(stt_times)
                stt_count = len(stt_times)
                stt_throughput = stt_count / uptime if uptime > 0 else 0

                print("STT WORKERS:")
                print(f"  Total Jobs: {stt_count}")
                print(f"  Average: {stt_avg:.3f}s")
                print(f"  Minimum: {stt_min:.3f}s")
                print(f"  Maximum: {stt_max:.3f}s")
                print(f"  Throughput: {stt_throughput:.2f} jobs/sec")
                print()

        # Translation Worker Statistics
        if translation_workers:
            trans_times = [time for times in translation_workers.values() for time in times]
            if trans_times:
                trans_avg = statistics.mean(trans_times)
                trans_min = min(trans_times)
                trans_max = max(trans_times)
                trans_count = len(trans_times)
                trans_throughput = trans_count / uptime if uptime > 0 else 0

                print("TRANSLATION WORKERS:")
                print(f"  Total Jobs: {trans_count}")
                print(f"  Average: {trans_avg:.3f}s")
                print(f"  Minimum: {trans_min:.3f}s")
                print(f"  Maximum: {trans_max:.3f}s")
                print(f"  Throughput: {trans_throughput:.2f} jobs/sec")
                print()

        # Individual Worker Performance (top 5 overall)
        if self.worker_times:
            print("INDIVIDUAL WORKER PERFORMANCE (Top 5 by job count):")
            worker_stats = []
            for worker_id, times in self.worker_times.items():
                if times:
                    worker_type = "STT" if worker_id.startswith('stt-') else "TRANS" if worker_id.startswith('translation-') else "OTHER"
                    worker_stats.append({
                        'worker_id': worker_id,
                        'worker_type': worker_type,
                        'count': len(times),
                        'avg_time': statistics.mean(times),
                        'min_time': min(times),
                        'max_time': max(times)
                    })

            worker_stats.sort(key=lambda x: x['count'], reverse=True)
            for stat in worker_stats[:5]:
                print(f"{stat['worker_type']:<6} {stat['worker_id']:<25} {stat['count']:>3} jobs   avg:{stat['avg_time']:.3f}s   min:{stat['min_time']:.3f}s   max:{stat['max_time']:.3f}s")

        print("-" * 80)

    async def run(self):
        """Main monitoring loop"""
        try:
            await self.connect_redis()
            await self.monitor_results()
        except Exception as e:
            self.logger.error(f"Monitor failed: {e}")
        finally:
            if self.redis:
                await self.redis.close()


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    monitor = STTMonitor()
    asyncio.run(monitor.run())


if __name__ == "__main__":
    main()
