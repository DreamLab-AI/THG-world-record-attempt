# Product Requirements Document v3.0: Autonomous Campaign Generator Swarm

## 1. Executive Summary

**Objective:** Architect and deploy an automated, end-to-end creative workflow pipeline that transforms raw garment/mannequin imagery into a cohesive, multi-format, animated ad campaign for Topshop.

**Execution Engine:** A claude-flow v3 hierarchical agent swarm running inside the `agentic-workstation` container, orchestrating three image generation backends (local Flux2 GPU, Google Nano Banana, Google Imagen 4) and one video generation backend (Google Veo 3.1).

**Intelligence Layer:**
- **Orchestration & Reasoning:** Claude Opus 4.6 via claude-flow v3 agent swarm
- **Image Generation:** Flux2 Dev FP8 (local RTX 6000 Ada, 48GB VRAM), Nano Banana (`gemini-2.5-flash-image`), Nano Banana Pro (`gemini-3-pro-image-preview`), Imagen 4 Ultra (`imagen-4.0-ultra-generate-001`)
- **Video Generation:** Google Veo 3.1 (`veo-3.1-generate-preview`)
- **Research:** Perplexity Sonar API for typography research, trend analysis, and ComfyUI node discovery
- **Quality Evaluation:** Claude Vision for output assessment and feedback loops

**Constraint Philosophy:** "MVP Agility." Garment fidelity relies on high-accuracy approximation via Nano Banana image-to-image rather than pixel-perfect masks. Ad layout and compositing are dynamic. Topshop-specific branding hardcoded for MVP speed.

**Creative Autonomy:** The photoshoot direction (environments, lighting, poses, camera angles, mood) is at the **evolving discretion of the agents**. Agents should iterate freely to discover what is aesthetically suitable for the Topshop campaign. The Brand Guardian evaluates results against Topshop identity, but creative exploration is encouraged. No fixed shot list - agents discover the best compositions through generation and evaluation loops.

---

## 2. System Architecture

### 2.1 Infrastructure (Verified)

| Component | Location | Access | Status |
|-----------|----------|--------|--------|
| **ComfyUI** (Flux2 Dev) | Docker container `comfyui` | `http://comfyui:8188` (ComfyUI API), `http://comfyui:3000` (SaladTech API + Swagger) | Running, RTX 6000 Ada 48GB |
| **Nano Banana** | Google API | `generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent` | Verified working |
| **Nano Banana Pro** | Google API | `generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-image-preview:generateContent` | Available |
| **Imagen 4 Ultra** | Google API | `generativelanguage.googleapis.com/v1beta/models/imagen-4.0-ultra-generate-001:predict` | Available |
| **Veo 3.1** | Google API | `generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning` | Verified working |
| **Perplexity** | Perplexity API | `api.perplexity.ai/chat/completions` (model: `sonar`) | Verified working |
| **VisionFlow** | Docker container `visionflow_prod_container` | `http://visionflow_prod_container:3001` | Running, Solid pod storage |
| **Agent Workstation** | Docker container `agentic-workstation` | Local execution environment | Running |

### 2.2 File Management

```
/home/devuser/workspace/campaign/
  inputs/              # Raw garment images (uploaded by user)
  configs/             # Brand config, workflow templates, prompt libraries
    topshop.json       # Topshop brand identity config
    workflows/         # ComfyUI workflow JSON templates
    prompts/           # Prompt template library
  processing/          # Intermediate outputs during pipeline
    base-gen/          # Phase 1: Base image generations
    refined/           # Phase 2: Nano Banana refined images
    composited/        # Phase 3: Text-layered static ads
    animated/          # Phase 4: Veo animated ads
  outputs/             # Final approved campaign assets
    static/            # Approved static ads (16:9, 1:1, 9:16)
    animated/          # Approved animated ads (.mp4)
    rejected/          # Failed QA outputs with rejection reasons
  state/               # Swarm state and evaluation logs
    pipeline.json      # Current pipeline state
    evaluations/       # QA evaluation results per asset
```

### 2.3 Image Engine Routing

Each phase uses the optimal engine for its task:

