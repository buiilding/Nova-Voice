"""
test_stt_enhanced.py - Enhanced STT Worker Test with Audio Preprocessing

Adds audio enhancement features:
- Volume normalization (boost quiet audio)
- Noise reduction option
- Audio format conversion to optimal settings
- Detailed audio analysis before submission
"""

import asyncio
import json
import base64
import time
import os
import sys
import io
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import redis.asyncio as redis
from redis.exceptions import ConnectionError
import numpy as np
from pydub import AudioSegment
from pydub.effects import normalize, compress_dynamic_range

# === Configuration ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
AUDIO_JOBS_STREAM = "audio_jobs"
RESULTS_CHANNEL_PREFIX = "results:"
TEST_CLIENT_ID = f"test-client-{int(time.time())}"
TEST_AUDIOS_DIR = "test_audios"

# Audio enhancement settings
ENABLE_NORMALIZATION = True  # Boost audio to optimal levels
ENABLE_COMPRESSION = True    # Dynamic range compression
TARGET_SAMPLE_RATE = 16000   # Whisper's native sample rate
TARGET_CHANNELS = 1          # Mono
MIN_DURATION_MS = 100        # Skip files shorter than this

SUPPORTED_FORMATS = {'.wav', '.mp3', '.m4a', '.ogg', '.flac', '.opus', '.webm'}


