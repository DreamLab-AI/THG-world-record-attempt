# Recommended ComfyUI Custom Nodes

Custom nodes to install for the fashion campaign pipeline.
Container: `comfyui:8188`

---

## Priority 1: Essential Nodes

### 1. ComfyUI-MultiGPU (Dual GPU Support)

Enables distributing UNet, CLIP, and VAE across our two RTX 6000 Ada GPUs.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/pollockjj/ComfyUI-MultiGPU && \
  echo 'MultiGPU installed'"
```

**Provides:** UNETLoaderMultiGPU, CLIPLoaderMultiGPU, VAELoaderMultiGPU, DeviceSelectorMultiGPU, Virtual VRAM (DisTorch2)

**Source:** [github.com/pollockjj/ComfyUI-MultiGPU](https://github.com/pollockjj/ComfyUI-MultiGPU)

---

### 2. Google GenMedia Custom Nodes (Veo + Imagen + Gemini)

Official Google nodes for Veo 3.1 (video), Imagen 4 (images), Gemini (text/image), and Virtual Try-On.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes && \
  pip install -r comfyui-google-genmedia-custom-nodes/requirements.txt && \
  echo 'Google GenMedia nodes installed'"
```

**Authentication setup:**
```bash
# Option A: User credentials (development)
docker exec -it comfyui bash -c "gcloud auth application-default login"

# Option B: Service account (production)
# Mount service account key into container and set:
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
```

**Provides:** Veo 3.1 T2V, Veo 3.1 I2V, Imagen3, Imagen4, Gemini 2.5 Flash Image, Gemini 3 Pro Image, Virtual Try-On, Lyria2