| Phase | Primary Engine | Fallback | Rationale |
|-------|---------------|----------|-----------|
| Base generation (garment + scene) | **Flux2 Dev** (local) | Nano Banana | Local GPU = zero latency, free, 48GB VRAM handles 1024x1024+ |
| Style transfer (chrome mannequin) | **Nano Banana** | Nano Banana Pro | Native image-to-image with style preservation |
| Variation scaling (16-24 shots) | **Flux2 Dev** (local) | Imagen 4 Fast | Batch generation fastest on local GPU |
| Final hero shots | **Imagen 4 Ultra** | Nano Banana Pro | Highest fidelity for hero assets |
| Text compositing validation | **Nano Banana** | Claude Vision | Nano Banana can composite text natively via multimodal |
| Animation | **Veo 3.1** | Veo 3.0 Fast | Best quality video with audio |

### 2.4 Authentication

All API keys accessed via environment variables. Never hardcoded.

| Service | Env Var | Status |
|---------|---------|--------|
| Google Gemini/Nano Banana/Veo/Imagen | `GOOGLE_API_KEY` | Set |
| Perplexity | `PERPLEXITY_API_KEY` | Set |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | Set |
| ComfyUI | N/A (Docker network) | Direct access |
| SaladCloud (optional burst) | `SALAD_API_KEY` | Not configured |

---

## 3. Agent Swarm Architecture

### 3.1 Topology

**claude-flow v3 hierarchical swarm** with 6 specialized agents:

```
                    [Campaign Coordinator]
                    (sparc-coord agent)
                           |
          +--------+-------+-------+--------+
          |        |       |       |        |
     [Workflow] [Creative] [Brand] [Pipeline] [QA]
     Architect  Director  Guardian Operator  Engineer
     (coder)  (researcher) (reviewer) (coder) (tester)
```

### 3.2 Agent Roles (Mapped to claude-flow Types)

#### Campaign Coordinator (`sparc-coord`)
- Orchestrates the full pipeline lifecycle
- Manages agent task assignment via claude-flow task system
- Tracks pipeline state in `state/pipeline.json`
- Handles error escalation and retry decisions

#### Workflow Architect (`coder`)
- Constructs and iterates ComfyUI workflow JSONs for Flux2 Dev
- Builds API request payloads for Nano Banana, Imagen 4, Veo 3.1
- Manages workflow template library in `configs/workflows/`
- Handles ComfyUI node compatibility and model routing

#### Creative Director (`researcher`)
- Generates positive/negative prompts for all image engines
- Writes Veo animation scripts with motion directives
- Uses Perplexity to research Topshop typography (geometric sans-serifs matching brand identity)
- Creates shot concepts and variation strategies
- Builds prompt template library in `configs/prompts/`

#### Brand Guardian (`reviewer`)
- Evaluates all outputs against Topshop visual identity:
  - Stark high-contrast aesthetic
  - Black/white/grey palette with selective metallic accents
  - Urban, editorial tone
  - Chrome mannequin material fidelity
- Uses Claude Vision to analyze generated images
- Rates Pass/Fail with specific feedback
- Validates typography placement using negative space analysis

#### Pipeline Operator (`coder`)
- Manages API calls to all external services (Nano Banana, Veo, Imagen, Perplexity)
- Handles async job submission to ComfyUI (`POST /prompt`)
- Polls Veo long-running operations until completion
- Manages base64 encoding/decoding for API payloads
- Saves outputs to correct directories
- Handles retry logic with exponential backoff

#### QA Engineer (`tester`)
- Runs automated quality checks on all outputs:
  - Image resolution and format validation
  - Aspect ratio compliance (16:9, 1:1, 9:16)
  - File size constraints for ad platform requirements
  - Video loop seamlessness check
  - Text legibility scoring
- Generates evaluation reports in `state/evaluations/`

---

## 4. Phase-by-Phase Workflow

### Phase 1: Base Image Generation (Flux2 Dev - Local GPU)

**Objective:** Transform raw garment images into base campaign shots with chrome mannequins in urban environments.

**Engine:** Flux2 Dev FP8 via ComfyUI (`comfyui:8188`)

**Workflow:**
1. **Input:** Load garment image from `inputs/`
2. **Prompt Generation:** Creative Director generates editorial prompt via Claude:
   - "Full-length editorial campaign shot, polished chrome mannequin wearing [garment], wet UK city street reflection, brutalist concrete architecture, overcast diffused lighting, Topshop SS26 campaign aesthetic"
