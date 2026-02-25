# URGENT AGENT NOTICE - Multi-GPU Required

## Problem
The Flux2 CLIP using Mistral text encoder is very memory intensive. GPU 0 is nearly full (5.8GB of 49GB free). GPU 1 is completely idle (48.4GB free).

## Available GPUs
```
GPU 0: NVIDIA RTX 6000 Ada Generation - 49140 MiB total, ~5853 MiB free (loaded with models)
GPU 1: NVIDIA RTX 6000 Ada Generation - 49140 MiB total, ~48470 MiB free (IDLE)
```

## Required Action
ComfyUI must be configured to use BOTH GPUs. Research, install, and troubleshoot multi-GPU support.

### Approaches to try (in order):

1. **ComfyUI --multi-gpu flag**: Check if ComfyUI supports `--multi-gpu` or `--cuda-device` flags
   ```bash
   docker exec comfyui python3 /root/ComfyUI/main.py --help | grep -i gpu
   ```

2. **CUDA_VISIBLE_DEVICES**: Ensure both GPUs are visible
   ```bash
   docker exec comfyui python3 -c "import torch; print(torch.cuda.device_count())"
   ```

3. **ComfyUI model offloading**: Use `--lowvram` or `--gpu-only` flags to control VRAM usage, or use the `--force-channels-last` flag

4. **Custom node for multi-GPU**: Install a multi-GPU custom node:
   ```bash
   docker exec comfyui bash -c "cd /root/ComfyUI/custom_nodes && git clone https://github.com/city96/ComfyUI_ExtraModels.git"
   ```

5. **Manual model placement**: In the workflow, split CLIP/text encoder to GPU 1 and UNET to GPU 0:
   - Set `CUDA_DEVICE_ORDER=PCI_BUS_ID`
   - Use ComfyUI's model management to place different models on different devices

6. **Restart ComfyUI with multi-GPU args**:
   ```bash
   # Kill existing and restart with both GPUs
   docker exec comfyui pkill -f "main.py"
   # Wait for comfyui-api to restart it, or manually:
   docker exec -d comfyui /app/venv/bin/python /root/ComfyUI/main.py --listen --port 8188 --multi-gpu
   ```

## After fixing, verify:
```bash
docker exec comfyui python3 -c "
import torch
for i in range(torch.cuda.device_count()):
    print(f'GPU {i}: {torch.cuda.get_device_name(i)} - {torch.cuda.mem_get_info(i)[1]/1e9:.1f}GB total, {torch.cuda.mem_get_info(i)[0]/1e9:.1f}GB free')
"
```
