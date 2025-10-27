# GPU Setup Guide for macOS

**⚠️ Important Notice: NVIDIA GPU Support on macOS**

NVIDIA GPUs are **not supported on modern macOS** systems (macOS 10.14 Mojave and later). Apple deprecated NVIDIA GPU support in 2018.

However, this guide covers:
1. **Apple Silicon (M1/M2/M3) GPU acceleration** - Native support
2. **Intel Mac with AMD GPU** - Limited support via ROCm
3. **Backend-only deployment** - Run services on Linux/Windows with GPU

---

## Overview

### Option 1: Apple Silicon Macs (M1/M2/M3) - ✅ Recommended

Apple Silicon Macs have integrated GPUs that can be used for machine learning workloads through **Metal Performance Shaders (MPS)**.

**Performance:**
- ⚡ **5-10x faster** than CPU-only
- 🔋 **Power efficient** (M-series chips excel at ML tasks)
- 📦 **Native support** in PyTorch and TensorFlow

**Limitations:**
- Not as fast as dedicated NVIDIA GPUs
- Docker GPU support is experimental/limited
- Best performance with native Python (not Docker)

### Option 2: Intel Mac with AMD GPU - ⚠️ Limited Support

AMD GPUs on Intel Macs have **very limited** support for ML workloads:
- ROCm (AMD's CUDA alternative) is not officially supported on macOS
- Docker does not support AMD GPU passthrough on macOS
- Best option: CPU-only or remote GPU server

### Option 3: Remote GPU Server - ✅ Recommended for Production

Run the **frontend on Mac**, but connect to a **backend on Linux/Windows with NVIDIA GPU**.

---

## Setup Guide for Apple Silicon Macs (M1/M2/M3)

### Prerequisites

- **macOS 12.3 or later** (for MPS support)
- **Apple Silicon** (M1, M1 Pro, M1 Max, M1 Ultra, M2, M2 Pro, M2 Max, M2 Ultra, M3, M3 Pro, M3 Max)
- **Xcode Command Line Tools**
- **Homebrew** (package manager)

### Check Your System

```bash
# Check if you have Apple Silicon
uname -m
# Should output: arm64

# Check macOS version
sw_vers
# ProductVersion should be 12.3 or higher
```

---

## Installation Steps

### Step 1: Install Homebrew (If Not Already Installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Python 3.10+

```bash
# Install Python via Homebrew
brew install python@3.10

# Verify installation
python3 --version
```

### Step 3: Install PyTorch with MPS Support

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install PyTorch with MPS support (Apple Silicon)
pip install torch torchvision torchaudio

# Verify MPS is available
python3 -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

**Expected output:**
```
MPS available: True
```

### Step 4: Install Project Dependencies

```bash
cd ~/Transcription-Translation1/backend

# Install dependencies
pip install -r requirements.txt
pip install -r gateway/requirements.txt
pip install -r stt_worker/requirements.txt
pip install -r translation_worker/requirements.txt
```

### Step 5: Install Redis

```bash
# Install Redis via Homebrew
brew install redis

# Start Redis
brew services start redis

# Verify Redis is running
redis-cli ping
# Should output: PONG
```

---

## Configuration for Apple Silicon GPU

### Edit Environment Configuration

Create `backend/infra/.env` from the example:

```bash
cd backend/infra
cp ../.env_example .env
```

Edit `.env` for Apple Silicon:

```bash
# === Apple Silicon GPU Configuration ===
# Note: MPS (Metal Performance Shaders) is used instead of CUDA

# STT Worker - Use MPS device
DEVICE=mps
MODEL_SIZE=medium  # Start with medium, adjust based on performance

# Translation Worker - Use MPS
FORCE_CPU=false
NLLB_MODEL=facebook/nllb-200-distilled-600M

# Redis
REDIS_URL=redis://localhost:6379
```

### Modify Worker Code for MPS Support

The worker code needs to be updated to support MPS. Create a patch file:

**For STT Worker** (`backend/stt_worker/config.py`):

```python
# Detect device (add MPS support)
if torch.backends.mps.is_available() and DEVICE == "mps":
    DEVICE = "mps"
    print("Using Apple Silicon GPU (MPS)")
elif torch.cuda.is_available() and DEVICE == "cuda":
    DEVICE = "cuda"
    print(f"Using CUDA GPU: {torch.cuda.get_device_name(0)}")
else:
    DEVICE = "cpu"
    print("Using CPU")
```

**For Translation Worker** (`backend/translation_worker/config.py`):

```python
# Device configuration with MPS support
if torch.backends.mps.is_available() and not FORCE_CPU:
    DEVICE = "mps"
    print("Using Apple Silicon GPU (MPS)")
elif torch.cuda.is_available() and not FORCE_CPU:
    DEVICE = "cuda"
    print(f"Using CUDA GPU")
else:
    DEVICE = "cpu"
    print("Using CPU (FORCE_CPU=True or no GPU available)")
```

---

## Running Services Locally (Not Docker)

**Note:** Docker Desktop for Mac **does not support GPU passthrough** well. For best performance on Apple Silicon, run services **natively** without Docker.

### Start All Services

```bash
cd backend

# Terminal 1: Start Gateway
source venv/bin/activate
python -m gateway.gateway

# Terminal 2: Start STT Worker
source venv/bin/activate
python -m stt_worker.worker

# Terminal 3: Start Translation Worker
source venv/bin/activate
python -m translation_worker.worker
```

Or use the provided script:

```bash
cd backend
./run-services.sh dev
```

---

## Docker Desktop (CPU-Only)

If you must use Docker on Mac:

### Install Docker Desktop

1. Download **Docker Desktop for Mac** from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. Install and start Docker Desktop
3. **Note:** GPU acceleration is **not available** in Docker on Mac

### Configure for CPU

Edit `backend/infra/.env`:

```bash
# === Docker CPU-Only Configuration ===
DEVICE=cpu
FORCE_CPU=true
MODEL_SIZE=small  # Use smaller models for CPU
```

### Start Services

```bash
cd backend/infra
docker compose up --build
```

**Performance Note:** CPU-only Docker on Mac will be significantly slower than native Python with MPS.

---

## Option 3: Remote GPU Server (Recommended for Production)

The best option for Mac users is to run the backend on a **remote Linux/Windows server with NVIDIA GPU** and connect to it from your Mac.

### Architecture

```
┌─────────────────────────────────┐
│  Mac (Frontend Only)            │
│  - Electron App                 │
│  - WebSocket Client             │
└─────────────────────────────────┘
              │
              │ WebSocket over Internet
              │
              ▼
┌─────────────────────────────────┐
│  Linux/Windows Server (Backend) │
│  - Gateway Service              │
│  - STT Worker (NVIDIA GPU)      │
│  - Translation Worker (GPU)     │
│  - Redis                        │
└─────────────────────────────────┘
```

### Setup Steps

#### 1. On Remote Server (Linux/Windows)

Follow the appropriate GPU setup guide:
- **Windows**: [GPU_SETUP_WINDOWS.md](GPU_SETUP_WINDOWS.md)
- **Linux**: [GPU_SETUP_LINUX.md](GPU_SETUP_LINUX.md)

#### 2. Configure Remote Access

On the remote server, edit `backend/infra/.env`:

```bash
# Allow connections from any IP
GATEWAY_PORT=5026

# Optional: Add authentication/SSL
```

#### 3. On Your Mac

**Frontend Configuration:**

Edit frontend configuration to connect to remote server:

```typescript
// frontend/lib/config.ts or environment variable
const GATEWAY_URL = "ws://your-server-ip:5026"
```

**Security Note:** Use a VPN or SSH tunnel for secure connections:

```bash
# SSH tunnel to remote server
ssh -L 5026:localhost:5026 user@remote-server

# Now connect to ws://localhost:5026 from your Mac
```

---

## Performance Comparison

### Apple Silicon (M1/M2/M3) vs NVIDIA GPU

| Model | Device | Speed (RTF*) | Latency | Power |
|-------|--------|--------------|---------|-------|
| Whisper large-v3 | M1 Pro (CPU) | 2.0x | ~4000ms | High |
| Whisper large-v3 | M1 Pro (MPS) | 0.4x | ~800ms | Low |
| Whisper large-v3 | M2 Max (MPS) | 0.3x | ~600ms | Low |
| Whisper large-v3 | RTX 4090 (CUDA) | 0.08x | ~160ms | Very High |
| NLLB-600M | M1 Pro (MPS) | - | ~80ms | Low |
| NLLB-600M | RTX 4090 (CUDA) | - | ~40ms | Very High |

*RTF = Real-Time Factor (lower is better; 1.0 = real-time)

**Summary:**
- ⚡ Apple Silicon MPS: **5-10x faster** than CPU, **40% of NVIDIA GPU speed**
- 🔋 Apple Silicon: Much more **power efficient**
- 🚀 NVIDIA GPU: **Fastest**, but requires separate machine

---

## Troubleshooting

### Issue 1: MPS Not Available

**Check:**

```bash
python3 -c "import torch; print(f'MPS available: {torch.backends.mps.is_available()}')"
```

**If False:**
- Ensure you have macOS 12.3 or later
- Ensure you're on Apple Silicon (M1/M2/M3)
- Reinstall PyTorch: `pip install --upgrade torch`

---

### Issue 2: Model Loading Errors with MPS

**Error:** `RuntimeError: MPS backend out of memory`

**Solution:**
- Use smaller models: `MODEL_SIZE=small` or `MODEL_SIZE=base`
- Close other applications to free memory
- Restart your Mac

---

### Issue 3: Docker Container Can't See GPU

**This is expected.** Docker Desktop for Mac does not support GPU passthrough.

**Solution:** Run services natively (see "Running Services Locally" above)

---

### Issue 4: Slow Performance Even with MPS

**Check if MPS is actually being used:**

```bash
# In your service logs, look for:
# "Using Apple Silicon GPU (MPS)"
# NOT: "Using CPU"
```

**Common causes:**
- Code not updated to use MPS (see configuration section)
- Model fallback to CPU due to compatibility issues
- Too large model for available memory

---

## Recommended Configuration for Different Mac Models

### M1/M2 Base (8GB RAM)
```bash
MODEL_SIZE=small
NLLB_MODEL=facebook/nllb-200-distilled-600M
```

### M1/M2 Pro (16GB RAM)
```bash
MODEL_SIZE=medium
NLLB_MODEL=facebook/nllb-200-distilled-600M
```

### M1/M2 Max/Ultra (32GB+ RAM)
```bash
MODEL_SIZE=large-v3
NLLB_MODEL=facebook/nllb-200-1.3B
```

### M3 Series
Same as M1/M2, but expect slightly better performance.

---

## Quick Reference Commands

```bash
# Check Apple Silicon
uname -m  # Should output: arm64

# Check MPS availability
python3 -c "import torch; print(f'MPS: {torch.backends.mps.is_available()}')"

# Start Redis
brew services start redis

# Check Redis
redis-cli ping

# Start services natively
cd backend
source venv/bin/activate
./run-services.sh dev

# Or start individually
python -m gateway.gateway &
python -m stt_worker.worker &
python -m translation_worker.worker &

# Monitor resource usage
top -pid $(pgrep Python)
```

---

## Additional Resources

- [PyTorch MPS Documentation](https://pytorch.org/docs/stable/notes/mps.html)
- [Apple Metal Performance Shaders](https://developer.apple.com/metal/pytorch/)
- [Faster-Whisper on Apple Silicon](https://github.com/SYSTRAN/faster-whisper/discussions/288)
- [Docker Desktop for Mac](https://docs.docker.com/desktop/mac/install/)

---

## Conclusion

**For Mac Users:**

1. **Best Option**: Apple Silicon with native Python + MPS ✅
   - Good performance (5-10x faster than CPU)
   - Power efficient
   - Runs locally

2. **Second Best**: Remote GPU Server (Linux/Windows) ✅
   - Best performance (NVIDIA GPU)
   - Mac runs frontend only
   - Requires network connection

3. **Fallback**: CPU-Only Mode ⚠️
   - Works but slow
   - Use smaller models
   - Acceptable for development/testing

**Note:** The **frontend currently only works on Windows** due to native keyboard integration. If you're developing on Mac, you're likely working on the backend services only.

---

**Need Help?** Open an issue on GitHub with:
1. Your Mac model and chip (M1/M2/M3)
2. macOS version (`sw_vers`)
3. Output of MPS check command
4. Service logs showing errors

