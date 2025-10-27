# GPU Setup Guide for Windows (WSL2)

This guide will help you configure your Windows system with WSL2 to use NVIDIA GPUs with Docker for accelerated speech transcription and translation.

## Prerequisites

### 1. Check Your GPU

Open **Command Prompt** or **PowerShell** and run:

```powershell
nvidia-smi
```

You should see output similar to:

```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.82.10              Driver Version: 581.29         CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce RTX 5070 Ti     On  |   00000000:01:00.0  On |                  N/A |
+-----------------------------------------+------------------------+----------------------+
```

**If `nvidia-smi` is not found:**
- Download and install the latest NVIDIA drivers from [NVIDIA's website](https://www.nvidia.com/download/index.aspx)
- Reboot your system after installation

### 2. System Requirements

- **Windows 10/11** (64-bit) version 21H2 or higher
- **WSL2** installed and configured
- **Docker Desktop** for Windows with WSL2 backend
- **NVIDIA GPU** with driver version 470.76 or higher

---

## Step 1: Install WSL2

### Install WSL2 (If Not Already Installed)

Open **PowerShell as Administrator** and run:

```powershell
# Install WSL2 with Ubuntu
wsl --install -d Ubuntu-22.04

# Set WSL2 as default
wsl --set-default-version 2

# Verify installation
wsl --list --verbose
```

**Expected output:**
```
  NAME            STATE           VERSION
* Ubuntu-22.04    Running         2
```

**Important:** WSL2 uses the **Windows NVIDIA driver** - do NOT install NVIDIA drivers inside WSL!

---

## Step 2: Install Docker Desktop

### Download and Install

1. Download **Docker Desktop** from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
2. Run the installer
3. During installation, ensure **"Use WSL 2 instead of Hyper-V"** is selected
4. Restart your computer

### Configure Docker Desktop

1. Open **Docker Desktop**
2. Go to **Settings** → **General**
3. Ensure **"Use the WSL 2 based engine"** is checked
4. Go to **Settings** → **Resources** → **WSL Integration**
5. Enable integration for your Ubuntu distribution
6. Click **"Apply & Restart"**

---

## Step 3: Install NVIDIA Container Toolkit in WSL

Open your **WSL terminal** (Ubuntu) and run:

```bash
# Add NVIDIA Container Toolkit repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install NVIDIA Container Toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
```

---

## Step 4: Restart Docker

### Option A: Restart Docker Desktop

1. Right-click the **Docker Desktop** icon in the system tray
2. Select **"Restart Docker Desktop"**
3. Wait for Docker to fully restart

### Option B: Restart WSL

Open **PowerShell as Administrator** and run:

```powershell
wsl --shutdown
```

Then reopen your WSL terminal. Docker Desktop will auto-start.

---

## Step 5: Verify GPU Access

### Test in WSL Terminal

```bash
# Test if Docker can see your GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

**Expected output:** You should see your GPU listed (same as when you run `nvidia-smi` in PowerShell)

**If successful**, you should see something like:

```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 580.82.10              Driver Version: 581.29         CUDA Version: 13.0     |
+-----------------------------------------+------------------------+----------------------+
|   0  NVIDIA GeForce RTX 5070 Ti     On  |   00000000:01:00.0  On |                  N/A |
+-----------------------------------------+------------------------+----------------------+
```

---

## Step 6: Start Your Services

Navigate to your project directory in WSL:

```bash
cd /mnt/d/Team/Transcription-Translation1/backend/infra
docker compose up --build
```

### Watch for Success Indicators

**STT Worker logs:**
```
✓ Device: cuda
✓ Loading Faster-Whisper model: large-v3
✓ Model loaded successfully on GPU
```

**Translation Worker logs:**
```
✓ Device: cuda (FORCE_CPU=False)
✓ Loading NLLB model: facebook/nllb-200-distilled-600M
✓ Model loaded successfully on GPU
```

---

## Troubleshooting

### Issue 1: "docker: Error response from daemon: could not select device driver"

**Cause:** Docker doesn't have NVIDIA runtime configured.

**Solution:**

1. Check if `/etc/docker/daemon.json` exists in WSL:

```bash
cat /etc/docker/daemon.json
```

2. If missing or incorrect, create/edit it:

```bash
sudo nano /etc/docker/daemon.json
```

Add this content:

```json
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
```

3. Restart Docker Desktop or WSL

---

### Issue 2: "Failed to initialize NVML: Driver/library version mismatch"

**Cause:** Windows NVIDIA driver and WSL kernel mismatch.

**Solution:**

1. **Update Windows NVIDIA drivers** from [NVIDIA's website](https://www.nvidia.com/download/index.aspx)
2. **Update WSL kernel**:

```powershell
# In PowerShell as Administrator
wsl --update
wsl --shutdown
```

3. Reboot Windows

---

### Issue 3: "CUDA driver version is insufficient for CUDA runtime version"

**Cause:** Docker image uses newer CUDA than your driver supports.

**Solution:**

**Option A: Update NVIDIA Drivers** (recommended)

Download and install the latest drivers from [NVIDIA's website](https://www.nvidia.com/download/index.aspx).

**Option B: Use CPU Mode Temporarily**

Edit `backend/infra/.env`:

```bash
# STT Worker
DEVICE=cpu

# Translation Worker
FORCE_CPU=true
```

Restart services:

```bash
docker compose down
docker compose up --build
```

---

### Issue 4: Docker Desktop Not Seeing GPU

**Solution:**

1. Ensure **Docker Desktop** is fully updated
2. Go to **Settings** → **Resources** → **WSL Integration**
3. Toggle off and on your Ubuntu distribution
4. Click **"Apply & Restart"**

---

### Issue 5: WSL Can't Access /mnt/d Drive

**Cause:** Drive not mounted in WSL.

**Solution:**

1. Check mounted drives:

```bash
ls /mnt/
```

2. If `d` is missing, restart WSL:

```powershell
# In PowerShell
wsl --shutdown
```

3. Reopen WSL terminal

---

## Performance Comparison

### CPU vs GPU on Windows (WSL2)

| Model | Device | Speed (RTF*) | Latency | Memory |
|-------|--------|--------------|---------|--------|
| Whisper large-v3 | CPU (16 cores) | 1.5x | ~3000ms | 4GB RAM |
| Whisper large-v3 | RTX 3060 | 0.2x | ~400ms | 6GB VRAM |
| Whisper large-v3 | RTX 5070 Ti | 0.1x | ~200ms | 6GB VRAM |
| NLLB-600M | CPU (16 cores) | - | ~150ms | 2GB RAM |
| NLLB-600M | GPU | - | ~50ms | 2GB VRAM |

*RTF = Real-Time Factor (lower is better; 1.0 = real-time)

**GPU acceleration provides:**
- ⚡ **10-15x faster** transcription
- ⚡ **3x faster** translation
- ⚡ **Sub-200ms** end-to-end latency

---

## Configuration

### Enable/Disable GPU

Edit `backend/infra/.env`:

```bash
# === Enable GPU (default) ===
DEVICE=cuda
FORCE_CPU=false

# === Disable GPU (fallback to CPU) ===
DEVICE=cpu
FORCE_CPU=true
```

### Adjust Model Size Based on VRAM

```bash
# For 4GB VRAM
MODEL_SIZE=small

# For 8GB VRAM
MODEL_SIZE=medium

# For 12GB+ VRAM
MODEL_SIZE=large-v3
```

---

## Advanced: Multiple GPUs

If you have multiple GPUs, assign different workers to different GPUs:

Edit `backend/infra/docker-compose.yml`:

```yaml
services:
  stt_worker:
    environment:
      - CUDA_VISIBLE_DEVICES=0  # Use first GPU
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['0']
              capabilities: [gpu]

  translation_worker:
    environment:
      - CUDA_VISIBLE_DEVICES=1  # Use second GPU
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ['1']
              capabilities: [gpu]
```

---

## Quick Reference Commands

```bash
# Check GPU on Windows
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# Navigate to project (adjust drive letter if needed)
cd /mnt/d/Team/Transcription-Translation1/backend/infra

# Start services
docker compose up --build

# Monitor GPU usage (in Windows PowerShell)
nvidia-smi -l 1  # Updates every 1 second

# Check service logs
docker compose logs -f stt_worker
docker compose logs -f translation_worker

# Restart services
docker compose down
docker compose up --build
```

---

## Additional Resources

- [NVIDIA CUDA on WSL2 User Guide](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)
- [Docker Desktop WSL2 Backend](https://docs.docker.com/desktop/windows/wsl/)
- [NVIDIA Container Toolkit Documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- [WSL Documentation](https://docs.microsoft.com/en-us/windows/wsl/)

---

**Need Help?** Open an issue on GitHub with:
1. Your `nvidia-smi` output (from PowerShell)
2. Your `wsl --list --verbose` output
3. Your `docker compose logs` output
4. Docker Desktop version and settings screenshot

