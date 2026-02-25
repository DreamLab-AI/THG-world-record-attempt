# Workflow Research Findings

Date: 2026-02-25
Research Method: WebSearch + WebFetch across official docs, GitHub repos, and community resources

---

## 1. Flux 2 Dev ComfyUI Workflows

### Official Workflow Architecture (from Comfy-Org)

The official Flux 2 Dev workflow uses a **subgraph-based architecture** called "Image Edit (Flux.2 Dev)" that encapsulates the full pipeline into a reusable component.

**Core Node Chain:**
```
UNETLoader -> [Optional: LoraLoaderModelOnly -> ComfySwitchNode] -> BasicGuider
CLIPLoader -> CLIPTextEncode -> FluxGuidance -> ReferenceLatent -> BasicGuider
VAELoader -> VAEEncode (reference image) -> ReferenceLatent
             VAELoader -> VAEDecode (output)
RandomNoise -> SamplerCustomAdvanced
KSamplerSelect -> SamplerCustomAdvanced
Flux2Scheduler -> SamplerCustomAdvanced
EmptyFlux2LatentImage -> SamplerCustomAdvanced
```

**Key Parameters (from official workflow JSON):**
- **Sampler:** `euler` (via KSamplerSelect)
- **Steps:** 20 (standard) or 8 (with Turbo LoRA)
- **FluxGuidance:** 4.0
- **Scheduler:** `Flux2Scheduler` (custom node, NOT standard scheduler)
- **Dimensions:** 1248x832 (default, ~1 megapixel)
- **CFG:** Not used directly -- BasicGuider replaces KSampler, so CFG is controlled via FluxGuidance value
- **Model files:**
  - UNet: `flux2_dev_fp8mixed.safetensors` (diffusion_models/)
  - CLIP: `mistral_3_small_flux2_bf16.safetensors` (text_encoders/) -- NOTE: fp8 variant also available
  - VAE: `flux2-vae.safetensors` (vae/)
  - LoRA (optional): `Flux_2-Turbo-LoRA_comfyui.safetensors` (loras/)

**Important Notes:**
- Flux 2 uses `SamplerCustomAdvanced` NOT the standard `KSampler` node
- The `Flux2Scheduler` node is specific to Flux 2 and takes steps + width + height as inputs
- `ReferenceLatent` node connects a reference image's latent to the conditioning pipeline
- The workflow supports toggling between standard (20 steps) and turbo (8 steps with LoRA) modes
- Flux 2 targets 1-4 megapixels; start smaller for look development

