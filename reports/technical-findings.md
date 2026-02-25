# Technical Findings Report

**Date:** 2026-02-25
**System:** Dual RTX 6000 Ada + ComfyUI + Google Generative AI APIs

---

## 1. Flux 2 Dev on ComfyUI

### Working Configuration

```
Model: flux2_dev_fp8mixed.safetensors (~17.5GB)
CLIP: mistral_3_small_flux2_fp8.safetensors (~9GB)
VAE: flux2-vae.safetensors (~336MB)
Sampler: euler, 20 steps, CFG 1.0, Simple scheduler
```

### Key Findings

- **CLIPLoader type must be `flux2`** - Using `stable_diffusion` or `sd3` type fails silently
- **clip_l.safetensors is corrupted** on this system (safetensors header error). Use the Mistral CLIP instead
- **CFG 1.0** is correct for Flux 2. Higher CFG values cause oversaturation
- **EmptySD3LatentImage** works for Flux 2 latent space initialization
- Research suggests `SamplerCustomAdvanced` + `FluxGuidance` (guidance=4.0) + `Flux2Scheduler` may produce better results than `KSampler`

### Optimal Workflow (from research)

The official Flux 2 Dev workflow template uses:
- `SamplerCustomAdvanced` instead of `KSampler`
- `Flux2Scheduler` (takes width/height as inputs)
- `FluxGuidance` node (replaces CFG parameter, set to 4.0)
- `ReferenceLatent` node for native image-to-image capability

---

## 2. Multi-GPU Configuration

### Hardware

```
GPU 0: NVIDIA RTX 6000 Ada Generation - 50.9GB total
GPU 1: NVIDIA RTX 6000 Ada Generation - 50.9GB total
```

### Installation

```bash
# ComfyUI-MultiGPU already installed at:
/root/ComfyUI/custom_nodes/ComfyUI-MultiGPU/

# Fork: pollockjj/ComfyUI-MultiGPU (enhanced with Virtual VRAM support)
```

### MultiGPU Node Mapping

| Standard Node | MultiGPU Node | Device |
|--------------|---------------|--------|
| `UNETLoader` | `UNETLoaderMultiGPU` | `cuda:0` |
| `CLIPLoader` | `CLIPLoaderMultiGPU` | `cuda:1` |
| `VAELoader` | `VAELoaderMultiGPU` | `cuda:1` |

### Verified VRAM Distribution

| GPU | Component | VRAM Used | VRAM Free |
|-----|-----------|-----------|-----------|
| cuda:0 | UNet + working memory | 38.2GB | 12.6GB |
| cuda:1 | CLIP + VAE | 19.3GB | 31.6GB |

### Performance Impact

- Eliminates model swap time when switching between text encoding and diffusion
- Cold start: ~15s (vs ~25s single GPU)
- Leaves ~12GB free on GPU 0 and ~31GB on GPU 1 for ControlNet, IP-Adapter, LoRA
- Multi-GPU does NOT parallelize sampling steps - speedup comes from avoiding model swaps

---

## 3. Nano Banana (Gemini 2.5 Flash Image)

### API Configuration

```
Endpoint: https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent
Auth: x-goog-api-key header OR ?key= query parameter
Response: Base64-encoded image in inlineData.data
```

### Image-to-Image Pattern

```json
{
  "contents": [{
    "parts": [
      {"inlineData": {"mimeType": "image/jpeg", "data": "<base64>"}},
      {"text": "Editorial refinement prompt..."}
    ]
  }],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"]
  }
}
```

### Findings

- **Text rendering unreliable** - "STYLE REIMAGINED" consistently misspelled across multiple attempts
- **Garment fidelity excellent** - Preserves botanical ink patterns, diagonal stripes, chain straps
- **Style transfer strong** - Effectively transforms flat product shots into editorial scenes
- **Cost:** ~$0.039/image (standard), ~$0.06-0.10 (Pro)
- **Nano Banana Pro** (`gemini-3-pro-image-preview`) is recommended for text-heavy outputs

---

