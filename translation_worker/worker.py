"""
translation_worker.py - Translation Worker Service with Redis Streams

This service consumes transcription results from Redis and performs text translation:
- Consumes transcription jobs from Redis Streams with consumer groups (xreadgroup/xack/xdel)
- Uses NLLB-200 model for translation with GPU acceleration
- Publishes translated results back to Redis pub/sub channels
- Async processing with ThreadPoolExecutor to prevent memory leaks
- Memory monitoring with automatic garbage collection every 5 minutes
- Health check HTTP server on port 8082 with CORS support
- Comprehensive metrics collection (jobs processed, failures, processing times)
- Horizontal scaling with multiple worker instances using consumer groups
- Graceful shutdown with proper resource cleanup
"""

import asyncio
import json
import time
import os
import sys
import logging
import gc
import psutil
from typing import Dict, Any, Optional
import redis.asyncio as redis
from redis.exceptions import ConnectionError
from aiohttp import web
import aiohttp_cors
from concurrent.futures import ThreadPoolExecutor
import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# === Configuration ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
WORKER_ID = os.getenv("WORKER_ID", f"translation-{os.getpid()}")
CONSUMER_GROUP = os.getenv("CONSUMER_GROUP", "translation_workers")

# Redis Streams/Channels
TRANSCRIPTIONS_STREAM = os.getenv("TRANSCRIPTIONS_STREAM", "transcriptions")
RESULTS_CHANNEL_PREFIX = "results:"

# NLLB-200 Translation parameters
NLLB_MODEL = os.getenv("NLLB_MODEL", "facebook/nllb-200-distilled-600M")
# Use GPU if available, fallback to CPU
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Health check
HEALTH_PORT = int(os.getenv("HEALTH_PORT", "8082"))

# === Language Mapping Configuration ===
# Maps two-character language codes to NLLB-200 BCP-47 format codes
# Format: {iso639-3}_{script}
LANGUAGE_MAPPING = {
    "en": "eng_Latn",      # English (Latin script)
    "es": "spa_Latn",      # Spanish (Latin script)
    "fr": "fra_Latn",      # French (Latin script)
    "de": "deu_Latn",      # German (Latin script)
    "vi": "vie_Latn",      # Vietnamese (Latin script)
    "zh": "zho_Hans",      # Chinese Simplified (Hans script)
    "ja": "jpn_Jpan",      # Japanese (Japanese script)
    "hi": "hin_Deva",      # Hindi (Devanagari script)
}

def get_mapped_language(lang_code: str) -> str:
    """
    Get the mapped NLLB-200 language code for translation worker.
    Returns the NLLB BCP-47 format code if available, otherwise returns the original code.

    Args:
        lang_code: Two-character language code (e.g., 'en', 'vi')

    Returns:
        NLLB-200 BCP-47 format code (e.g., 'eng_Latn', 'vie_Latn')
    """
    return LANGUAGE_MAPPING.get(lang_code.lower(), lang_code)


