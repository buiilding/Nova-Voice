"""
worker.py - Main Translation Worker Service (refactored)

Orchestrates the translation worker components: model management, language mapping,
Redis consumption, translation execution, result publishing, health monitoring, and metrics collection.
"""

import asyncio
import time
import logging
from typing import Dict, Any

import redis.asyncio as redis
from redis.exceptions import ConnectionError
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from .config import (
    REDIS_URL, TRANSCRIPTIONS_STREAM, CONSUMER_GROUP, WORKER_ID,
    HEALTH_PORT, validate_configuration, print_configuration
)
from .model_manager import TranslationModelManager
from .translator import Translator
from .result_publisher import ResultPublisher
import sys
import os
# Add backend directory to path so shared modules can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from shared.redis_consumer import RedisStreamConsumer
from shared.health_server import HealthServer
from shared.metrics import WorkerMetrics


class TranslationWorker:
    """Main Translation Worker class that orchestrates all components"""

    def __init__(self):
        self.worker_id = WORKER_ID
        self.logger = logging.getLogger(f"Translation-{self.worker_id}")

        # Initialize components
        self.metrics = WorkerMetrics("translation", self.worker_id)
        self.model_manager = TranslationModelManager(self.logger)
        self.redis: redis.Redis = None
        self.translator: Translator = None
        self.result_publisher: ResultPublisher = None
        self.redis_consumer: RedisStreamConsumer = None
        self.health_server: HealthServer = None

        # Thread pool for translation to prevent memory leaks
        self.executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="translation")

        # Configuration validation
        issues = validate_configuration()
        if issues:
            for issue in issues:
                self.logger.error(f"Configuration issue: {issue}")
            raise ValueError("Configuration validation failed")

    async def connect_redis(self):
        """Connect to Redis and set up consumer group"""
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=False)

        # Test connection
        await self.redis.ping()

        # Create consumer group if it doesn't exist
        try:
            await self.redis.xgroup_create(TRANSCRIPTIONS_STREAM, CONSUMER_GROUP, "0", mkstream=True)
            self.logger.info(f"Created consumer group {CONSUMER_GROUP}")
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            self.logger.info(f"Consumer group {CONSUMER_GROUP} already exists")

        self.logger.info("Connected to Redis")

    def initialize_components(self):
        """Initialize all worker components"""
        # Load the model
        model, tokenizer = self.model_manager.load_model()

        # Initialize translator
        self.translator = Translator(model, tokenizer, self.logger)
        self.result_publisher = ResultPublisher(self.redis, self.logger)

        # Initialize Redis consumer
        self.redis_consumer = RedisStreamConsumer(
            redis_url=REDIS_URL,
            stream_name=TRANSCRIPTIONS_STREAM,
            consumer_group=CONSUMER_GROUP,
            consumer_id=self.worker_id,
            logger=self.logger,
            message_processor=self._process_translation_job
        )

        # Initialize health server
        self.health_server = HealthServer(
            instance_id=self.worker_id,
            port=HEALTH_PORT,
            logger=self.logger,
            get_health_data=self._get_health_data,
            get_metrics_data=self._get_metrics_data
        )

    async def _process_translation_job(self, message_id: str, job_data: Dict[str, Any]):
        """Process a single translation job from the Redis stream"""
        start_time = time.time()

        try:
            # Extract job parameters
            job_id = job_data.get("job_id", "unknown")
            client_id = job_data.get("client_id", "unknown")
            text = job_data.get("text", "").strip()

            self.logger.info(f"Processing translation job {job_id} for client {client_id}")

            if not text:
                self.logger.warning(f"Empty text in job {job_id}, skipping")
                self.metrics.record_job_failure()
                return

            # Extract parameters
            source_lang = job_data.get("source_lang", "en")
            target_lang = job_data.get("target_lang", "vi")
            is_final = self._parse_bool(job_data.get("is_final", False))

            # Perform translation in thread pool to prevent memory leaks
            translation = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self.translator.translate_text,
                text,
                source_lang,
                target_lang
            )

            processing_time = time.time() - start_time

            # Build result
            result = {
                "status": "ok",
                "job_id": job_id,
                "client_id": client_id,
                "segment_id": job_data.get("segment_id", ""),
                "source_lang": source_lang,
                "target_lang": target_lang,
                "text": text,
                "translation": translation,
                "is_final": is_final,
                "worker_id": self.worker_id,
                "timestamp": time.time(),
                "processing_time": processing_time
            }

            # Update metrics
            self.metrics.record_job_success(processing_time)

            # Publish result
            await self.result_publisher.publish_result(result)

            self.logger.info(f"Translation completed in {processing_time:.2f}s")

        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error processing translation job: {e}")
            self.metrics.record_job_failure()

            # Send error result
            error_result = {
                "status": "error",
                "job_id": job_data.get("job_id", "unknown"),
                "client_id": job_data.get("client_id", "unknown"),
                "segment_id": job_data.get("segment_id", ""),
                "error": str(e),
                "worker_id": self.worker_id,
                "timestamp": time.time(),
                "processing_time": processing_time
            }
            await self.result_publisher.publish_result(error_result)

    def _get_health_data(self) -> Dict[str, Any]:
        """Get health check data"""
        return {
            "model_loaded": self.model_manager.is_model_loaded(),
            "redis_connected": self.redis is not None,
            **self.model_manager.get_model_info()
        }

    def _get_metrics_data(self) -> Dict[str, Any]:
        """Get detailed metrics data"""
        return self.metrics.get_metrics_dict()

    @staticmethod
    def _parse_bool(value: Any) -> bool:
        """Parse boolean from various string formats"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    async def start(self):
        """Start the translation worker"""
        try:
            self.logger.info("Starting Translation Worker...")
            print_configuration()

            # Connect to Redis
            await self.connect_redis()

            # Initialize components
            self.initialize_components()

            # Connect Redis consumer
            await self.redis_consumer.connect()

            # Start health server
            await self.health_server.start_server()

            # Start consuming jobs
            self.logger.info("Translation Worker started successfully")
            await self.redis_consumer.consume_jobs()

        except Exception as e:
            self.logger.error(f"Error starting Translation Worker: {e}")
            raise
        finally:
            # Cleanup
            if self.executor:
                self.executor.shutdown(wait=True)

    async def cleanup(self):
        """Cleanup resources"""
        if self.executor:
            self.executor.shutdown(wait=True)


async def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [Translation] %(levelname)s: %(message)s'
    )

    worker = TranslationWorker()
    try:
        await worker.start()
    finally:
        await worker.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