**Source:** [github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes](https://github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes)

---

### 3. ComfyUI-IPAdapter-Plus (Style Transfer + Reference Images)

Enables using reference images to guide style, garment details, and aesthetic consistency.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus && \
  echo 'IPAdapter Plus installed'"
```

**Required models (download into ComfyUI/models/):**
```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/models && \
  mkdir -p ipadapter clip_vision && \
  wget -q -O ipadapter/ip-adapter-plus_sd15.safetensors \
    'https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-plus_sd15.safetensors' && \
  echo 'IP-Adapter models downloaded'"
```

**Provides:** IPAdapterApply, IPAdapterEncoder, IPAdapterBatch, style transfer nodes

**Source:** [github.com/cubiq/ComfyUI_IPAdapter_plus](https://github.com/cubiq/ComfyUI_IPAdapter_plus)

---

## Priority 2: Fashion-Specific Nodes

### 4. XLabs Flux ControlNet + IP-Adapter

Native ControlNet and IP-Adapter for Flux architecture (works with Flux 2).

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/XLabs-AI/x-flux-comfyui && \
  echo 'XLabs Flux nodes installed'"
```

**Required models:**
```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/models && \
  mkdir -p xlabs/controlnets xlabs/ipadapters && \
  wget -q -O xlabs/controlnets/flux-canny-controlnet-v3.safetensors \
    'https://huggingface.co/XLabs-AI/flux-controlnet-collections/resolve/main/flux-canny-controlnet-v3.safetensors' && \
  wget -q -O xlabs/controlnets/flux-depth-controlnet-v3.safetensors \
    'https://huggingface.co/XLabs-AI/flux-controlnet-collections/resolve/main/flux-depth-controlnet-v3.safetensors' && \
  wget -q -O xlabs/ipadapters/flux-ip-adapter.safetensors \
    'https://huggingface.co/XLabs-AI/flux-ip-adapter/resolve/main/flux-ip-adapter.safetensors' && \
  echo 'XLabs models downloaded'"
```

**Provides:** Flux ControlNet Apply, Flux Load IPAdapter, Flux ControlNet Loader, style/pose transfer

**Source:** [github.com/XLabs-AI/x-flux-comfyui](https://github.com/XLabs-AI/x-flux-comfyui)

---

### 5. ComfyUI Segment Anything (SAM)

Automatic garment segmentation for masking and inpainting workflows.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/storyicon/comfyui_segment_anything && \
  pip install -r comfyui_segment_anything/requirements.txt && \
  echo 'Segment Anything installed'"
```

**Provides:** SAM segmentation, automatic mask generation, garment isolation

**Source:** [github.com/storyicon/comfyui_segment_anything](https://github.com/storyicon/comfyui_segment_anything)

---

### 6. ComfyUI Inpaint Nodes

Context-aware inpainting for garment editing, background replacement, and cleanup.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/Acly/comfyui-inpaint-nodes && \
  echo 'Inpaint nodes installed'"
```

**Provides:** FOOOCUS inpaint, context-aware fill, mask processing, inpaint model loading

**Source:** [github.com/Acly/comfyui-inpaint-nodes](https://github.com/Acly/comfyui-inpaint-nodes)

---

## Priority 3: Utility Nodes

### 7. ComfyUI-Florence2 (Auto Captioning + Detection)

Automatic image understanding, captioning, and object detection for batch processing.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/kijai/ComfyUI-Florence2 && \
  pip install -r ComfyUI-Florence2/requirements.txt && \
  echo 'Florence2 installed'"
```

**Provides:** Auto-captioning, object detection, garment recognition, dense region captioning

**Source:** [github.com/kijai/ComfyUI-Florence2](https://github.com/kijai/ComfyUI-Florence2)

---

### 8. ComfyUI Impact Pack (Workflow Utilities)

Essential utility nodes for batch processing, conditionals, and workflow control.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack && \
  pip install -r ComfyUI-Impact-Pack/requirements.txt && \
  echo 'Impact Pack installed'"
```

**Provides:** Wildcard, batch processing, face detection, conditional logic, image comparison

**Source:** [github.com/ltdrdata/ComfyUI-Impact-Pack](https://github.com/ltdrdata/ComfyUI-Impact-Pack)

---

### 9. ComfyUI-Manager (Node Manager)

Required for easy discovery, installation, and updates of other custom nodes.

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/ltdrdata/ComfyUI-Manager && \
  echo 'ComfyUI Manager installed'"
```

**Provides:** Node browser, one-click install, update management, missing node detection

**Source:** [github.com/ltdrdata/ComfyUI-Manager](https://github.com/ltdrdata/ComfyUI-Manager)

---

## Install All at Once

Run this single command to install all recommended nodes:

```bash
docker exec -it comfyui bash -c "\
  cd /opt/ComfyUI/custom_nodes && \
  git clone https://github.com/pollockjj/ComfyUI-MultiGPU && \
  git clone https://github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes && \
  pip install -r comfyui-google-genmedia-custom-nodes/requirements.txt && \
  git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus && \
  git clone https://github.com/XLabs-AI/x-flux-comfyui && \
  git clone https://github.com/storyicon/comfyui_segment_anything && \
  pip install -r comfyui_segment_anything/requirements.txt && \
  git clone https://github.com/Acly/comfyui-inpaint-nodes && \
  git clone https://github.com/kijai/ComfyUI-Florence2 && \
  pip install -r ComfyUI-Florence2/requirements.txt && \
  git clone https://github.com/ltdrdata/ComfyUI-Impact-Pack && \
  pip install -r ComfyUI-Impact-Pack/requirements.txt && \
  git clone https://github.com/ltdrdata/ComfyUI-Manager && \
  echo 'All custom nodes installed successfully'"
```

Then restart ComfyUI:
```bash
docker restart comfyui
```

---

## Verification

After restarting, verify all nodes loaded:

```bash
# Check ComfyUI logs for any import errors
docker logs comfyui 2>&1 | grep -i "error\|import\|custom_node"

# List all installed custom nodes
docker exec comfyui ls /opt/ComfyUI/custom_nodes/
```

In the ComfyUI web interface at `http://comfyui:8188`:
- Right-click canvas -> "Add Node"
- Check for "multigpu" category (MultiGPU nodes)
- Check for "Google AI" category (GenMedia nodes)
- Check for "ipadapter" category (IPAdapter Plus)

---

## Node Summary by Use Case

| Use Case | Nodes |
|----------|-------|
| Multi-GPU | ComfyUI-MultiGPU |
| Video generation | Google GenMedia (Veo 3.1) |
| Image generation (API) | Google GenMedia (Imagen4, Gemini) |
| Virtual try-on | Google GenMedia (Virtual Try-On) |
| Style transfer | ComfyUI_IPAdapter_plus |
| Pose control | x-flux-comfyui (ControlNet) |
| Edge detection | x-flux-comfyui (Canny ControlNet) |
| Depth maps | x-flux-comfyui (Depth ControlNet) |
| Garment segmentation | comfyui_segment_anything |
| Inpainting | comfyui-inpaint-nodes |
| Auto-captioning | ComfyUI-Florence2 |
| Batch processing | ComfyUI-Impact-Pack |
| Node management | ComfyUI-Manager |