3. **ComfyUI Workflow:** Workflow Architect submits to ComfyUI:
   - `UNETLoader` -> `flux2_dev_fp8mixed.safetensors`
   - `CLIPLoader` -> `mistral_3_small_flux2_fp8.safetensors` (type: flux2)
   - `VAELoader` -> `flux2-vae.safetensors`
   - `KSampler` (steps: 25, cfg: 1.0, sampler: euler, scheduler: simple)
   - Optional: `Flux2TurboComfyv2.safetensors` LoRA for speed
4. **Output:** 4-6 base variations saved to `processing/base-gen/`

**Acceptance Criteria:**
- Image resolution >= 512x512
- Garment recognizable in output
- Chrome/metallic mannequin material present
- Urban environment context

### Phase 2: Style Refinement & Scaling (Nano Banana + Imagen 4)

**Objective:** Refine base images with Nano Banana image-to-image for chrome fidelity, then generate 16-24 cohesive variations.

**Engine:** Nano Banana (`gemini-2.5-flash-image`) + Imagen 4 Ultra for hero shots

**Workflow:**
1. **Image-to-Image Refinement:** Pipeline Operator sends base images to Nano Banana:
   ```json
   {
     "contents": [{
       "parts": [
         {"inlineData": {"mimeType": "image/png", "data": "<base64_image>"}},
         {"text": "Transform this into a high-fashion editorial photo. Make the mannequin surface highly polished chrome with sharp reflections. Maintain exact garment shape and details. Topshop campaign aesthetic."}
       ]
     }],
     "generationConfig": {
       "responseModalities": ["IMAGE"],
       "imageConfig": {"aspectRatio": "3:4", "imageSize": "2K"}
     }
   }
   ```
2. **Variation Scaling:** Generate 16-24 variations by:
   - Varying Nano Banana prompts (different lighting, angles, backgrounds)
   - Using Flux2 Dev with different seeds for batch diversity
   - 2-3 hero shots via Imagen 4 Ultra for highest fidelity
3. **Output:** Refined images saved to `processing/refined/`

**Acceptance Criteria:**
- Chrome mannequin material convincingly metallic
- Garment shape/detail preserved (approximation acceptable, not pixel-perfect)
- Consistent Topshop editorial tone across variations
- At least 16 passing variations from 24 generated

### Phase 3: Static Ad Compositing (Nano Banana + Claude Vision)

**Objective:** Overlay campaign typography and adapt to 16:9, 1:1, 9:16 aspect ratios.

**Topshop Typography:**
- Primary: Geometric sans-serif (closest match to Topshop brand identity)
- Creative Director uses Perplexity to identify: likely **Futura**, **Gotham**, or **Proxima Nova** equivalents
- Text content: "STYLE REIMAGINED", "NEW COLLECTION", "TOPSHOP SS26"

**Workflow:**
1. **Negative Space Analysis:** Brand Guardian sends image to Claude Vision:
   - "Analyze this campaign image. Identify the largest area of negative space suitable for text overlay. Return coordinates as percentage of image dimensions."
2. **Text Compositing (Primary Route):** Nano Banana native text overlay:
   ```json
   {
     "contents": [{
       "parts": [
         {"inlineData": {"mimeType": "image/png", "data": "<base64_refined_image>"}},
         {"text": "Add bold white geometric sans-serif text 'STYLE REIMAGINED' in the [identified negative space]. Text should be large, clean, high-contrast. Do not cover the garment. Maintain the editorial lighting."}
       ]
     }],
     "generationConfig": {"responseModalities": ["IMAGE"]}
   }
   ```
3. **Aspect Ratio Adaptation:** Generate three formats per image:
   - 16:9 (landscape, YouTube/display)
   - 1:1 (square, Instagram feed)
   - 9:16 (portrait, Stories/Reels/TikTok)
4. **Fallback Route:** If Nano Banana text quality insufficient, use ComfyUI text nodes with downloaded font files
5. **Output:** Composited ads saved to `processing/composited/`

**Acceptance Criteria:**
- Text legible at 50% scale
- Text does not overlap garment
- All three aspect ratios generated per shot
- Typography matches Topshop brand identity
- High-contrast white/black text on urban backgrounds