class STTTester:
    def __init__(self, audio_dir: str = TEST_AUDIOS_DIR):
        self.audio_dir = Path(audio_dir)
        self.redis = None
        self.pubsub = None
        self.client_id = TEST_CLIENT_ID
        self.results = []
        self.pending_jobs = {}
        
    async def connect_redis(self):
        """Connect to Redis"""
        print(f"Connecting to Redis: {REDIS_URL}")
        self.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
        await self.redis.ping()
        print("Connected to Redis\n")
        
    async def subscribe_to_results(self):
        """Subscribe to results channel"""
        channel = f"{RESULTS_CHANNEL_PREFIX}{self.client_id}"
        print(f"Subscribing to channel: {channel}")
        
        self.pubsub = self.redis.pubsub()
        await self.pubsub.subscribe(channel)
        print(f"Subscribed to results channel\n")
        
    async def listen_for_results(self):
        """Listen for transcription results"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    result = json.loads(message["data"])
                    job_id = result.get("job_id")
                    
                    if job_id in self.pending_jobs:
                        submit_time = self.pending_jobs[job_id]["submit_time"]
                        total_time = time.time() - submit_time
                        
                        result_data = {
                            "job_id": job_id,
                            "filename": self.pending_jobs[job_id]["filename"],
                            "original_size_kb": self.pending_jobs[job_id]["original_size_kb"],
                            "processed_size_kb": self.pending_jobs[job_id]["processed_size_kb"],
                            "duration_s": self.pending_jobs[job_id]["duration_s"],
                            "text": result.get("text", ""),
                            "language": result.get("language", ""),
                            "language_probability": result.get("language_probability", 0.0),
                            "segments": result.get("segments", 0),
                            "processing_time": result.get("processing_time", 0.0),
                            "total_time": total_time,
                            "worker_id": result.get("worker_id", "unknown"),
                            "status": result.get("status", "unknown"),
                            "error": result.get("error", None)
                        }
                        
                        self.results.append(result_data)
                        del self.pending_jobs[job_id]
                        
                        status = "OK" if result_data["status"] == "ok" else "FAIL"
                        text_preview = result_data['text'][:80] if result_data['text'] else "[EMPTY]"
                        print(f"[{status}] {result_data['filename']} ({result_data['duration_s']:.1f}s): {text_preview}")
                        print(f"      Processing: {result_data['processing_time']:.2f}s | Total: {total_time:.2f}s | Lang: {result_data['language']}\n")
                        
        except asyncio.CancelledError:
            pass
    
    def enhance_audio(self, audio_segment: AudioSegment, filename: str) -> AudioSegment:
        """
        Enhance audio for better transcription:
        - Convert to mono
        - Resample to 16kHz
        - Normalize volume
        - Apply compression
        """
        print(f"  Enhancing: {filename}")
        
        # Get original stats
        orig_duration = len(audio_segment) / 1000.0
        orig_channels = audio_segment.channels
        orig_rate = audio_segment.frame_rate
        orig_rms = audio_segment.rms
        
        print(f"    Original: {orig_duration:.2f}s, {orig_channels}ch, {orig_rate}Hz, RMS={orig_rms}")
        
        # Convert to mono
        if audio_segment.channels > 1:
            audio_segment = audio_segment.set_channels(1)
            
        # Resample to target rate
        if audio_segment.frame_rate != TARGET_SAMPLE_RATE:
            audio_segment = audio_segment.set_frame_rate(TARGET_SAMPLE_RATE)
            
        # Normalize volume (boost to optimal level)
        if ENABLE_NORMALIZATION:
            audio_segment = normalize(audio_segment, headroom=0.1)
            
        # Apply dynamic range compression (makes quiet parts louder)
        if ENABLE_COMPRESSION:
            audio_segment = compress_dynamic_range(
                audio_segment,
                threshold=-20.0,
                ratio=4.0,
                attack=5.0,
                release=50.0
            )
            
        new_rms = audio_segment.rms
        print(f"    Enhanced: {len(audio_segment)/1000.0:.2f}s, 1ch, {TARGET_SAMPLE_RATE}Hz, RMS={new_rms} (boost: {new_rms/orig_rms:.1f}x)")
        
        return audio_segment
            
    def load_and_analyze_audio(self, file_path: Path) -> Dict[str, Any]:
        """Load audio file and analyze its properties"""
        try:
            # Load audio based on format
            if file_path.suffix.lower() == '.mp3':
                audio = AudioSegment.from_mp3(file_path)
            elif file_path.suffix.lower() == '.wav':
                audio = AudioSegment.from_wav(file_path)
            elif file_path.suffix.lower() == '.m4a':
                audio = AudioSegment.from_file(file_path, format='m4a')
            elif file_path.suffix.lower() == '.ogg':
                audio = AudioSegment.from_ogg(file_path)
            elif file_path.suffix.lower() == '.flac':
                audio = AudioSegment.from_file(file_path, format='flac')
            else:
                audio = AudioSegment.from_file(file_path)
                
            duration_ms = len(audio)
            duration_s = duration_ms / 1000.0
            
            # Skip very short files
            if duration_ms < MIN_DURATION_MS:
                print(f"  SKIP: {file_path.name} - too short ({duration_s:.2f}s)")
                return None
                
            # Enhance audio
            enhanced_audio = self.enhance_audio(audio, file_path.name)
            
            # Export to WAV format in memory (best for Whisper)
            buffer = io.BytesIO()
            enhanced_audio.export(buffer, format="wav")
            audio_bytes = buffer.getvalue()
            
            return {
                "path": file_path,
                "filename": file_path.name,
                "original_size_kb": file_path.stat().st_size / 1024,
                "processed_size_kb": len(audio_bytes) / 1024,
                "duration_s": duration_s,
                "audio_bytes": audio_bytes,
                "sample_rate": TARGET_SAMPLE_RATE,
                "channels": TARGET_CHANNELS
            }
            
        except Exception as e:
            print(f"  ERROR loading {file_path.name}: {e}")
            return None
            
    def load_audio_files(self) -> List[Dict[str, Any]]:
        """Load and preprocess all audio files"""
        if not self.audio_dir.exists():
            print(f"Directory not found: {self.audio_dir}")
            return []
            
        print(f"Loading audio files from: {self.audio_dir}")
        print(f"Enhancement: Normalize={ENABLE_NORMALIZATION}, Compress={ENABLE_COMPRESSION}")
        print("-" * 80)
        
        audio_files = []
        
        for file_path in sorted(self.audio_dir.iterdir()):
            if file_path.suffix.lower() in SUPPORTED_FORMATS:
                audio_data = self.load_and_analyze_audio(file_path)
                if audio_data:
                    audio_files.append(audio_data)
                    
        print("-" * 80)
        print(f"Loaded {len(audio_files)} valid audio files\n")
        
        return audio_files
        
    async def submit_audio_job(self, audio_file: Dict[str, Any], job_index: int) -> str:
        """Submit processed audio to STT worker"""
        # Encode audio
        audio_b64 = base64.b64encode(audio_file["audio_bytes"]).decode('utf-8')
            
        # Create job
        job_id = f"test-job-{job_index}-{int(time.time() * 1000)}"
        
        job_data = {
            "job_id": job_id,
            "client_id": self.client_id,
            "segment_id": f"segment-{job_index}",
            "audio_bytes_b64": audio_b64,
            "source_lang": "en",
            "target_lang": "vi",
            "translation_enabled": "false",
            "is_final": "true",
            "timestamp": str(time.time())
        }
        
        # Track pending job
        self.pending_jobs[job_id] = {
            "filename": audio_file["filename"],
            "original_size_kb": audio_file["original_size_kb"],
            "processed_size_kb": audio_file["processed_size_kb"],
            "duration_s": audio_file["duration_s"],
            "submit_time": time.time()
        }
        
        # Submit to Redis Stream
        await self.redis.xadd(AUDIO_JOBS_STREAM, job_data)
        
        return job_id
        
    async def run_test(self, timeout: int = 300):
        """Run the transcription test"""
        print("="*80)
        print("STT WORKER TRANSCRIPTION TEST (ENHANCED)")
        print("="*80)
        print(f"Client ID: {self.client_id}")
        print(f"Test Directory: {self.audio_dir}")
        print(f"Translation: DISABLED")
        print(f"Audio Enhancement: ENABLED")
        print("="*80 + "\n")
        
        # Load and preprocess audio files
        audio_files = self.load_audio_files()
        
        if not audio_files:
            print("No valid audio files to test")
            return
            
        # Display summary
        total_duration = sum(a["duration_s"] for a in audio_files)
        print(f"Test Summary:")
        print(f"  Files: {len(audio_files)}")
        print(f"  Total duration: {total_duration:.1f}s")
        print(f"  Avg duration: {total_duration/len(audio_files):.1f}s per file")
        print()
        
        # Connect and subscribe
        await self.connect_redis()
        await self.subscribe_to_results()
        
        # Start listening
        listener_task = asyncio.create_task(self.listen_for_results())
        
        # Submit all jobs
        print(f"Submitting {len(audio_files)} jobs...")
        print("="*80 + "\n")
        
        start_time = time.time()
        
        for i, audio_file in enumerate(audio_files):
            job_id = await self.submit_audio_job(audio_file, i)
            print(f"Submitted: {audio_file['filename']} ({audio_file['duration_s']:.1f}s)")
            await asyncio.sleep(0.05)
            
        print(f"\nAll jobs submitted. Waiting for results...\n")
        
        # Wait for results
        elapsed = 0
        while self.pending_jobs and elapsed < timeout:
            await asyncio.sleep(1)
            elapsed = time.time() - start_time
            
            if elapsed % 10 == 0:
                remaining = len(self.pending_jobs)
                completed = len(self.results)
                print(f"[{elapsed:.0f}s] Completed: {completed}/{len(audio_files)} | Pending: {remaining}")
                
        listener_task.cancel()
        
        total_time = time.time() - start_time
        
        # Generate report
        self.print_report(total_time, len(audio_files))
        
    def print_report(self, total_time: float, total_files: int):
        """Print test report"""
        print("\n" + "="*80)
        print("TRANSCRIPTION TEST REPORT")
        print("="*80)
        
        if not self.results:
            print("No results received")
            return
            
        successful = [r for r in self.results if r["status"] == "ok" and r["text"].strip()]
        empty = [r for r in self.results if r["status"] == "ok" and not r["text"].strip()]
        failed = [r for r in self.results if r["status"] != "ok"]
        
        print(f"\nResults:")
        print(f"  Total files: {total_files}")
        print(f"  Transcribed: {len(successful)}")
        print(f"  Empty transcriptions: {len(empty)}")
        print(f"  Failed: {len(failed)}")
        print(f"  Still pending: {len(self.pending_jobs)}")
        print(f"  Total time: {total_time:.2f}s")
        
        if successful:
            total_duration = sum(r["duration_s"] for r in successful)
            total_proc_time = sum(r["processing_time"] for r in successful)
            avg_proc_time = total_proc_time / len(successful)
            rtf = total_proc_time / total_duration if total_duration > 0 else 0
            
            print(f"\nPerformance:")
            print(f"  Total audio duration: {total_duration:.1f}s")
            print(f"  Total processing time: {total_proc_time:.2f}s")
            print(f"  Avg processing time: {avg_proc_time:.2f}s per file")
            print(f"  Real-time factor: {rtf:.2f}x (lower is better)")
            print(f"  Throughput: {len(successful) / total_time:.2f} files/second")
            
        # Show empty transcriptions
        if empty:
            print(f"\nEmpty Transcriptions ({len(empty)} files):")
            for r in empty:
                print(f"  - {r['filename']} ({r['duration_s']:.1f}s, {r['segments']} segments)")
                
        # Detailed results
        print(f"\nDetailed Results:")
        print("-" * 80)
        
        for i, result in enumerate(sorted(self.results, key=lambda x: x["filename"]), 1):
            status = "OK" if (result["status"] == "ok" and result["text"].strip()) else "EMPTY" if (result["status"] == "ok") else "FAIL"
            print(f"\n{i}. [{status}] {result['filename']}")
            print(f"   Duration: {result['duration_s']:.1f}s | Processing: {result['processing_time']:.2f}s")
            print(f"   Size: {result['original_size_kb']:.1f}KB -> {result['processed_size_kb']:.1f}KB")
            print(f"   Language: {result['language']} ({result['language_probability']:.1%})")
            print(f"   Segments: {result['segments']}")
            
            if result["text"].strip():
                text = result['text'][:150] + "..." if len(result['text']) > 150 else result['text']
                print(f"   Text: {text}")
            else:
                print(f"   Text: [EMPTY - possible causes: silence, VAD filter, or very short speech]")
                
        print("\n" + "="*80)
        
    def save_results(self, filename: str = None):
        """Save results to JSON"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"stt_enhanced_results_{timestamp}.json"
            
        output = {
            "test_info": {
                "client_id": self.client_id,
                "test_directory": str(self.audio_dir),
                "timestamp": datetime.now().isoformat(),
                "enhancement_enabled": True,
                "normalization": ENABLE_NORMALIZATION,
                "compression": ENABLE_COMPRESSION
            },
            "results": self.results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
            
        print(f"\nResults saved to: {filename}")
        
    async def cleanup(self):
        """Cleanup"""
        if self.pubsub:
            await self.pubsub.aclose()
        if self.redis:
            await self.redis.aclose()


async def main():
    audio_dir = sys.argv[1] if len(sys.argv) > 1 else TEST_AUDIOS_DIR
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    
    tester = STTTester(audio_dir=audio_dir)
    
    try:
        await tester.run_test(timeout=timeout)
        tester.save_results()
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        
    except Exception as e:
        print(f"\n\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await tester.cleanup()
        print("\nTest complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nCancelled")
        sys.exit(0)