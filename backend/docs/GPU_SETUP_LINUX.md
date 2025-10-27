# GPU Setup Guide for Linux

This guide will help you configure your Linux system to use NVIDIA GPUs with Docker for accelerated speech transcription and translation.

## Prerequisites

### 1. Check Your GPU

Open a terminal and run:

```bash
nvidia-smi
```

You should see output similar to:

```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03             Driver Version: 535.129.03   CUDA Version: 12.2      |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
|   0  NVIDIA GeForce RTX 4090        Off |   00000000:01:00.0  On |                  N/A |
+-----------------------------------------+------------------------+----------------------+
```

**If `nvidia-smi` is not found:**
You need to install NVIDIA drivers first (see [Installing NVIDIA Drivers](#installing-nvidia-drivers) below).

### 2. System Requirements

- **Linux Distribution**: Ubuntu 20.04/22.04, Debian 11/12, CentOS 8, RHEL 8, or similar
- **Docker**: Version 19.03 or higher
- **NVIDIA GPU**: With driver version 470.76 or higher
- **Kernel**: 4.15 or higher (for proper CUDA support)

---

## Step 1: Install NVIDIA Drivers (If Not Already Installed)

### For Ubuntu/Debian

```bash
# Update package list
sudo apt update

# Check available NVIDIA drivers
ubuntu-drivers devices

# Install recommended driver (automatic)
sudo ubuntu-drivers autoinstall

# Or install specific version (e.g., 535)
sudo apt install nvidia-driver-535

# Reboot system
sudo reboot
```

### For Fedora/RHEL/CentOS

```bash
# Enable RPM Fusion repository
sudo dnf install https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
sudo dnf install https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm

# Install NVIDIA driver
sudo dnf install akmod-nvidia

# Reboot system
sudo reboot
```

### Verify Installation

After reboot, check if drivers are working:

```bash
nvidia-smi
```

---

## Step 2: Install Docker (If Not Already Installed)

### For Ubuntu/Debian

```bash
# Remove old versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install dependencies
sudo apt update
sudo apt install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Add your user to docker group (avoid using sudo)
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify installation
docker --version
```

### For Fedora/RHEL/CentOS

```bash
# Install Docker
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
```

---

## Step 3: Install NVIDIA Container Toolkit

### For Ubuntu/Debian

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
```

### For Fedora/RHEL/CentOS

```bash
# Add NVIDIA Container Toolkit repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Install NVIDIA Container Toolkit
sudo dnf install -y nvidia-container-toolkit
```

---

## Step 4: Configure Docker Runtime

```bash
# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker

# Restart Docker daemon
sudo systemctl restart docker
```

### Verify Configuration

Check that Docker daemon config was updated:

```bash
cat /etc/docker/daemon.json
```

Should contain:

```json
{
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    }
}
```

---

## Step 5: Verify GPU Access

### Test Docker GPU Access

```bash
# Test if Docker can see your GPU
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

**Expected output:** You should see your GPU listed, just like when you run `nvidia-smi` directly.

**If successful:**

```
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 535.129.03             Driver Version: 535.129.03   CUDA Version: 12.2      |
+-----------------------------------------+------------------------+----------------------+
|   0  NVIDIA GeForce RTX 4090        Off |   00000000:01:00.0  On |                  N/A |
+-----------------------------------------+------------------------+----------------------+
```

---

## Step 6: Start Your Services

Navigate to your project directory:

```bash
cd ~/Transcription-Translation1/backend/infra
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

1. Check if NVIDIA Container Toolkit is installed:

```bash
nvidia-ctk --version
```

2. Reconfigure Docker runtime:

```bash
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

3. Verify `/etc/docker/daemon.json` has correct content (see Step 4)

---

### Issue 2: "Failed to initialize NVML: Driver/library version mismatch"

**Cause:** Kernel module and user-space library mismatch (usually after driver update).

**Solution:**

```bash
# Reload NVIDIA kernel modules
sudo rmmod nvidia_uvm
sudo rmmod nvidia_drm
sudo rmmod nvidia_modeset
sudo rmmod nvidia
sudo modprobe nvidia
sudo modprobe nvidia_modeset
sudo modprobe nvidia_drm
sudo modprobe nvidia_uvm

# If that fails, reboot
sudo reboot
```

---

### Issue 3: "CUDA driver version is insufficient for CUDA runtime version"

**Cause:** Docker image uses newer CUDA than your driver supports.

**Solution:**

**Option A: Update NVIDIA Drivers** (recommended)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt upgrade nvidia-driver-*

# Fedora/RHEL
sudo dnf update nvidia-driver-*

# Reboot
sudo reboot
```

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

### Issue 4: Permission Denied When Running Docker

**Cause:** User not in `docker` group.

**Solution:**

```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and back in, or run:
newgrp docker

# Verify
docker ps
```

---

### Issue 5: nvidia-smi Shows GPU But Docker Doesn't

**Cause:** NVIDIA Container Toolkit not properly configured.

**Solution:**

```bash
# Reinstall NVIDIA Container Toolkit
sudo apt remove --purge nvidia-container-toolkit
sudo apt autoremove
sudo apt install -y nvidia-container-toolkit

# Reconfigure Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Test again
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

---

## Performance Comparison

### CPU vs GPU on Linux

| Model | Device | Speed (RTF*) | Latency | Memory |
|-------|--------|--------------|---------|--------|
| Whisper large-v3 | CPU (16 cores) | 1.5x | ~3000ms | 4GB RAM |
| Whisper large-v3 | RTX 3060 | 0.2x | ~400ms | 6GB VRAM |
| Whisper large-v3 | RTX 4090 | 0.08x | ~160ms | 6GB VRAM |
| NLLB-600M | CPU (16 cores) | - | ~150ms | 2GB RAM |
| NLLB-600M | GPU | - | ~40ms | 2GB VRAM |

*RTF = Real-Time Factor (lower is better; 1.0 = real-time)

**GPU acceleration provides:**
- ⚡ **10-20x faster** transcription
- ⚡ **3-4x faster** translation
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

### Check GPU IDs

```bash
nvidia-smi -L
```

Output:
```
GPU 0: NVIDIA GeForce RTX 4090
GPU 1: NVIDIA GeForce RTX 3090
```

---

## Production Deployment Considerations

### Systemd Service

Create a systemd service for auto-start:

```bash
sudo nano /etc/systemd/system/nova-voice.service
```

Content:

```ini
[Unit]
Description=Nova Voice Backend Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/youruser/Transcription-Translation1/backend/infra
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=youruser

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nova-voice
sudo systemctl start nova-voice
```

### Resource Limits

Edit `docker-compose.yml` to add resource limits:

```yaml
services:
  stt_worker:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## Quick Reference Commands

```bash
# Check GPU status
nvidia-smi

# Monitor GPU in real-time
watch -n 1 nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# Start services
cd ~/Transcription-Translation1/backend/infra
docker compose up --build

# Start services in background
docker compose up -d --build

# Check service logs
docker compose logs -f stt_worker
docker compose logs -f translation_worker

# Restart services
docker compose restart

# Stop services
docker compose down

# Check Docker daemon status
sudo systemctl status docker

# Restart Docker daemon
sudo systemctl restart docker
```

---

## Additional Resources

- [NVIDIA CUDA Installation Guide for Linux](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/index.html)
- [Docker Installation on Linux](https://docs.docker.com/engine/install/)
- [NVIDIA Container Toolkit Documentation](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- [Docker Compose CLI Reference](https://docs.docker.com/compose/reference/)

---

**Need Help?** Open an issue on GitHub with:
1. Your `nvidia-smi` output
2. Your `cat /etc/docker/daemon.json` output
3. Your `docker compose logs` output
4. Your Linux distribution and version (`lsb_release -a` or `cat /etc/os-release`)

