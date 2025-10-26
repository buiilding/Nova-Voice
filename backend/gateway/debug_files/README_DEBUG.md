# Audio Debug Tools

This directory contains tools to monitor and debug the audio processing pipeline between the gateway and workers by saving audio chunks for analysis.

## Tools

### 1. `debug_audio_monitor.py` - Audio Chunk Saver

Monitors the Redis `audio_jobs` stream and automatically saves all audio chunks sent to workers as WAV files.

**Features:**
- Automatically saves all audio chunks as WAV files for analysis
- Filter by specific client ID
- Monitor job metadata (duration, timestamps, etc.)
- Quiet mode for minimal output

**Usage:**

```bash
# Install dependencies
pip install redis[hiredis] numpy scipy

# Save all audio chunks to debug_audio/ directory
python debug_audio_monitor.py

# Save to custom directory
python debug_audio_monitor.py --save-dir my_audio_debug/

# Monitor specific client only
python debug_audio_monitor.py --client-id client_123

# Quiet mode (minimal output)
python debug_audio_monitor.py --quiet
```

**Output:**
```
📡 Monitoring Redis stream: audio_jobs
💾 Saving audio to: debug_audio/
Press Ctrl+C to stop...

📡 Job: abc12345 | Client: client_abc | Duration: 1.23s
💾 Saved: debug_audio/143022_client_abc_1698765432_abc12345.wav (1.23s)
```

### 2. `play_saved_audio.py` - Play Saved WAV Files

Simple utility to play WAV files saved by the debug monitor.

**Usage:**

```bash
# Play single file
python play_saved_audio.py debug_audio/143022_client_abc_1698765432_abc12345.wav

# Play all files in directory
python play_saved_audio.py --dir debug_audio/
```

## Audio Enhancement Debugging

The gateway applies several audio enhancements before sending to workers:

1. **Format Detection**: Detects audio bit depth and channels
2. **Mono Conversion**: Converts stereo to mono for better transcription
3. **Resampling**: Converts to 16kHz (optimal for Whisper)
4. **Volume Normalization**: Boosts quiet speech (aggressive, headroom=0.05)
5. **Dynamic Compression**: Reduces dynamic range for consistent levels
6. **High-pass Filter**: Gentle 80Hz filter to reduce microphone rumble

Use these tools to verify that the audio enhancements are working correctly and that the audio quality sent to workers matches your expectations.

## Troubleshooting

**Redis connection issues:**
- Ensure Redis is running on the URL specified in `config.py`
- Check `REDIS_URL` environment variable

**Permission errors:**
- Ensure write permissions for save directories
- Check Redis authentication if required

**No audio files being saved:**
- Verify Redis is running and the gateway is sending jobs
- Check that the specified save directory is writable
- Use `--client-id` to filter for specific clients if needed

## File Naming Convention

Saved WAV files follow this pattern:
```
{HHMMSS}_{microseconds}_{client_id}_{segment_id}_{job_id_8chars}.wav

Example: 143022_123456_client_abc_1698765432_abc12345.wav
- 143022: Timestamp (14:30:22)
- 123456: Microseconds for uniqueness
- client_abc: Client identifier
- 1698765432: Segment ID (Unix timestamp)
- abc12345: First 8 chars of job ID
```

## Example Workflow

1. Start your gateway and workers
2. Run the debug monitor: `python debug_audio_monitor.py`
3. Speak into your application
4. Review saved WAV files in the `debug_audio/` directory for quality analysis
5. Use `play_saved_audio.py` to replay specific chunks