class TranslationWorker:
    def __init__(self):
        self.redis = None
        self.model = None
        self.tokenizer = None
        self.worker_id = WORKER_ID
        self.consumer_group = CONSUMER_GROUP
        self.logger = logging.getLogger(f"TRANSLATION-{self.worker_id}")

        # Thread pool for translation tasks (prevents memory leaks from unlimited threads)
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="translation")

        # Metrics
        self.metrics = {
            "jobs_processed": 0,
            "jobs_failed": 0,
            "total_processing_time": 0.0,
            "model_load_time": 0.0,
            "uptime": time.time(),
            "memory_mb": 0.0,
            "gc_collections": 0,
            "device": DEVICE
        }

        # Memory management
        self.last_gc_time = time.time()
        self.gc_interval = 300  # Run GC every 5 minutes

    def _parse_bool(self, value: Any) -> bool:
        """Parse boolean value from various formats (string, bool, etc.)"""
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        if isinstance(value, (int, float)):
            return value != 0
        try:
            s = str(value).strip().lower()
            return s in {"1", "true", "yes", "y", "on"}
        except Exception:
            return False

    async def connect_redis(self):
        """Connect to Redis"""
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=False)
        await self.redis.ping()
        self.logger.info("Connected to Redis")
        # Ensure consumer group exists for the transcriptions stream
        try:
            await self.redis.xgroup_create(
                TRANSCRIPTIONS_STREAM,
                self.consumer_group,
                "$",
                mkstream=True
            )
            self.logger.info(f"Created consumer group {self.consumer_group} on stream '{TRANSCRIPTIONS_STREAM}'")
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise
            self.logger.info(f"Consumer group {self.consumer_group} already exists on '{TRANSCRIPTIONS_STREAM}'")

    def _monitor_memory(self):
        """Monitor memory usage and trigger GC if needed"""
        try:
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            self.metrics["memory_mb"] = memory_mb

            # Trigger garbage collection periodically
            current_time = time.time()
            if current_time - self.last_gc_time > self.gc_interval:
                collected = gc.collect()
                self.metrics["gc_collections"] += 1
                self.last_gc_time = current_time
                
                # Clear CUDA cache if using GPU
                if DEVICE == "cuda" and torch.cuda.is_available():
                    torch.cuda.empty_cache()

        except Exception as e:
            self.logger.warning(f"Memory monitoring error: {e}")

    def load_model(self):
        """Load the NLLB-200 translation model"""
        start_time = time.time()
        try:
            self.logger.info(f"Loading NLLB-200 model '{NLLB_MODEL}' on {DEVICE}...")
            
            # Load model with optimizations
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                NLLB_MODEL,
                torch_dtype=torch.float16 if DEVICE == "cuda" else torch.float32,
                low_cpu_mem_usage=True
            )
            
            # Move model to device
            self.model = self.model.to(DEVICE)
            self.model.eval()  # Set to evaluation mode
            
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(NLLB_MODEL)
            
            # Warm up the model with a test translation
            self.logger.info("Performing model warm-up translation...")
            warmup_text = "Hello, this is a test."
            src_lang = "eng_Latn"
            tgt_lang = "vie_Latn"
            
            inputs = self.tokenizer(
                warmup_text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(DEVICE)
            
            with torch.no_grad():
                _ = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(tgt_lang),
                    max_length=200,
                    num_beams=5
                )
            
            load_time = time.time() - start_time
            self.metrics["model_load_time"] = load_time
            self.logger.info(f"NLLB-200 model loaded in {load_time:.2f}s")
            
            # Log GPU info if available
            if DEVICE == "cuda":
                self.logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
                self.logger.info(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")
                
        except Exception as e:
            self.logger.error(f"Error loading NLLB-200 model: {e}")
            raise

    def _translate_sync(self, text: str, src_lang: str, tgt_lang: str) -> str:
        """
        Synchronous translation function to be called in thread pool.
        Optimized for GPU inference with proper batching and memory management.
        
        Args:
            text: Text to translate
            src_lang: Source language in NLLB-200 format (e.g., 'eng_Latn')
            tgt_lang: Target language in NLLB-200 format (e.g., 'vie_Latn')
            
        Returns:
            Translated text
        """
        try:
            # Tokenize input with proper settings
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(DEVICE)
            
            # Generate translation with optimized parameters
            with torch.no_grad():  # Disable gradient calculation for inference
                translated_tokens = self.model.generate(
                    **inputs,
                    forced_bos_token_id=self.tokenizer.convert_tokens_to_ids(tgt_lang),
                    max_length=200,
                    num_beams=5,  # Beam search for quality
                    early_stopping=True,
                    do_sample=False  # Deterministic output
                )
            
            # Decode translation
            translation = self.tokenizer.batch_decode(
                translated_tokens,
                skip_special_tokens=True
            )[0]
            
            # Clean up tensors to free memory
            del inputs
            del translated_tokens
            
            return translation
            
        except Exception as e:
            self.logger.error(f"Translation error: {e}")
            raise

    async def process_translation_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single translation job"""
        start_time = time.time()

        # Monitor memory usage
        self._monitor_memory()

        try:
            job_id = job_data.get("job_id", "unknown")
            client_id = job_data.get("client_id", "unknown")
            text = job_data.get("text", "")
            source_lang = job_data.get("source_lang", "en")
            target_lang = job_data.get("target_lang", "vi")
            audio_duration = job_data.get("audio_duration", 0.0)
            is_final = self._parse_bool(job_data.get("is_final", False))

            self.logger.info(f"Processing translation job {job_id} for client {client_id}")

            if not text.strip():
                result = {
                    "status": "ok",
                    "job_id": job_id,
                    "client_id": client_id,
                    "segment_id": job_data.get("segment_id", ""),
                    "text": "",
                    "translation": "",
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "processing_time": time.time() - start_time,
                    "worker_id": self.worker_id,
                    "timestamp": time.time(),
                    "audio_duration": audio_duration,
                    "is_final": is_final
                }
            else:
                # Map language codes to NLLB-200 format
                mapped_source_lang = get_mapped_language(source_lang)
                mapped_target_lang = get_mapped_language(target_lang)

                self.logger.debug(
                    f"Translating: {text[:50]}... "
                    f"({source_lang}->{mapped_source_lang}) -> ({target_lang}->{mapped_target_lang})"
                )

                # Perform translation using thread pool to avoid blocking
                translation = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    self._translate_sync,
                    text.strip(),
                    mapped_source_lang,
                    mapped_target_lang
                )
                
                processing_time = time.time() - start_time
                result = {
                    "status": "ok",
                    "job_id": job_id,
                    "client_id": client_id,
                    "segment_id": job_data.get("segment_id", ""),
                    "text": text,
                    "translation": translation,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "processing_time": processing_time,
                    "worker_id": self.worker_id,
                    "timestamp": time.time(),
                    "audio_duration": audio_duration,
                    "is_final": is_final
                }
                self.logger.info(f"Translation completed in {processing_time:.2f}s")
                
            # Update metrics
            self.metrics["jobs_processed"] += 1
            self.metrics["total_processing_time"] += result["processing_time"]
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Error processing translation job {job_data.get('job_id', 'unknown')}: {e}")
            self.metrics["jobs_failed"] += 1
            return {
                "status": "error",
                "job_id": job_data.get("job_id", "unknown"),
                "client_id": job_data.get("client_id", "unknown"),
                "segment_id": job_data.get("segment_id", ""),
                "text": job_data.get("text", ""),
                "translation": "",
                "error": str(e),
                "processing_time": processing_time,
                "worker_id": self.worker_id,
                "timestamp": time.time()
            }

    async def publish_result(self, result: Dict[str, Any]):
        """Publish result to Redis pub/sub channel"""
        channel = f"{RESULTS_CHANNEL_PREFIX}{result['client_id']}"
        # Publish as UTF-8 encoded bytes for consistent handling
        await self.redis.publish(channel, json.dumps(result).encode('utf-8'))
        self.logger.info(
            f"Published translation result for client {result['client_id']} "
            f"(segment_id: {result.get('segment_id', 'N/A')})"
        )

    async def consume_transcription_results(self):
        """Consume transcriptions from Redis Stream using consumer groups for horizontal scaling."""
        while True:
            try:
                messages = await self.redis.xreadgroup(
                    self.consumer_group,
                    self.worker_id,
                    {TRANSCRIPTIONS_STREAM: ">"},
                    count=1,
                    block=1000
                )
                if messages:
                    stream_name, message_list = messages[0]
                    for message_id, message_data in message_list:
                        try:
                            # Decode bytes to strings for message_data (Redis with decode_responses=False)
                            decoded_message_data = {}
                            for key, value in message_data.items():
                                if isinstance(key, bytes):
                                    key = key.decode('utf-8')
                                if isinstance(value, bytes):
                                    value = value.decode('utf-8')
                                decoded_message_data[key] = value

                            text = (decoded_message_data.get("text") or "").strip()
                            if text:
                                result = await self.process_translation_job(decoded_message_data)
                                await self.publish_result(result)
                            await self.redis.xack(TRANSCRIPTIONS_STREAM, self.consumer_group, message_id)
                            await self.redis.xdel(TRANSCRIPTIONS_STREAM, message_id)
                        except Exception as e:
                            self.logger.error(f"Error processing transcription {message_id}: {e}")
                            self.metrics["jobs_failed"] += 1
            except ConnectionError as e:
                self.logger.error(f"Redis connection error: {e}")
                await asyncio.sleep(5)
            except Exception as e:
                self.logger.error(f"Error consuming transcriptions stream: {e}")
                await asyncio.sleep(1)

    async def health_check_handler(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "worker_id": self.worker_id,
            "model_loaded": self.model is not None,
            "device": DEVICE,
            "timestamp": time.time(),
            "metrics": self.metrics
        })

    async def metrics_handler(self, request):
        """Metrics endpoint"""
        avg_processing_time = (
            self.metrics["total_processing_time"] / self.metrics["jobs_processed"]
            if self.metrics["jobs_processed"] > 0
            else 0
        )
        
        return web.json_response({
            "worker_id": self.worker_id,
            "device": DEVICE,
            "model": NLLB_MODEL,
            "metrics": {
                **self.metrics,
                "avg_processing_time": avg_processing_time,
                "uptime_seconds": time.time() - self.metrics["uptime"]
            },
            "timestamp": time.time()
        })

    async def start_health_server(self):
        """Start health check HTTP server"""
        app = web.Application()
        app.router.add_get('/health', self.health_check_handler)
        app.router.add_get('/metrics', self.metrics_handler)
        
        # Disable aiohttp access logging
        logging.getLogger('aiohttp.access').setLevel(logging.CRITICAL)

        # Add CORS support
        cors = aiohttp_cors.setup(app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
            )
        })

        for route in list(app.router.routes()):
            cors.add(route)

        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', HEALTH_PORT)
        await site.start()
        self.logger.info(f"Health server started on port {HEALTH_PORT}")


async def main():
    """Main translation worker service"""
    worker = TranslationWorker()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
    )

    try:
        # Connect to Redis
        await worker.connect_redis()
        
        # Load model
        worker.load_model()
        
        # Start health server
        await worker.start_health_server()

        # Log all configuration variables
        worker.logger.info("Translation Worker initialization complete")
        worker.logger.info(f"Redis: {REDIS_URL}")
        worker.logger.info(f"Worker ID: {WORKER_ID}")
        worker.logger.info(f"Consumer Group: {CONSUMER_GROUP}")
        worker.logger.info(f"Transcriptions Stream: {TRANSCRIPTIONS_STREAM}")
        worker.logger.info(f"Results Channel Prefix: {RESULTS_CHANNEL_PREFIX}")
        worker.logger.info(f"Translation Model: NLLB-200 ({NLLB_MODEL})")
        worker.logger.info(f"Device: {DEVICE}")
        worker.logger.info(f"Health server on port {HEALTH_PORT}")
        worker.logger.info(f"Supported languages: {list(LANGUAGE_MAPPING.keys())}")

        worker.logger.info(f"Starting Translation Worker {worker.worker_id}")
        
        # Start consuming transcription results
        await worker.consume_transcription_results()
        
    except Exception as e:
        worker.logger.error(f"Worker startup error: {e}")
        raise
    finally:
        # Proper cleanup to prevent memory leaks
        worker.logger.info("Shutting down translation worker...")
        
        if worker.redis:
            await worker.redis.close()
            
        if worker.executor:
            worker.executor.shutdown(wait=True)
            
        if worker.model:
            del worker.model
            
        if worker.tokenizer:
            del worker.tokenizer
            
        # Clear CUDA cache if using GPU
        if DEVICE == "cuda" and torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        worker.logger.info("Translation worker shutdown complete")

if __name__ == "__main__":
    asyncio.run(main())