# NLLB-200 Translation Worker

High-performance translation worker using Meta's NLLB-200 model with GPU acceleration.

## Key Features

- **GPU-Accelerated**: Automatic CUDA detection with float16 precision for 2x faster inference
- **Memory Optimized**: Automatic garbage collection, CUDA cache clearing, and proper tensor cleanup
- **Production Ready**: Thread pool execution, comprehensive metrics, health checks
- **Horizontally Scalable**: Redis consumer groups for distributed processing
- **7 Languages Supported**: English, Spanish, French, German, Vietnamese, Chinese, Japanese

## Language Codes

The worker uses two-character ISO codes that are automatically mapped to NLLB-200 format:

| Input Code | NLLB-200 Code | Language |
|------------|---------------|----------|
| `en` | `eng_Latn` | English |
| `es` | `spa_Latn` | Spanish |
| `fr` | `fra_Latn` | French |
| `de` | `deu_Latn` | German |
| `vi` | `vie_Latn` | Vietnamese |
| `zh` | `zho_Hans` | Chinese (Simplified) |
| `ja` | `jpn_Jpan` | Japanese |

## Installation

### 1. Install Dependencies

```bash
# For GPU (CUDA 11.8)
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# For GPU (CUDA 12.1)
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# For CPU only (not recommended for production)
pip install torch==2.1.2 --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 2. Environment Variables

```bash
# Redis connection
export REDIS_URL="redis://localhost:6379"

# Worker identification
export WORKER_ID="translation-worker-1"
export CONSUMER_GROUP="translation_workers"

# Model configuration
export NLLB_MODEL="facebook/nllb-200-distilled-600M"  # Default: 600M (2.4GB)
# OR: export NLLB_MODEL="facebook/nllb-200-distilled-1.3B"  # 1.3B model (5GB, better quality)

# Health check port
export HEALTH_PORT="8082"
```

## Model Variants

Choose based on your GPU memory and quality requirements:

| Model | Size | GPU Memory | Quality | Speed |
|-------|------|------------|---------|-------|
| `facebook/nllb-200-distilled-600M` | 2.4GB | ~5GB | Good | Fast |
| `facebook/nllb-200-distilled-1.3B` | 5GB | ~8GB | Better | Medium |
| `facebook/nllb-200-1.3B` | 5GB | ~8GB | Best | Medium |
| `facebook/nllb-200-3.3B` | 13GB | ~18GB | Excellent | Slower |

**Recommendation**: Use `600M` for most cases. It provides excellent quality-to-speed ratio.

## Performance Optimizations

### GPU Optimizations (Already Implemented)

1. **Float16 Precision**: 2x faster inference with minimal quality loss
2. **Batch Processing**: Efficient token processing
3. **No Gradient Calculation**: `torch.no_grad()` for inference-only mode
4. **CUDA Cache Management**: Automatic cache clearing every 5 minutes