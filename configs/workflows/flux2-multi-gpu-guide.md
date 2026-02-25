# Flux 2 Multi-GPU Configuration Guide

System: 2x NVIDIA RTX 6000 Ada (48GB VRAM each)
Container: comfyui:8188

---

## Overview

With dual RTX 6000 Ada GPUs (96GB total VRAM), we can distribute the Flux 2 pipeline across both GPUs to avoid model swapping and maximize throughput.

**Optimal distribution:**
- **GPU 0 (cuda:0):** Diffusion model (UNet) -- 35.5GB for fp8mixed
- **GPU 1 (cuda:1):** Mistral text encoder (~18GB) + VAE (~336MB)

This eliminates the overhead of constantly loading/unloading models from VRAM.

Note: Multi-GPU does NOT add parallelism. Steps still execute sequentially, just on different GPUs. The speedup comes from not needing to swap models in and out of VRAM.

---

## Installation

### Step 1: Install ComfyUI-MultiGPU Custom Node

```bash
# Use the enhanced fork with Virtual VRAM support
docker exec -it comfyui bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/pollockjj/ComfyUI-MultiGPU"

# Restart ComfyUI to load the new nodes
docker restart comfyui
```

### Step 2: Verify GPUs are Visible

```bash
# Check that both GPUs are visible inside the container
docker exec comfyui nvidia-smi

# Expected output should show:
# GPU 0: NVIDIA RTX 6000 Ada Generation (48GB)
# GPU 1: NVIDIA RTX 6000 Ada Generation (48GB)
```

```bash
# Verify CUDA device count in Python
docker exec comfyui python3 -c "import torch; print(f'CUDA devices: {torch.cuda.device_count()}'); [print(f'  GPU {i}: {torch.cuda.get_device_name(i)} ({torch.cuda.get_device_properties(i).total_mem / 1e9:.1f}GB)') for i in range(torch.cuda.device_count())]"
```

---

## Workflow Configuration

### Option A: Replace Standard Loaders with MultiGPU Loaders

In your ComfyUI workflow, replace the standard loader nodes with their MultiGPU equivalents:

| Standard Node | MultiGPU Node | Device |
|--------------|---------------|--------|
| `UNETLoader` | `UNETLoaderMultiGPU` | `cuda:0` |
| `CLIPLoader` | `CLIPLoaderMultiGPU` | `cuda:1` |
| `VAELoader` | `VAELoaderMultiGPU` | `cuda:1` |

Each MultiGPU loader adds a `device` dropdown where you select the target GPU.

### Option B: Use DeviceSelectorMultiGPU Node

Add a `DeviceSelectorMultiGPU` node before each loader to explicitly set the target device:

```
DeviceSelectorMultiGPU (device: cuda:0) -> UNETLoader
DeviceSelectorMultiGPU (device: cuda:1) -> CLIPLoader
DeviceSelectorMultiGPU (device: cuda:1) -> VAELoader
```

### Option C: Virtual VRAM for Oversized Models (Advanced)

If using the full-precision Flux 2 model (64GB+), use DisTorch2 to split the UNet across both GPUs:

```
UNETLoaderMultiGPU:
  model: flux2_dev_fp8mixed.safetensors
  device: cuda:0
  virtual_vram_gb: 0  (not needed for fp8, fits in 48GB)

CLIPLoaderMultiGPU:
  model: mistral_3_small_flux2_fp8.safetensors
  device: cuda:1
  virtual_vram_gb: 0
```

For full-precision models that exceed single GPU memory:
```
UNETLoaderMultiGPU:
  model: flux2_dev_bf16.safetensors
  device: cuda:0
  virtual_vram_gb: 16  (offload 16GB to cuda:1 or CPU)
  allocation: "cuda:0,32gb;cuda:1,32gb"
```

---

## VRAM Budget

### FP8 Mixed Precision (Recommended)

| Component | Size | GPU |
|-----------|------|-----|
| flux2_dev_fp8mixed.safetensors | ~17.5GB | cuda:0 |
| mistral_3_small_flux2_fp8.safetensors | ~9GB | cuda:1 |
| flux2-vae.safetensors | ~336MB | cuda:1 |
| Working memory (latents, intermediates) | ~8-12GB | cuda:0 |
| **Total GPU 0** | **~30GB / 48GB** | |
| **Total GPU 1** | **~10GB / 48GB** | |

This leaves approximately 18GB free on GPU 0 and 38GB free on GPU 1 for:
- ControlNet models
- IP-Adapter models
- LoRA models
- Batch processing

### BF16 Full Precision (If Needed)

| Component | Size | GPU |
|-----------|------|-----|
| flux2_dev_bf16.safetensors | ~35.5GB | cuda:0 |
| mistral_3_small_flux2_bf16.safetensors | ~18GB | cuda:1 |
| flux2-vae.safetensors | ~336MB | cuda:1 |
| Working memory | ~8-12GB | cuda:0 |
| **Total GPU 0** | **~47GB / 48GB** | |
| **Total GPU 1** | **~18.5GB / 48GB** | |

Tight on GPU 0 but feasible.

---

## ComfyUI Launch Flags

For multi-GPU, ComfyUI should be launched with specific flags:

```bash
# In docker-compose or container startup:
python3 main.py \
  --listen 0.0.0.0 \
  --port 8188 \
  --cuda-device 0 \
  --disable-smart-memory
```

- `--cuda-device 0` sets the primary GPU (MultiGPU nodes handle the rest)
- `--disable-smart-memory` prevents ComfyUI from auto-managing VRAM (let MultiGPU handle it)

---

## Troubleshooting

### Issue: Model loads on wrong GPU
Make sure you are using the MultiGPU variant of the loader node, not the standard one. Standard nodes always use the primary GPU.

### Issue: Out of memory on one GPU
Check with `nvidia-smi` which GPU is full. Consider:
- Moving VAE to the same GPU as CLIP (they are small)
- Using Virtual VRAM to spill overflow to CPU RAM
- Reducing batch size

### Issue: Slow generation despite two GPUs
Multi-GPU does NOT parallelize the sampling steps. It only prevents model swapping. Generation speed is roughly the same as single-GPU but there is no swapping delay between model components.

### Issue: CUDA error about device mismatch
Ensure all tensors flowing between nodes are on the same device at point of use. The MultiGPU nodes handle this automatically for standard workflows.

---

## Performance Expectations

| Scenario | Single GPU | Dual GPU |
|----------|-----------|----------|
| First generation (cold start) | ~25s | ~15s |
| Subsequent generations | ~12s | ~12s |
| Switching between txt2img and img2img | ~8s swap + 12s gen | ~12s (no swap) |
| Batch of 4 images | ~48s | ~48s |

The main benefit of multi-GPU is **eliminating swap time** when switching between workflows that use different model components, and **enabling full-precision models** that would not fit on a single 48GB GPU.

---

## References

- [ComfyUI-MultiGPU (pollockjj fork)](https://github.com/pollockjj/ComfyUI-MultiGPU)
- [ComfyUI-MultiGPU (neuratech-ai original)](https://github.com/neuratech-ai/ComfyUI-MultiGPU)
- [ComfyUI Multi-GPU Discussion](https://github.com/comfyanonymous/ComfyUI/discussions/4139)
- [RunComfy MultiGPU Guide](https://www.runcomfy.com/comfyui-nodes/ComfyUI-MultiGPU)