**Sources:**
- [Official Flux 2 Examples](https://comfyanonymous.github.io/ComfyUI_examples/flux2/)
- [ComfyUI Flux 2 Dev Tutorial](https://docs.comfy.org/tutorials/flux/flux-2-dev)
- [Flux 2 Dev in ComfyUI - RunComfy](https://www.runcomfy.com/comfyui-workflows/flux-2-dev-in-comfyui-high-fidelity-visual-generation)
- [Flux 2 Setup Guide](https://sonusahani.com/blogs/how-to-install-flux-2-in-comfyui)
- [Official Workflow JSON](https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/image_flux2.json)

---

## 2. Flux 2 Multi-GPU ComfyUI

### ComfyUI-MultiGPU Extension

Two main implementations exist:

**1. neuratech-ai/ComfyUI-MultiGPU** (original)
- Adds `device` parameter to all loader nodes
- Provides: CheckpointLoaderMultiGPU, CLIPLoaderMultiGPU, ControlNetLoaderMultiGPU, DualCLIPLoaderMultiGPU, UNETLoaderMultiGPU, VAELoaderMultiGPU
- Does NOT add parallelism -- steps still execute sequentially on different GPUs
- Performance gains come from reduced model loading/unloading overhead
- Experimental / not well tested

**2. pollockjj/ComfyUI-MultiGPU** (enhanced fork)
- Adds "Virtual VRAM" (DisTorch2) for UNet and CLIP loaders
- Supports WanVideoWrapper nodes
- Expert allocation modes: byte-level, ratio-based, fraction-based splitting
- Example: `cuda:0,2.5gb;cpu,*` or `cuda:0,25%;cpu,75%`

**Optimal Configuration for Dual RTX 6000 Ada (48GB each):**
```
GPU 0 (cuda:0): UNet / Diffusion Model
GPU 1 (cuda:1): CLIP Text Encoder + VAE
```

This prevents constant VRAM transfers between devices. The Mistral text encoder is ~18GB and the diffusion model is 35-64GB depending on precision.

**Installation:**
```bash
cd ComfyUI/custom_nodes/
git clone https://github.com/neuratech-ai/ComfyUI-MultiGPU
# OR for enhanced version:
git clone https://github.com/pollockjj/ComfyUI-MultiGPU
```

**Sources:**
- [neuratech-ai/ComfyUI-MultiGPU](https://github.com/neuratech-ai/ComfyUI-MultiGPU)
- [pollockjj/ComfyUI-MultiGPU](https://github.com/pollockjj/ComfyUI-MultiGPU)
- [RunComfy MultiGPU Guide](https://www.runcomfy.com/comfyui-nodes/ComfyUI-MultiGPU)
- [ComfyUI Multi-GPU Discussion](https://github.com/comfyanonymous/ComfyUI/discussions/4139)

---

## 3. Flux 2 Image-to-Image / ControlNet

### Native Flux 2 Image Editing

The official Flux 2 workflow already includes image-to-image via the `ReferenceLatent` node:
1. Load reference image with `LoadImage`
2. Scale to target pixel count with `ImageScaleToTotalPixels`
3. Encode to latent with `VAEEncode`
4. Feed into `ReferenceLatent` which conditions the generation

### ControlNet for Flux

Available ControlNet models:
- **InstantX ControlNet Union**: Canny, Depth, Tile, Blur, Pose, Gray, Low quality (bundled)
- **XLabs-AI flux-ip-adapter**: Dedicated IP-Adapter for Flux
- **InstantX independent Canny and IP-Adapter models**

### IP-Adapter for Fashion/Garment Work

- Use "Flux Load IPAdapter" node with CLIP vision model
- **ControlNet Strength:** Keep above 0.7 for strong subject control
- **IP-Adapter Strength:** Keep below 0.5 -- higher values degrade image quality
- IP-Adapter was trained at 512x512 (50k steps) and 1024x1024 (25k steps)

### Garment Preservation Techniques

- Combine ControlNet (structure) + IP-Adapter (style transfer)
- Use image-to-image with moderate denoise (0.4-0.6) to preserve garment details
- Virtual Try-On workflows available (Qwen model, SalvTON, CozyMantis)
- FLUX.1 ControlNet Pose provides precise body keypoints for fashion poses

**Sources:**
- [Flux IP-Adapter - XLabs-AI](https://huggingface.co/XLabs-AI/flux-ip-adapter)
- [ControlNet + IPAdapter Style Transfer](https://comfyui.org/en/image-style-transfer-controlnet-ipadapter-workflow)
- [Flux ComfyUI I2I Tutorial](https://comfyui-wiki.com/en/tutorial/advanced/image/flux/flux-1-dev-i2i)
- [XLabs Flux ComfyUI Nodes](https://github.com/XLabs-AI/x-flux-comfyui)
- [Fashion Photography with FLUX.1](https://comfyui.org/en/photorealistic-fashion-photography-with-flux1-and-controlnet)

---

## 4. Nano Banana (Gemini 2.5 Flash Image) API

### Model Details

- **Model name:** `gemini-2.5-flash-image`
- **Codename:** Nano Banana
- **Released:** August 2025, GA October 2025
- **Architecture:** Multimodal Diffusion Transformer (450M - 8B parameters)
- **Pricing:** $30/M output tokens, each image = 1,290 tokens (~$0.039/image)
- **Ranked #1** on LMArena Image Edit and Text-to-Image leaderboards (August 2025)

### API Configuration

**Endpoint:** `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent`

**Required header:** `x-goog-api-key: $GOOGLE_API_KEY`

**Response modalities:** `["TEXT", "IMAGE"]`

**Supported aspect ratios:** 1:1, 2:3, 3:2, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9

### Text-to-Image (curl)
```bash
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent" \
  -H "x-goog-api-key: $GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "Your prompt"}]}],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"]
    }
  }'
```

### Text-to-Image (Python)
```python
from google import genai
from google.genai import types

client = genai.Client()
response = client.models.generate_content(
    model="gemini-2.5-flash-image",
    contents="Your prompt here",
    config=types.GenerateContentConfig(
        response_modalities=["TEXT", "IMAGE"]
    )
)
```

### Image-to-Image Capabilities
- Supports editing with combined text + image inputs
- Add, remove, modify elements, change style, adjust color grading
- Multi-turn conversations for iterative refinement
- Up to 14 reference images supported
- Google Search grounding integration
- SynthID watermark on all outputs

**Sources:**
- [Gemini Image Generation API Docs](https://ai.google.dev/gemini-api/docs/image-generation)
- [Gemini 2.5 Flash Image Announcement](https://developers.googleblog.com/introducing-gemini-2-5-flash-image/)
- [Gemini 2.5 Flash Image Production Release](https://developers.googleblog.com/en/gemini-2-5-flash-image-now-ready-for-production-with-new-aspect-ratios/)
- [Gemini Models](https://ai.google.dev/gemini-api/docs/models)

---

## 5. Nano Banana Pro vs Nano Banana

### Key Differences

| Feature | Nano Banana | Nano Banana Pro |
|---------|------------|-----------------|
| **Model** | `gemini-2.5-flash-image` | `gemini-3-pro-image-preview` |
| **Focus** | Speed, efficiency, high-volume | Professional asset production |
| **Text Rendering** | Basic, improving | Sharp, legible -- ideal for posters, packaging |
| **Reasoning** | Standard | Advanced "Thinking" mode |
| **Resolution** | 1K | 1K, 2K, 4K |
| **Best For** | Fast iteration, drafts | Final production assets |
| **Pricing** | $0.039/image | Higher (Pro tier) |

### For Fashion Photography

- **Nano Banana:** Good for rapid iteration, color testing, pattern application to surfaces
- **Nano Banana Pro:** Better for final production assets, studio-quality visuals from single prompt, precise text overlay for advertising

### Recommendation for Our Pipeline

- Use **Nano Banana** for rapid concept iteration and A/B testing
- Use **Nano Banana Pro** for final campaign assets requiring text overlays
- Both support image-to-image editing for garment modifications

**Sources:**
- [Nano Banana Pro API](https://kie.ai/nano-banana)
- [Gemini 2.5 Flash Image - DeepMind](https://deepmind.google/models/gemini-image/flash/)
- [Nano Banana Feature Comparison](https://www.cometapi.com/gemini-2-5-flash-imagenano-banana-feature-benchmark-and-usage/)

---

## 6. Google Veo 3.1 ComfyUI Integration

### Official Google Custom Nodes

**Repository:** `GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes`

**Available Nodes:**
- Gemini (multimodal)
- Gemini 2.5 Flash Image
- Gemini 3 Pro Image
- Imagen3 (text-to-image)
- Imagen4 (text-to-image)
- Lyria2
- **Veo2 & Veo3.1** (video generation)
- Virtual-try-on

**Installation:**
```bash
cd ComfyUI/custom_nodes
git clone https://github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes
pip install -r comfyui-google-genmedia-custom-nodes/requirements.txt
```

**Authentication:** GCP workload identity or `gcloud auth application-default login`

### Community Nodes

- **Comfly_Googel_Veo3**: Text-to-video with Veo 3 model
- **Siray ComfyUI nodes**: Veo 3.1 I2V and T2V nodes
- **ComfyUI-Veo3-Experimental**: Experimental integration

### Veo 3.1 Capabilities

- 720p or 1080p resolution
- 24 fps
- 4, 6, or 8 second clips (up to 2 minutes with extension)
- Text-to-video (T2V) and Image-to-video (I2V) modes
- Synchronized audio generation
- "Extend" feature for adding duration while maintaining consistency

**Sources:**
- [Google GenMedia Custom Nodes](https://github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes)
- [Veo 3.1 in ComfyUI Blog Post](https://blog.comfy.org/p/veo-31-is-now-available-in-comfyui)
- [ComfyUI Veo 3 Node](https://comfy.icu/node/Veo3VideoGenerationNode)
- [Siray Veo 3.1 I2V](https://www.runcomfy.com/comfyui-nodes/siray-comfyui/siray-google-veo-3-1-i2v)

---

## 7. Veo 3.1 Best Practices for Fashion Advertising

### Prompting Framework (7-Layer Master Template)

```
[Camera move + lens]: [Subject] [Action & physics], in [Setting + atmosphere],
lit by [Light source]. Style: [Texture/finish]. Audio: [Dialogue/SFX/ambience].
```

### Camera and Motion Control

- **Lens choices:** 16mm (expands space), 35mm (natural), 85mm (compress backgrounds, intimacy)
- **Motion verbs:** push, pull, strike, slam, sway, ripple, spiral
- **Camera movements:** dolly-in, lateral shifts, forward push -- specify explicitly
- **Subject motion:** "leans slightly forward as he speaks, lifting one hand..."

### Fashion-Specific Prompting

**Example:**
```
"Runway medium-wide of a model in a flowing linen suit, cream on cream.
Slow tracking left. High-key studio light, soft shadows.
Fabric rustle and faint catwalk crowd murmur.
She says, 'Effortless for spring.' No subtitles."
```

**Material cues:** Include fabric type for light-reflection stability (e.g., "charcoal cotton hoodie")
**Lighting:** Name specific light sources rather than brightness levels

### Text Overlay Control

- Add `"No subtitles."` to suppress unwanted text
- Use `visual_rules` to explicitly exclude text overlays
- For text-locked scenes: render text in the source image, then use I2V with minimal motion

### Duration and Resolution

- Max 8 seconds per clip
- Use "Veo 3.1 Extend" for longer clips with consistency
- **9:16** for Instagram Reels, YouTube Shorts, TikTok
- **16:9** for YouTube, landing pages, cinematic

### Timestamp Prompting

Control progression within a single shot:
```
"0-3 seconds: Open on dark setup...
 3-6 seconds: Introduce side-light sweep...
 6-8 seconds: Full focus close-up"
```

### Clip Chaining

Reuse final frame of Clip 1 as start frame for Clip 2 to maintain consistency across transitions.

**Sources:**
- [Ultimate Prompting Guide for Veo 3.1 - Google Cloud](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1)
- [Veo 3.1 Prompt Guide - Invideo](https://invideo.io/blog/google-veo-prompt-guide/)
- [Best Veo 3 Prompts 2025](https://skywork.ai/blog/best-veo-3-prompts-2025/)
- [Veo 3 Prompts for Marketers](https://www.godofprompt.ai/blog/veo-3-prompts-for-marketer)
- [Google Veo 3 for Ads](https://www.valuex2.com/how-google-veo-3-will-make-your-ads-go-viral/)

---

## 8. ComfyUI Fashion Photography Workflows

### Key Workflow Types

1. **Virtual Try-On**: Qwen model + IPAdapter + ControlNet + Inpainting
   - Generates realistic visuals of person wearing selected garments
   - Automatic garment segmentation
   - Context-aware inpainting with Flux Fill models

2. **Model Swap**: Uses deepfashion_2 model for swapping models while preserving outfit

3. **Clothing Replacement**: CozyMantis SalvTON workflow
   - Reference image of clothing + target person
   - Preserves garment details while adapting to pose

4. **Fashion Photography with FLUX.1 + ControlNet Pose**
   - Precise body keypoints
   - High-resolution outputs
   - Pose control for editorial poses

### Recommended Custom Nodes for Fashion

- **ComfyUI-IPAdapter-Plus**: Style transfer, outfit changes
- **ComfyUI-ControlNet**: Pose, depth, canny edge control
- **ComfyUI-Inpaint**: Context-aware garment editing
- **ComfyUI-Florence2**: Automatic segmentation
- **ComfyUI-MultiGPU**: Dual GPU support
- **comfyui-google-genmedia-custom-nodes**: Veo/Imagen integration

### Text Overlay Approaches

- Use external compositing (ImageMagick, Pillow) after generation
- Flux 2's native text rendering (via prompt) for embroidered/printed text
- Nano Banana Pro for integrated text in images
- Post-processing overlay in the pipeline

**Sources:**
- [Virtual Try-On Workflow - RunComfy](https://www.runcomfy.com/comfyui-workflows/comfyui-virtual-try-on-workflow-qwen-model-clothing-fitting)
- [Fashion Photography with FLUX.1](https://comfyui.org/en/photorealistic-fashion-photography-with-flux1-and-controlnet)
- [GPT-Image-1 Fashion Workflow](https://comfyui.org/en/unleash-your-fashion-sense-with-gpt-image-1)
- [Clothes Swap SalvTON](https://github.com/cozymantis/clothes-swap-salvton-comfyui-workflow)
- [AI Clothing Replacement](https://comfyui.org/en/ai-generated-clothing-replacement)