### Phase 4: Animation (Veo 3.1)

**Objective:** Turn static text-layered ads into 8-second seamless looping videos with subtle ambient motion.

**Engine:** Veo 3.1 (`veo-3.1-generate-preview`)

**Workflow:**
1. **Motion Script:** Creative Director generates Veo-specific prompts:
   - "Subtle ambient motion only: soft shimmer glides across metallic chrome highlights, gentle rain particles drift through background, completely static text overlay, locked camera, editorial fashion film"
2. **API Submission:** Pipeline Operator sends to Veo 3.1:
   ```json
   {
     "instances": [{
       "prompt": "<motion_script>",
       "image": {"inlineData": {"mimeType": "image/png", "data": "<base64_composited_ad>"}}
     }],
     "parameters": {
       "aspectRatio": "16:9",
       "durationSeconds": 8,
       "resolution": "1080p"
     }
   }
   ```
3. **Polling:** Pipeline Operator polls `GET /v1beta/{operation_name}` every 10s until `done: true`
4. **Download:** Retrieve video from `response.generateVideoResponse.generatedSamples[].video.uri`
5. **Output:** Animated ads saved to `processing/animated/`
6. **Repeat** for 9:16 (Stories) and 1:1 (social) formats

**Acceptance Criteria:**
- Text remains static/locked throughout video
- Chrome reflections and ambient elements animate subtly
- 8-second duration, seamless loop potential
- Resolution >= 1080p for 16:9
- File size < 50MB per video

---

## 5. Quality Assurance & Validation Loops

### 5.1 Automated QA Pipeline

Every generated asset passes through:

1. **Technical Validation** (QA Engineer):
   - Format check (PNG for images, MP4 for video)
   - Resolution >= minimum per format
   - Aspect ratio within 1% tolerance
   - File size within platform limits

2. **Brand Compliance** (Brand Guardian via Claude Vision):
   ```
   "Evaluate this Topshop campaign ad:
   1. Is the mannequin chrome/metallic? (Yes/No)
   2. Does the garment closely match the input? (approximation acceptable) (Yes/No)
   3. Is text placed in clean negative space, not overlapping the garment? (Yes/No)
   4. Does the palette conform to high-contrast black/white/grey/metallic? (Yes/No)
   5. Does this meet editorial fashion campaign standards? (Yes/No)
   Rate: PASS (all Yes) or FAIL (any No) with specific feedback."
   ```

3. **Iteration Loop:**
   - **PASS:** Asset moves to `outputs/static/` or `outputs/animated/`
   - **FAIL:** Brand Guardian flags specific error -> Workflow Architect adjusts parameters -> Pipeline Operator resubmits
   - **Max retries:** 3 per asset before escalation to human review

### 5.2 Evaluation Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Garment fidelity | >= 70% similarity | Claude Vision comparison to input |
| Chrome material quality | Pass/Fail | Claude Vision material analysis |
| Text legibility | Readable at 50% scale | Claude Vision text detection |
| Brand compliance | >= 80% of outputs pass | Brand Guardian pass rate |
| Pipeline throughput | 24 static + 8 animated per run | Asset count |
| Generation success rate | >= 70% first-pass | Pass count / total generated |

---

## 6. Initialization Sequence

The swarm executes this sequence on startup:

```
STEP 1: VALIDATE_INFRASTRUCTURE
  - Ping ComfyUI: GET http://comfyui:8188/system_stats
  - Test Nano Banana: POST generateContent with test prompt
  - Test Veo 3.1: POST predictLongRunning with test prompt
  - Test Perplexity: POST chat/completions with test query
  - Verify input images exist in inputs/

STEP 2: RESEARCH_TYPOGRAPHY (Creative Director + Perplexity)
  - Query: "Topshop brand typography font family geometric sans-serif closest open-source match"
  - Store result in configs/topshop.json

STEP 3: LOAD_BRAND_CONFIG
  - Parse configs/topshop.json for palette, typography, tone directives
  - Initialize prompt templates in configs/prompts/

STEP 4: BUILD_WORKFLOW_TEMPLATES (Workflow Architect)
  - Create Flux2 Dev base generation workflow JSON
  - Create Nano Banana refinement request templates
  - Create Veo 3.1 animation request templates
  - Store in configs/workflows/

STEP 5: BEGIN_PIPELINE
  - Start Phase 1 for all input garments
  - Pipeline Operator manages async execution
  - Campaign Coordinator tracks overall progress
```

