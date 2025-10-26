"""
metrics.py - Shared metrics collection for worker services

Provides a standardized metrics collection system used by both STT and translation workers.
Tracks processing times, success rates, memory usage, and other operational metrics.
"""

import time
import psutil
import gc
from typing import Dict, Any
import logging


class WorkerMetrics:
    """Collects and manages metrics for worker services"""

    def __init__(self, worker_type: str, instance_id: str):
        self.worker_type = worker_type
        self.instance_id = instance_id
        self.logger = logging.getLogger(f"{worker_type.upper()}-{instance_id}")

        # Initialize metrics
        self.metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "total_processing_time": 0.0,
            "memory_mb": 0.0,
            "gc_collections": 0,
            "start_time": time.time()
        }

        # Track last memory check time
        self.last_memory_check = time.time()

    def update_memory_usage(self):
        """Update current memory usage metric"""
        current_time = time.time()
        # Only check memory every 30 seconds to avoid overhead
        if current_time - self.last_memory_check >= 30:
            try:
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                self.metrics["memory_mb"] = round(memory_mb, 2)
                self.last_memory_check = current_time
            except Exception as e:
                self.logger.warning(f"Failed to get memory usage: {e}")

    def record_gc_collection(self):
        """Record that a garbage collection occurred"""
        self.metrics["gc_collections"] += 1

    def record_job_success(self, processing_time: float):
        """Record a successful job completion"""
        self.metrics["jobs_processed"] += 1
        self.metrics["total_processing_time"] += processing_time

    def record_job_failure(self):
        """Record a failed job"""
        self.metrics["jobs_failed"] += 1

    def get_metrics_dict(self) -> Dict[str, Any]:
        """Get all metrics as a dictionary"""
        # Update memory before returning
        self.update_memory_usage()

        # Calculate derived metrics
        metrics_copy = self.metrics.copy()
        total_jobs = metrics_copy["jobs_processed"] + metrics_copy["jobs_failed"]

        if total_jobs > 0:
            metrics_copy["success_rate"] = round((metrics_copy["jobs_processed"] / total_jobs) * 100, 2)
        else:
            metrics_copy["success_rate"] = 0.0

        if metrics_copy["jobs_processed"] > 0:
            metrics_copy["avg_processing_time"] = round(metrics_copy["total_processing_time"] / metrics_copy["jobs_processed"], 3)
        else:
            metrics_copy["avg_processing_time"] = 0.0

        # Add uptime
        metrics_copy["uptime_seconds"] = int(time.time() - metrics_copy["start_time"])

        return metrics_copy

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get a summary of key metrics for health checks"""
        metrics = self.get_metrics_dict()
        return {
            "worker_type": self.worker_type,
            "instance_id": self.instance_id,
            "jobs_processed": metrics["jobs_processed"],
            "jobs_failed": metrics["jobs_failed"],
            "success_rate": metrics["success_rate"],
            "avg_processing_time": metrics["avg_processing_time"],
            "memory_mb": metrics["memory_mb"],
            "uptime_seconds": metrics["uptime_seconds"]
        }
