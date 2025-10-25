#!/usr/bin/env python3
"""
demo_client.py - Demo client for testing the speech microservices

This script simulates multiple clients streaming audio concurrently to validate:
- Horizontal scaling of workers
- Job distribution across STT workers
- Result delivery to correct clients
- Translation workflow
- End-to-end latency and throughput
"""

import asyncio
import websockets
import json
import struct
import numpy as np
import time
import logging
import argparse
from typing import List, Dict, Any
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

class DemoClient:
    def __init__(self, client_id: str, gateway_url: str = "ws://localhost:5026"):
        self.client_id = client_id
        self.gateway_url = gateway_url
        self.websocket = None
        self.results = []
        self.connected = False
        self.start_time = None
        self.end_time = None

    async def connect(self):
        """Connect to gateway WebSocket"""
        try:
            self.websocket = await websockets.connect(self.gateway_url)
            self.connected = True
            logger.info(f"Client {self.client_id} connected to gateway")

            # Send initial status request
            await self.websocket.send(json.dumps({"type": "get_status"}))

        except Exception as e:
            logger.error(f"Client {self.client_id} failed to connect: {e}")
            self.connected = False

    async def disconnect(self):
        """Disconnect from gateway"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info(f"Client {self.client_id} disconnected")

    async def send_audio_chunk(self, audio_data: bytes, sample_rate: int = 16000):
        """Send audio chunk to gateway"""
        if not self.connected or not self.websocket:
            logger.error(f"Client {self.client_id} not connected")
            return

        try:
            # Create metadata
            metadata = json.dumps({
                'sampleRate': sample_rate,
                'channels': 1,
                'bitsPerSample': 16
            }).encode('utf-8')

            # Create message: [4 bytes metadata length][metadata JSON][audio data]
            metadata_len = struct.pack("<I", len(metadata))
            message = metadata_len + metadata + audio_data

            await self.websocket.send(message)

        except Exception as e:
            logger.error(f"Client {self.client_id} failed to send audio: {e}")

    async def receive_results(self):
        """Receive and process results from gateway"""
        if not self.websocket:
            return

        try:
            async for message in self.websocket:
                if isinstance(message, str):
                    data = json.loads(message)

                    if data.get("type") == "realtime":
                        result = {
                            "client_id": self.client_id,
                            "text": data.get("text", ""),
                            "translation": data.get("translation", ""),
                            "timestamp": time.time()
                        }
                        self.results.append(result)
                        logger.info(f"Client {self.client_id} received: '{result['text'][:50]}...'")

                    elif data.get("type") == "utterance_end":
                        logger.info(f"Client {self.client_id} utterance ended")
                        break

                    elif data.get("type") == "status":
                        logger.info(f"Client {self.client_id} status: {data}")

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client {self.client_id} connection closed")
        except Exception as e:
            logger.error(f"Client {self.client_id} error receiving results: {e}")

    def generate_test_audio(self, text: str, duration_seconds: float = 2.0, sample_rate: int = 16000) -> bytes:
        """Generate synthetic audio for testing (sine wave)"""
        # This is a placeholder - in a real scenario, you'd use TTS or prerecorded audio
        num_samples = int(duration_seconds * sample_rate)
        frequency = 440  # A4 note

        # Generate sine wave
        t = np.linspace(0, duration_seconds, num_samples)
        audio = np.sin(2 * np.pi * frequency * t)

        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        return audio_int16.tobytes()

def create_test_audio_files():
    """Create some test audio files for demo"""
    test_phrases = [
        "Hello world",
        "How are you today",
        "Thank you very much",
        "Good morning everyone",
        "I love programming",
        "The weather is nice",
        "Can you help me please",
        "What time is it now"
    ]

    logger.info("Generating test audio files...")
    for i, phrase in enumerate(test_phrases):
        # Generate synthetic audio (placeholder)
        audio_data = np.random.randn(16000).astype(np.float32) * 0.1
        audio_int16 = (audio_data * 32767).astype(np.int16)

        filename = f"test_audio_{i+1}.wav"
        # Note: This is just raw PCM data, not a proper WAV file
        # In a real scenario, you'd save proper WAV files
        with open(filename, 'wb') as f:
            f.write(audio_int16.tobytes())

        logger.info(f"Created {filename} for phrase: '{phrase}'")

async def run_single_client_test(client_id: str, audio_duration: float = 2.0):
    """Run a single client test"""
    client = DemoClient(client_id)

    try:
        # Connect to gateway
        await client.connect()

        if not client.connected:
            return None

        # Start receiving results in background
        receive_task = asyncio.create_task(client.receive_results())

        # Wait a bit for connection to stabilize
        await asyncio.sleep(0.5)

        # Generate and send test audio
        logger.info(f"Client {client_id} sending {audio_duration}s of audio...")
        audio_data = client.generate_test_audio("test phrase", audio_duration)

        client.start_time = time.time()
        await client.send_audio_chunk(audio_data)

        # Wait for utterance to end or timeout
        await asyncio.wait_for(receive_task, timeout=10.0)

        client.end_time = time.time()

        # Calculate latency
        if client.results:
            latency = client.results[0]["timestamp"] - client.start_time
        else:
            latency = None

        return {
            "client_id": client_id,
            "results_count": len(client.results),
            "latency": latency,
            "duration": client.end_time - client.start_time if client.end_time else None
        }

    except Exception as e:
        logger.error(f"Client {client_id} test failed: {e}")
        return None
    finally:
        await client.disconnect()

async def run_concurrent_clients_test(num_clients: int, audio_duration: float = 2.0):
    """Run multiple clients concurrently"""
    logger.info(f"Starting concurrent test with {num_clients} clients...")

    start_time = time.time()

    # Create and run all clients concurrently
    tasks = []
    for i in range(num_clients):
        client_id = f"client_{i+1:03d}"
        task = asyncio.create_task(run_single_client_test(client_id, audio_duration))
        tasks.append(task)

    # Wait for all clients to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    total_duration = end_time - start_time

    # Process results
    successful_results = [r for r in results if r is not None and not isinstance(r, Exception)]
    failed_count = len(results) - len(successful_results)

    if successful_results:
        latencies = [r["latency"] for r in successful_results if r["latency"] is not None]
        avg_latency = statistics.mean(latencies) if latencies else None
        min_latency = min(latencies) if latencies else None
        max_latency = max(latencies) if latencies else None

        total_results = sum(r["results_count"] for r in successful_results)
        avg_results_per_client = total_results / len(successful_results)

        logger.info("=== Test Results ===")
        logger.info(f"Total clients: {num_clients}")
        logger.info(f"Successful clients: {len(successful_results)}")
        logger.info(f"Failed clients: {failed_count}")
        logger.info(f"Average latency: {avg_latency:.2f}s")
        logger.info(f"Min latency: {min_latency:.2f}s")
        logger.info(f"Max latency: {max_latency:.2f}s")
        logger.info(f"Total duration: {total_duration:.2f}s")
        logger.info(f"Average results per client: {avg_results_per_client:.1f}")

        # Throughput calculation
        throughput = total_results / total_duration if total_duration > 0 else 0
        logger.info(f"Throughput: {throughput:.2f} results/second")

        return {
            "total_clients": num_clients,
            "successful_clients": len(successful_results),
            "failed_clients": failed_count,
            "total_duration": total_duration,
            "avg_latency": avg_latency,
            "min_latency": min_latency,
            "max_latency": max_latency,
            "total_results": total_results,
            "avg_results_per_client": avg_results_per_client,
            "throughput": throughput
        }
    else:
        logger.error("No successful client results!")
        return None

async def run_load_test(clients_per_batch: int, num_batches: int, delay_between_batches: float = 1.0):
    """Run a load test with multiple batches of clients"""
    logger.info(f"Starting load test: {num_batches} batches of {clients_per_batch} clients each")

    all_results = []

    for batch in range(num_batches):
        logger.info(f"\n--- Batch {batch + 1}/{num_batches} ---")
        result = await run_concurrent_clients_test(clients_per_batch)
        if result:
            all_results.append(result)

        if batch < num_batches - 1:
            logger.info(f"Waiting {delay_between_batches:.1f}s before next batch...")
            await asyncio.sleep(delay_between_batches)

    # Aggregate results
    if all_results:
        total_clients = sum(r["total_clients"] for r in all_results)
        successful_clients = sum(r["successful_clients"] for r in all_results)
        total_results = sum(r["total_results"] for r in all_results)
        total_duration = sum(r["total_duration"] for r in all_results)

        logger.info("=== Load Test Summary ===")
        logger.info(f"Total batches: {num_batches}")
        logger.info(f"Total clients: {total_clients}")
        logger.info(f"Successful clients: {successful_clients}")
        logger.info(f"Success rate: {successful_clients / total_clients:.1%}")
        logger.info(f"Total duration: {total_duration:.2f}s")

        return {
            "batches": num_batches,
            "clients_per_batch": clients_per_batch,
            "total_clients": total_clients,
            "successful_clients": successful_clients,
            "success_rate": successful_clients / total_clients,
            "total_results": total_results,
            "total_duration": total_duration
        }

    return None

def main():
    parser = argparse.ArgumentParser(description="Demo client for speech microservices")
    parser.add_argument("--gateway-url", default="ws://localhost:5026",
                       help="Gateway WebSocket URL")
    parser.add_argument("--clients", type=int, default=5,
                       help="Number of concurrent clients for test")
    parser.add_argument("--duration", type=float, default=2.0,
                       help="Audio duration per client (seconds)")
    parser.add_argument("--load-test", action="store_true",
                       help="Run load test with multiple batches")
    parser.add_argument("--batches", type=int, default=3,
                       help="Number of batches for load test")
    parser.add_argument("--delay", type=float, default=1.0,
                       help="Delay between batches in load test")
    parser.add_argument("--create-audio", action="store_true",
                       help="Create test audio files")

    args = parser.parse_args()

    if args.create_audio:
        create_test_audio_files()
        return

    async def run_test():
        if args.load_test:
            await run_load_test(args.clients, args.batches, args.delay)
        else:
            await run_concurrent_clients_test(args.clients, args.duration)

    asyncio.run(run_test())

if __name__ == "__main__":
    main()