---

## 7. API Reference (Verified Endpoints)

### Nano Banana (Image Generation)
```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"prompt"}]}],"generationConfig":{"responseModalities":["TEXT","IMAGE"],"imageConfig":{"aspectRatio":"3:4","imageSize":"2K"}}}'
```
Response: Base64 PNG in `candidates[0].content.parts[].inlineData.data`

### Veo 3.1 (Video Generation)
```bash
# Submit
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instances":[{"prompt":"text","image":{"inlineData":{"mimeType":"image/png","data":"base64"}}}],"parameters":{"aspectRatio":"16:9","durationSeconds":8}}'

# Poll (durationSeconds MUST be number, not string)
curl "https://generativelanguage.googleapis.com/v1beta/{operation_name}?key=$GOOGLE_API_KEY"
```
Response when `done: true`: Video URI in `response.generateVideoResponse.generatedSamples[].video.uri`

### Imagen 4 Ultra (Hero Shots)
```bash
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-ultra-generate-001:predict?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instances":[{"prompt":"text"}],"parameters":{"aspectRatio":"3:4","sampleCount":4}}'
```

### ComfyUI / Flux2 Dev (Local GPU)
```bash
# Submit workflow
curl -X POST http://comfyui:8188/prompt -H "Content-Type: application/json" \
  -d '{"prompt":{...workflow_json...}}'

# Poll history
curl "http://comfyui:8188/history/{prompt_id}"

# Download image
curl "http://comfyui:8188/view?filename={name}&type=output" -o output.png
```

### Perplexity (Research)
```bash
curl -X POST "https://api.perplexity.ai/chat/completions" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sonar","messages":[{"role":"user","content":"query"}]}'
```

---

## 8. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Nano Banana text rendering poor quality | Medium | Medium | Fallback to ComfyUI text nodes or post-processing |
| Veo text drift during animation | High | High | Lock camera, explicit "static text" in prompts, QA rejection loop |
| Garment fidelity loss in style transfer | Medium | High | Multiple Nano Banana iterations, lower style strength |
| API rate limits (Google) | Medium | Medium | Local Flux2 as primary, Google APIs for refinement only |
| Chrome material inconsistency | Low | Medium | Brand Guardian evaluation + specific prompt engineering |
| ComfyUI container restart loses state | Low | High | Pipeline state persisted in `state/pipeline.json` |

---

## 9. Success Criteria (MVP)

For the MVP to be considered complete:

- [ ] Pipeline processes at least 1 garment image end-to-end autonomously
- [ ] Generates >= 16 static ad variations (across 3 aspect ratios)
- [ ] Generates >= 4 animated ad videos (8s each)
- [ ] >= 70% of outputs pass Brand Guardian QA on first attempt
- [ ] All outputs saved to correct directory structure
- [ ] Pipeline state tracked and recoverable
- [ ] No hardcoded API keys in any source file
- [ ] Total pipeline time < 30 minutes per garment

---

## 10. Agent Operational Directives

### 10.1 ComfyUI Container Full Control

All agents have **complete control** of the ComfyUI Docker container. This includes:

```bash
# Execute any command inside the container
docker exec comfyui <command>

# Interactive shell access
docker exec -it comfyui bash

# Download models directly into the container
docker exec comfyui wget -O /root/ComfyUI/models/checkpoints/<model>.safetensors <url>
docker exec comfyui pip install <package>

# Install custom nodes
docker exec comfyui git clone <repo> /root/ComfyUI/custom_nodes/<node-name>

# Debug GPU issues
docker exec comfyui nvidia-smi
docker exec comfyui python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"

# Restart ComfyUI Python process (without restarting container)
docker exec comfyui pkill -f "main.py" && sleep 5  # API process will auto-restart it

# Create Python virtual environments
docker exec comfyui python3 -m venv /root/venvs/<name>

# Copy files in/out
docker cp <local_path> comfyui:<container_path>
docker cp comfyui:<container_path> <local_path>
```

### 10.2 Host Access via tmux Tab 7