## 4. Veo 3.1

### API Configuration

```
Endpoint: https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning
Auth: ?key= query parameter
Response: Asynchronous operation with polling
```

### T2V (Text-to-Video) - Working

```json
{
  "instances": [{"prompt": "Fashion video prompt..."}],
  "parameters": {
    "aspectRatio": "16:9",
    "durationSeconds": 8
  }
}
```

### I2V (Image-to-Video) - NOT Working via Gemini API

```
- inlineData: "inlineData isn't supported by this model"
- fileUri: "fileUri isn't supported by this model"
- Requires Vertex AI endpoint with Bearer token authentication
```

### Video Download Pattern

```python
# Response contains video.uri, NOT video.encodedVideo
video_uri = response["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
# URI format: https://generativelanguage.googleapis.com/v1beta/files/{id}:download?alt=media
# Must use -L flag for redirects
# Append &key=API_KEY to the URI
```

### Gotchas

1. **`durationSeconds` must be a number**, not a string (returns INVALID_ARGUMENT)
2. **`generateVideo` endpoint returns 404** - use `predictLongRunning` instead
3. **Video URI requires redirect following** (`-L` flag in curl)
4. **Operations take 1-3 minutes** to complete. Poll with 20s intervals
5. **Aspect ratio**: 16:9 produces ~6MB videos, 9:16 produces ~3-4MB

### Prompting Best Practices

- Include camera movement, lens focal length, subject description
- Use force-based motion verbs: push, pull, sway, ripple, drift, glide
- Explicitly state "No subtitles, no text overlays, no watermarks"
- For text-locked video: pre-render text in source image, use motion-restricted prompt

---

## 5. Programmatic Text Compositing

### Problem

AI-generated text (via both Flux 2 and Nano Banana) consistently misspells brand text. The word "REIMAGINED" was rendered as "REIMANGEED", "REIM ANGNED", and similar variants across all attempts.

### Solution

Use programmatic rendering (Pillow/ImageMagick) to overlay text on AI-generated images:

```bash
# FFmpeg approach for video text overlay
ffmpeg -i input.mp4 \
  -vf "drawtext=text='BRAND NAME':fontfile=font.ttf:fontsize=72:fontcolor=white:x=(w-text_w)/2:y=h*0.9" \
  -codec:a copy output.mp4
```

### Recommendation

Always use programmatic text rendering for brand names and campaign headlines. Reserve AI text generation only for concepts/drafts where exact spelling is not critical.

---

## 6. ComfyUI Container Access

### Network Configuration

```
Container name: comfyui
Internal URL: http://comfyui:8188
API endpoint: http://comfyui:8188/prompt
History endpoint: http://comfyui:8188/history/{prompt_id}
Object info: http://comfyui:8188/object_info
```

### Important Notes

- **Do NOT use localhost:8188** from the agentic-workstation container - use `comfyui:8188`
- Container runs on `agentbox-net` Docker network
- Input path: `/root/ComfyUI/input/`
- Output path: `/root/ComfyUI/output/`
- Custom nodes: `/root/ComfyUI/custom_nodes/`

---

## 7. Environment Variables

```
GOOGLE_API_KEY      - Google Gemini/Veo API access
GOOGLE_GEMINI_API_KEY - Alternative Gemini key
PERPLEXITY_API_KEY  - Perplexity Sonar search API
ANTHROPIC_API_KEY   - Claude API access
```

---

## 8. Recommended Custom Nodes (from research)

| Priority | Node | Purpose |
|----------|------|---------|
| 1 | ComfyUI-MultiGPU | Multi-GPU model distribution (INSTALLED) |
| 1 | Google GenMedia nodes | Veo/Imagen 4 integration in ComfyUI |
| 1 | IPAdapter Plus | Image reference for garment fidelity |
| 2 | XLabs Flux ControlNet | Pose/depth control for fashion shots |
| 2 | Segment Anything | Garment isolation |
| 3 | Florence2 | Caption generation for prompt engineering |
| 3 | ComfyUI-Manager | Node management |