**tmux tab 7 (`SSH-Shell`)** is logged into the host system that manages the Docker containers. Agents can use this for:

```bash
# Switch to tmux tab 7 for host-level operations
tmux select-window -t workspace:7

# Send commands to the host via tmux
tmux send-keys -t workspace:7 '<command>' Enter

# Use cases:
# - Docker container management (restart, rebuild, logs)
# - Volume inspection
# - Network debugging
# - Host GPU driver checks
```

### 10.3 Input Garment Image

**File:** `WLC OUTFITS 02_02_26 3.jpg`
**Location (ComfyUI):** `/root/ComfyUI/input/WLC OUTFITS 02_02_26 3.jpg`
**Location (local):** `/home/devuser/workspace/campaign/inputs/WLC OUTFITS 02_02_26 3.jpg`

**Garment Description (grounded from image):**
- **Type:** Sleeveless maxi dress, full-length, A-line silhouette
- **Bodice:** Cream/beige base with black botanical ink illustration (chrysanthemum, birds, floral line art)
- **Skirt:** Diagonal black stripes on cream base, wide flowing A-line with dramatic drape
- **Details:** Chain link straps, open back, fitted waist transitioning to full skirt
- **Panels:** 4-panel composite image labeled LOOK 6_1 (front), LOOK 6_2 (right side), LOOK 6_3 (back), LOOK 6_4 (left side)
- **Current mannequin:** White studio mannequin on grey/white background with black base

**Agent instruction:** Each panel should be treated as a separate reference angle. The front view (LOOK 6_1) is the primary hero angle. Agents should download this image from ComfyUI for additional grounding:
```bash
docker cp "comfyui:/root/ComfyUI/input/WLC OUTFITS 02_02_26 3.jpg" /tmp/garment-reference.jpg
```

### 10.4 Model Download Authority

Agents are authorized to download additional models into the ComfyUI container as needed:

```bash
# Checkpoints go to /root/ComfyUI/models/checkpoints/
# LoRAs go to /root/ComfyUI/models/loras/
# Custom nodes go to /root/ComfyUI/custom_nodes/
# Text encoders go to /root/ComfyUI/models/text_encoders/
# VAE models go to /root/ComfyUI/models/vae/
# ControlNet models go to /root/ComfyUI/models/controlnet/

# Example: download a model
docker exec comfyui wget -P /root/ComfyUI/models/checkpoints/ <model_url>

# Example: install a custom node
docker exec comfyui bash -c "cd /root/ComfyUI/custom_nodes && git clone <repo>"

# After installing nodes, restart ComfyUI to load them
docker restart comfyui
# Wait ~60-90s for GPU models to reload
```

### 10.5 Python & GPU Debugging

Agents can debug Python and GPU issues directly:

```bash
# Check GPU memory and utilization
docker exec comfyui nvidia-smi

# Check CUDA compatibility
docker exec comfyui python3 -c "import torch; print(f'CUDA: {torch.version.cuda}, PyTorch: {torch.__version__}')"

# Test model loading
docker exec comfyui python3 -c "
import safetensors
from safetensors.torch import load_file
m = load_file('/root/ComfyUI/models/diffusion_models/flux2_dev_fp8mixed.safetensors')
print(f'Keys: {len(m)}, dtype: {next(iter(m.values())).dtype}')
"

# Check ComfyUI logs
docker logs comfyui --tail 50

# Interactive Python debugging
docker exec -it comfyui python3
```

---

## 11. Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Orchestration | claude-flow v3 hierarchical swarm | Agent coordination |
| Intelligence | Claude Opus 4.6 | Reasoning, QA, prompt generation |
| Local Image Gen | Flux2 Dev FP8 + Mistral text encoder | Base generation, batch variations |
| Cloud Image Gen | Nano Banana / Nano Banana Pro | Image-to-image refinement, text compositing |
| Hero Image Gen | Imagen 4 Ultra | Maximum fidelity final assets |
| Video Gen | Veo 3.1 | 8s animated ads with ambient motion |
| Research | Perplexity Sonar | Typography research, trend analysis |
| Storage | VisionFlow + Solid pods | Asset management and distribution |
| GPU | NVIDIA RTX 6000 Ada (48GB) | Local ComfyUI inference |
| Container | agentic-workstation | Execution environment |
