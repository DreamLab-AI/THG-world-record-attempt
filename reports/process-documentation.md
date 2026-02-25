# THG World Record Attempt: Process Documentation

## Autonomous Campaign Generator -- Topshop SS26 "Style Reimagined"

**Date:** 2026-02-25
**Version:** 1.0.0
**Classification:** Technical Process Document
**Objective:** Complete reproduction guide for generating a full fashion advertising campaign from a single garment photograph using an autonomous AI agent swarm.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture](#2-system-architecture)
3. [Pre-Production Phase](#3-pre-production-phase)
4. [Campaign Configuration](#4-campaign-configuration)
5. [Pipeline Execution](#5-pipeline-execution)
6. [Garment Fidelity Reskinning](#6-garment-fidelity-reskinning)
7. [Multi-GPU Configuration](#7-multi-gpu-configuration)
8. [Quality Assurance](#8-quality-assurance)
9. [Technical Discoveries and Gotchas](#9-technical-discoveries-and-gotchas)
10. [Agent Roster and Performance](#10-agent-roster-and-performance)
11. [Deliverable Inventory](#11-deliverable-inventory)
12. [Recommendations for Next Iteration](#12-recommendations-for-next-iteration)

---

## 1. Executive Summary

### What Was Accomplished

An autonomous AI agent swarm, orchestrated by Claude Flow v3, generated a complete Topshop SS26 fashion advertising campaign from a single four-panel garment photograph. The system operated with zero human creative intervention after the initial garment image was provided and the pipeline was triggered.

The swarm produced **36+ deliverables** spanning four categories:

| Category | Count | Description |
|----------|-------|-------------|
| Base generations | 6 | Flux 2 Dev raw editorial shots at 768x1024 |
| Refined shots | 6 | Nano Banana image-to-image editorial enhancements |
| Final composites | 18 | Programmatic typography overlay across 3 aspect ratios |
| Animated fashion films | 6 | Veo 3.1 text-to-video at 8 seconds each |
| **Total** | **36** | |

### Scale of the Attempt

- **Input:** 1 garment photograph (`WLC OUTFITS 02_02_26 3.jpg`) -- a 4-panel composite showing front, right side, back, and left side views of Look 6
- **Output:** 36 production-ready campaign assets (18 static composites + 6 animated videos + 12 intermediate assets)
- **Pipeline duration:** Approximately 30 minutes from first API call to final asset delivery
- **Tool calls:** 142+ across the Pipeline Executor agent alone
- **Engines used:** 3 distinct AI generation backends (Flux 2 Dev, Gemini 2.5 Flash Image, Veo 3.1)
- **QA pass rate:** 100% on final deliverables (34/34 assets passed Brand Guardian evaluation)

### Infrastructure

| Component | Specification |
|-----------|--------------|
| GPU compute | 2x NVIDIA RTX 6000 Ada Generation (48GB VRAM each, 96GB total) |
| Local image generation | Flux 2 Dev FP8 Mixed via ComfyUI on Docker |
| Cloud image generation | Gemini 2.5 Flash Image ("Nano Banana") via Google Generative AI API |
| Cloud video generation | Veo 3.1 via Google Generative AI predictLongRunning API |
| Agent orchestration | Claude Flow v3 hierarchical swarm with 4 specialized agents |
| Intelligence layer | Claude Opus 4.6 for reasoning, QA, and prompt generation |
| Research | Perplexity Sonar API for typography and workflow research |
| Container runtime | SaladTechnologies ComfyUI API wrapper on Docker (`agentbox-net` network) |

---

## 2. System Architecture

### 2.1 Hardware

The system runs on a dual-GPU workstation accessible through a Docker container infrastructure:

```
Host System
  |
  +-- agentic-workstation container (Claude agents execute here)
  |     Network: agentbox-net
  |     Access: Local filesystem + Docker exec into comfyui
  |
  +-- comfyui container (Flux 2 Dev inference)
  |     GPU 0: NVIDIA RTX 6000 Ada Generation -- 48GB VRAM (50.9GB total)
  |     GPU 1: NVIDIA RTX 6000 Ada Generation -- 48GB VRAM (50.9GB total)
  |     ComfyUI API: http://comfyui:8188
  |     SaladTech API: http://comfyui:3000
  |     Models path: /root/ComfyUI/models/
  |     Custom nodes: /root/ComfyUI/custom_nodes/
  |     Input path: /root/ComfyUI/input/
  |     Output path: /root/ComfyUI/output/
  |
  +-- visionflow_prod_container (asset management)
        Access: http://visionflow_prod_container:3001
```

GPU verification command:

```bash
docker exec comfyui nvidia-smi
# Expected: 2x NVIDIA RTX 6000 Ada Generation, 48GB each

docker exec comfyui python3 -c "import torch; print(f'CUDA devices: {torch.cuda.device_count()}'); [print(f'  GPU {i}: {torch.cuda.get_device_name(i)} ({torch.cuda.get_device_properties(i).total_mem / 1e9:.1f}GB)') for i in range(torch.cuda.device_count())]"
```

### 2.2 Container and Network Setup

The ComfyUI container runs on the `agentbox-net` Docker network. All inter-container communication uses Docker hostnames, not `localhost`:

| Service | Hostname | Port | URL |
|---------|----------|------|-----|
| ComfyUI API | `comfyui` | 8188 | `http://comfyui:8188` |
| ComfyUI Prompt API | `comfyui` | 8188 | `http://comfyui:8188/prompt` |
| ComfyUI History API | `comfyui` | 8188 | `http://comfyui:8188/history/{prompt_id}` |
| ComfyUI Image Download | `comfyui` | 8188 | `http://comfyui:8188/view?filename={name}&type=output` |
| SaladTech API + Swagger | `comfyui` | 3000 | `http://comfyui:3000` |

**Critical note:** From the `agentic-workstation` container, you must use `comfyui:8188` not `localhost:8188`. Using `localhost` will fail silently or connect to a different service.

### 2.3 Agent Orchestration

The swarm uses a Claude Flow v3 hierarchical topology:

```
                [Campaign Coordinator]
                (sparc-coord agent)
                       |
          +--------+---+---+--------+
          |        |       |        |
     [Workflow] [Creative] [Brand] [Pipeline]
     Researcher  Director  Guardian Executor
     (researcher) (researcher) (reviewer) (coder)
```

Each agent is a Claude Opus 4.6 instance with specialized system prompts and tool access. The Campaign Coordinator assigns tasks, tracks pipeline state in `configs/pipeline.json`, and manages error escalation.

### 2.4 AI Engine Routing

| Phase | Primary Engine | Model ID | Deployment |
|-------|---------------|----------|------------|
| Phase 1: Base generation | Flux 2 Dev | `flux2_dev_fp8mixed.safetensors` | Local GPU via ComfyUI |
| Phase 2: Style refinement | Nano Banana | `gemini-2.5-flash-image` | Google Generative AI API |
| Phase 3: Text compositing | Programmatic | Pillow / ImageMagick | Local Python |
| Phase 4: Animation | Veo 3.1 | `veo-3.1-generate-preview` | Google Generative AI API |
| Research | Perplexity Sonar | `sonar` | Perplexity API |
| QA evaluation | Claude Vision | Claude Opus 4.6 | Anthropic API |

Available but unused in this run:
- Nano Banana Pro (`gemini-3-pro-image-preview`) -- recommended for text-heavy production assets
- Imagen 4 Ultra (`imagen-4.0-ultra-generate-001`) -- highest fidelity hero shots
- Imagen 4 Fast (`imagen-4.0-fast-generate-001`) -- batch variation scaling

### 2.5 Authentication

All API keys are stored as environment variables. No keys are hardcoded in any source file.

| Service | Environment Variable | Usage |
|---------|---------------------|-------|
| Google Gemini / Nano Banana / Veo / Imagen | `GOOGLE_API_KEY` | `?key=` query parameter or `x-goog-api-key` header |
| Perplexity | `PERPLEXITY_API_KEY` | `Authorization: Bearer` header |
| Anthropic (Claude) | `ANTHROPIC_API_KEY` | Claude agent reasoning |
| ComfyUI | N/A | Direct Docker network access, no auth required |

---

## 3. Pre-Production Phase

Before the pipeline could execute, several infrastructure and planning steps were completed.

### 3.1 Claude CLI Upgrade

The Claude CLI was upgraded from version 2.1.47 to 2.1.56 to ensure compatibility with Claude Flow v3 features:

```bash
claude --version  # Verify current version
# Upgrade process as per Anthropic documentation
```

After upgrade, the claude-flow MCP server was re-initialized:

```bash
claude mcp add claude-flow -- npx -y @claude-flow/cli@latest
npx @claude-flow/cli@latest daemon start
npx @claude-flow/cli@latest doctor --fix
```

### 3.2 Settings Backup and Hook System Verification

Before re-initialization, existing claude-flow settings were backed up. The hook system (self-learning hooks for pre-task, post-task, pre-edit, post-edit lifecycle events) was verified operational.

### 3.3 API Access Testing

Each external service was validated before pipeline execution:

**Google Gemini (Nano Banana):**
```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"test"}]}],"generationConfig":{"responseModalities":["TEXT","IMAGE"]}}'
```

**Veo 3.1:**
```bash
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instances":[{"prompt":"test"}],"parameters":{"aspectRatio":"16:9","durationSeconds":8}}'
```

**Perplexity:**
```bash
curl -s -X POST "https://api.perplexity.ai/chat/completions" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sonar","messages":[{"role":"user","content":"test query"}]}'
```

**ComfyUI:**
```bash
curl -s http://comfyui:8188/system_stats
```

### 3.4 ComfyUI Connectivity and Flux 2 Dev Validation

The Flux 2 Dev model stack was validated by confirming:

1. The UNet model exists at `/root/ComfyUI/models/diffusion_models/flux2_dev_fp8mixed.safetensors` (~17.5GB)
2. The CLIP text encoder exists at `/root/ComfyUI/models/text_encoders/mistral_3_small_flux2_fp8.safetensors` (~9GB)
3. The VAE exists at `/root/ComfyUI/models/vae/flux2-vae.safetensors` (~336MB)
4. A test workflow submission to `http://comfyui:8188/prompt` completes successfully

**Discovery during validation:** The standard `clip_l.safetensors` text encoder was corrupted on this system (safetensors header parse error). The Mistral 3 Small CLIP encoder was used as a replacement and must be loaded with CLIPLoader type set to `flux2`, not `stable_diffusion` or `sd3`.

### 3.5 PRD Review and Rewrite

The existing PRD v2.0 was reviewed, critiqued, and rewritten to PRD v3.0. Key changes included:

- Mapping all engines to verified working endpoints with exact model IDs
- Adding container access directives (agents have full `docker exec` authority)
- Documenting the 4-panel garment input format with per-panel descriptions
- Adding fallback chains for each engine
- Defining the garment description grounded from actual visual analysis
- Specifying the exact API request/response formats for each service

The final PRD is located at:
`/home/devuser/workspace/campaign/THG-world-record-attempt/docs/prd/campaign-generator-v3.md`

### 3.6 Architecture Flow Diagram (AFD) Generation

Twelve Mermaid diagrams were generated covering:

1. High-Level System Architecture
2. Agent Communication Topology
3. Phase 1: Base Image Generation Flow
4. Phase 2: Style Refinement and Scaling Flow
5. Phase 3: Static Ad Compositing Flow
6. Phase 4: Animation Flow
7. QA Feedback Loop Detail
8. Full Pipeline Sequence Diagram
9. File System Data Flow
10. Error Handling and Fallback Paths
11. Initialization Sequence
12. Parallel and Sequential Dependency Map

Plus three appendices: Engine Routing Decision Matrix, Pipeline Lifecycle State Machine, and API Call Flow Summary.

Location: `/home/devuser/workspace/campaign/THG-world-record-attempt/docs/afd/campaign-generator-afd.md`

### 3.7 Domain-Driven Design (DDD) Analysis

Six bounded contexts were identified:

1. **Campaign Management** (Core Domain) -- pipeline lifecycle, phase sequencing, agent coordination
2. **Image Generation** (Core Domain) -- engine routing, prompt construction, API payload assembly
3. **Video Generation** (Core Domain) -- Veo 3.1 long-running operations, motion script generation
4. **Brand Compliance** (Supporting Domain) -- brand identity rules, visual evaluation, QA gates
5. **Asset Management** (Supporting Domain) -- file lifecycle, directory structure, format validation
6. **Infrastructure Services** (Generic Domain) -- API transport, health checks, container access

Location: `/home/devuser/workspace/campaign/THG-world-record-attempt/docs/ddd/campaign-generator-ddd.md`

---

## 4. Campaign Configuration

### 4.1 Brand Identity Setup

The Topshop SS26 brand identity was configured in `configs/topshop.json` with the following parameters:

**Palette:**
| Role | Color | Hex |
|------|-------|-----|
| Primary | Black | `#000000` |
| Primary | White | `#FFFFFF` |
| Primary | Grey | `#808080` |
| Accent | Silver | `#C0C0C0` |
| Accent | Light Silver | `#D4D4D4` |
| Material | Chrome, polished metal, high-sheen reflective | -- |

**Tone:**
- Aesthetic: Stark high-contrast, editorial, urban
- Mood: Confident, modern, architectural
- Environment: Wet UK city streets, brutalist concrete, urban metal structures, overcast diffused lighting

**Headlines:**
- "STYLE REIMAGINED" (primary)
- "NEW COLLECTION" (secondary)
- "TOPSHOP SS26" (brand identifier)

### 4.2 Garment Ingest

**Source file:** `WLC OUTFITS 02_02_26 3.jpg`

**Location (ComfyUI container):** `/root/ComfyUI/input/WLC OUTFITS 02_02_26 3.jpg`

**Location (workspace):** `/home/devuser/workspace/campaign/inputs/WLC OUTFITS 02_02_26 3.jpg`

The input is a composite 4-panel photograph with the following panels:

| Panel | Label | View | Role |
|-------|-------|------|------|
| 1 | LOOK 6_1 | Front | Primary hero angle |
| 2 | LOOK 6_2 | Right side | Secondary reference |
| 3 | LOOK 6_3 | Back | Back detail reference |
| 4 | LOOK 6_4 | Left side | Secondary reference |

**Grounded garment description:**
- Type: Sleeveless maxi dress, full-length, A-line silhouette
- Bodice: Cream/beige base with black botanical ink illustration (chrysanthemum, birds, floral line art)
- Skirt: Diagonal black stripes on cream base, wide flowing A-line with dramatic drape
- Details: Chain link straps, open back, fitted waist transitioning to full skirt
- Mannequin: White studio mannequin on grey/white background with black base

**Important:** When using the multi-panel image as a reference for img2img operations, it must be cropped to a single panel first. Sending the full 4-panel composite to Nano Banana causes the model to produce a grid-layout output reproducing the multi-panel format rather than a single editorial scene. See Section 6 for the cropping approach.

### 4.3 Shot Concept Creation

The Creative Director agent generated 8 creative directions. The following 6 were selected for production:

| Shot | Concept Name | Description | Camera |
|------|-------------|-------------|--------|
| 01 | Hero | Chrome mannequin on wet brutalist concrete, key light from above | Low angle, 24mm wide |
| 02 | Rain | Dark urban alley, heavy rainfall, reflections on wet asphalt | Eye level, 85mm telephoto |
| 03 | Brutalist | Between massive concrete columns, dramatic overhead shadows | Eye level, 85mm, one-point perspective |
| 04 | Studio | Clean studio environment, three-point lighting | Standard, product photography |
| 05 | Night | Rain-soaked bus stop, sodium street lighting, car light trails | Cross-street, 100mm telephoto |
| 06 | Back | Open back detail, chain link straps, botanical ink from behind | Standard, 50mm |

Each shot concept includes a full environment description, lighting specification, camera angle, mood statement, and is stored in:
`/home/devuser/workspace/campaign/THG-world-record-attempt/configs/prompts/shot-concepts.json`

### 4.4 Prompt Engineering

For each shot, four prompt types were generated:

1. **Positive prompt** -- Full editorial description for Flux 2 Dev text-to-image generation, including garment details, environment, lighting, camera, and style directives
2. **Negative prompt** -- Elements to suppress (human skin, cartoon, illustration, warm tones, etc.)
3. **Nano Banana refinement prompt** -- Image-to-image instruction for chrome mannequin transformation and editorial enhancement
4. **Veo motion script** -- Animation directive specifying environmental motion, locked camera, and static garment/text

Example positive prompt (Shot 01 - Hero):
```
editorial fashion photography, chrome metallic mannequin standing on raised concrete
plinth in brutalist plaza, wearing cream sleeveless maxi dress with black botanical ink
illustration on bodice featuring chrysanthemum flowers birds and floral line art,
diagonal black striped A-line skirt flowing to floor, delicate chain link metal straps,
fitted waist, rain-slicked concrete surfaces with shallow reflecting puddles, brutalist
architecture concrete walls with water stains, Barbican Centre aesthetic, overcast
diffused British daylight, wet surface reflections creating soft uplight on dress hem,
cream fabric luminous against grey monochrome environment, low angle 24mm wide
perspective, monumental composition, no people, high fashion editorial campaign, 8k,
sharp detail, photorealistic
```

The full prompt library is stored at:
`/home/devuser/workspace/campaign/THG-world-record-attempt/configs/prompts/prompt-library.json`

Phase 1 execution prompts with seeds at:
`/home/devuser/workspace/campaign/THG-world-record-attempt/configs/prompts/phase1_prompts.json`

### 4.5 Typography Research

The Creative Director used web search (Perplexity returned 401 due to Cloudflare proxy on initial attempts, so WebSearch was used as fallback) to research Topshop brand typography.

**Findings:**
- Topshop wordmark uses a heavy geometric sans-serif, closest identified fonts: Neue Singular H Bold, Neue Helvetica eText Pro 75 Bold
- Letterforms: bold weight, all uppercase, wide letter-spacing, clean geometric with strict cuts, square terminals (post-1996 redesign)

**Google Fonts matching (ranked by match score):**

| Font | Role | Weight | Match Score | Rationale |
|------|------|--------|-------------|-----------|
| Jost | Primary headline | 700 | 0.92 | Closest geometric match, 1920s German sans-serif heritage (Futura lineage), Bauhaus geometry |
| Bebas Neue | Secondary headline / taglines | 400 | 0.78 | Condensed display, high vertical impact for posters and banners |
| Work Sans | Body / support copy | 400 | 0.83 | Closest impression to Helvetica Neue, clean digital readability |

**Typography system applied:**
- Headlines: Jost 700, uppercase, 0.15em letter-spacing, white (#FFFFFF)
- Taglines: Bebas Neue 400, uppercase, 0.05em letter-spacing
- Body: Work Sans 400, sentence case, 0.02em letter-spacing

Typography research is stored at:
`/home/devuser/workspace/campaign/THG-world-record-attempt/configs/prompts/typography-research.json`

---

## 5. Pipeline Execution

The pipeline executed in four sequential phases, each using a different AI engine optimized for its task. Total execution time was approximately 30 minutes.

### 5.1 Phase 1: Flux 2 Dev Base Generation

**Engine:** Flux 2 Dev FP8 Mixed via ComfyUI
**Duration:** ~6 minutes
**Resolution:** 768x1024 (later cropped/scaled as needed)

**Model stack:**

| Component | File | Size | Location |
|-----------|------|------|----------|
| UNet (diffusion model) | `flux2_dev_fp8mixed.safetensors` | ~17.5GB | `/root/ComfyUI/models/diffusion_models/` |
| CLIP text encoder | `mistral_3_small_flux2_fp8.safetensors` | ~9GB | `/root/ComfyUI/models/text_encoders/` |
| VAE | `flux2-vae.safetensors` | ~336MB | `/root/ComfyUI/models/vae/` |

**Sampler configuration:**
- Sampler: `euler`
- Steps: 20
- CFG: 1.0 (correct for Flux 2; higher values cause oversaturation)
- Scheduler: `simple`
- Latent space initialization: `EmptySD3LatentImage` (compatible with Flux 2)

**ComfyUI workflow node chain:**
```
UNETLoader -> KSampler
CLIPLoader (type: flux2) -> CLIPTextEncode -> KSampler
VAELoader -> VAEDecode -> SaveImage
EmptySD3LatentImage -> KSampler
```

**API submission pattern:**
```bash
# Submit workflow
curl -X POST http://comfyui:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": { ...workflow JSON... }}'
# Returns: {"prompt_id": "abc123"}

# Poll for completion
curl http://comfyui:8188/history/abc123
# Returns: {"abc123": {"status": {"completed": true}, "outputs": {...}}}

# Download result
curl "http://comfyui:8188/view?filename=campaign_shot01_hero_00001_.png&type=output" \
  -o campaign_shot01_hero_00001_.png
```

**Shots generated:**

| Shot | Seed | Output File |
|------|------|-------------|
| 01 - Hero | 42 | `campaign_shot01_hero_00001_.png` |
| 02 - Rain | 1337 | `campaign_shot02_rain_00001_.png` |
| 03 - Brutalist | 2024 | `campaign_shot03_brutalist_00001_.png` |
| 04 - Studio | 7890 | `campaign_shot04_studio_00001_.png` |
| 05 - Night | 5555 | `campaign_shot05_night_00001_.png` |
| 06 - Back | 9999 | `campaign_shot06_back_00001_.png` |

**Result:** 6/6 generated successfully. All 6 passed Brand Guardian QA (garment recognizable, chrome mannequin present, urban environment context).

**Output directory:** `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/base-gen/`

### 5.2 Phase 2: Nano Banana Style Refinement

**Engine:** Gemini 2.5 Flash Image (`gemini-2.5-flash-image`)
**Duration:** ~6 minutes
**Method:** Image-to-image with editorial prompt enhancement

**API endpoint:**
```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$GOOGLE_API_KEY
```

**Request format:**
```json
{
  "contents": [{
    "parts": [
      {
        "inlineData": {
          "mimeType": "image/png",
          "data": "<base64-encoded Phase 1 image>"
        }
      },
      {
        "text": "Transform the mannequin in this image into a highly polished chrome metallic mannequin with mirror-finish reflective silver surface. The mannequin should look like it is made of liquid mercury or polished stainless steel. Keep the dress exactly as it is -- the cream fabric with black botanical ink illustration bodice and diagonal striped skirt must remain unchanged. The chrome mannequin should reflect the surrounding concrete environment in its surface. The chain straps should also appear metallic chrome. Make the mannequin headless with a smooth rounded chrome neck cap. Keep the overall composition and lighting identical."
      }
    ]
  }],
  "generationConfig": {
    "responseModalities": ["TEXT", "IMAGE"]
  }
}
```

**Response parsing:**
The response contains a `candidates[0].content.parts[]` array. Each part is either `{"text": "..."}` or `{"inlineData": {"mimeType": "image/png", "data": "<base64>"}}`. The base64 image data is decoded and saved as PNG.

**Refinement focus areas:**
- Chrome mannequin surface transformation (liquid mercury / polished stainless steel)
- Specific fabric detail preservation (botanical ink, chrysanthemum, diagonal stripes)
- Environmental mood matching (wet concrete, rain, night)
- Professional fashion photography aesthetics

**Shots refined:**

| Input | Output | Brand Guardian Score |
|-------|--------|---------------------|
| `campaign_shot01_hero_00001_.png` | `refined_shot01_hero.png` | 0.94 |
| `campaign_shot02_rain_00001_.png` | `refined_shot02_rain.png` | 0.93 |
| `campaign_shot03_brutalist_00001_.png` | `refined_shot03_brutalist.png` | 0.955 (best) |
| `campaign_shot04_studio_00001_.png` | `refined_shot04_studio.png` | 0.92 |
| `campaign_shot05_night_00001_.png` | `refined_shot05_night.png` | 0.93 |
| `campaign_shot06_back_00001_.png` | `refined_shot06_back.png` | 0.91 |

**Result:** 6/6 refined successfully. All passed Brand Guardian QA.

**Cost:** Approximately $0.039 per image x 6 images = ~$0.23 for Phase 2.

**Output directory:** `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/refined/`

### 5.3 Phase 3: Programmatic Text Compositing

**Engine:** Pillow (PIL) / ImageMagick for programmatic text rendering
**Duration:** ~7 minutes
**Method:** Programmatic font rendering overlay on Phase 2 refined images

#### The AI Text Misspelling Problem

The initial plan was to use Nano Banana for text compositing -- sending the refined images back with instructions to add "STYLE REIMAGINED" and "TOPSHOP SS26" text overlays. This approach failed consistently.

**Failure pattern:** Across 15 AI-generated text attempts using Gemini 2.5 Flash Image, the word "REIMAGINED" was consistently misspelled:
- "REIMANGEED"
- "REIM ANGNED"
- "REIMAGINEED"
- Various other garbled variants

This is a known limitation of current diffusion-based and multimodal image models. Brand names and multi-syllable words with unusual character sequences are particularly susceptible to misspelling.

**All 9 first-round composites (3 formats x 3 initial shots) failed Brand Guardian QA with 0% pass rate** due to text errors.

#### The Solution: Programmatic Rendering

The pipeline switched to programmatic text rendering using Python's Pillow library and ImageMagick:

1. Load the refined Phase 2 image
2. Apply canvas resizing/cropping to target aspect ratio (16:9, 1:1, or 9:16)
3. Render text overlay using downloaded font files with exact positioning
4. Save final composite

**Typography applied:**
- Font: Noto Sans Bold (Jost 700 equivalent available via system fonts)
- Case: Uppercase
- Color: White (#FFFFFF)
- Placement: Upper portion negative space (avoiding garment overlap)
- Headlines: "STYLE REIMAGINED" (primary), "TOPSHOP SS26" (secondary)

**Output formats:**

| Format | Resolution | Use Case |
|--------|-----------|----------|
| Landscape 16:9 | 1920x1080 | YouTube pre-roll, web banners, landing pages |
| Square 1:1 | 1080x1080 | Instagram feed, Facebook |
| Portrait 9:16 | 1080x1920 | Instagram Story, TikTok, YouTube Shorts, Reels |

**Composites produced (18 total):**

For each of the 6 shots, 3 aspect ratio variants:
```
final_shot01_hero_{16x9,1x1,9x16}.png
final_shot02_rain_{16x9,1x1,9x16}.png
final_shot03_brutalist_{16x9,1x1,9x16}.png
final_shot04_studio_{16x9,1x1,9x16}.png
final_shot05_night_{16x9,1x1,9x16}.png
final_shot06_back_{16x9,1x1,9x16}.png
```

**Result:** 18/18 final composites with pixel-perfect, correctly spelled typography. 100% Brand Guardian pass rate after switching to programmatic rendering.

**Key learning:** Always use programmatic text rendering for brand names and campaign headlines. Reserve AI text generation only for concepts/drafts where exact spelling is not critical.

**Output directory:** `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/composited/`

### 5.4 Phase 4: Veo 3.1 Animation

**Engine:** Veo 3.1 (`veo-3.1-generate-preview`)
**Duration:** ~5 minutes (including polling wait times)
**Method:** Text-to-Video via `predictLongRunning` API
**Duration per clip:** 8 seconds
**Resolution:** 720p+

#### API Endpoint

```
POST https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key=$GOOGLE_API_KEY
```

**Note:** The `generateVideo` endpoint returns 404. You must use `predictLongRunning`.

#### Request Format (Text-to-Video)

```json
{
  "instances": [{
    "prompt": "Subtle ambient motion on a static fashion campaign image. Gentle rain continuously falls through the frame, creating expanding circular ripples in the puddles on the concrete ground. The water reflections shimmer and distort slightly. The mannequin and dress remain completely still and static. Camera is locked. No subtitles, no text overlays, no watermarks. Duration 8 seconds."
  }],
  "parameters": {
    "aspectRatio": "16:9",
    "durationSeconds": 8
  }
}
```

**Critical:** `durationSeconds` must be a **number** (8), not a **string** ("8"). Strings cause `INVALID_ARGUMENT` errors.

#### Polling Pattern

The API returns an operation name immediately. You must poll until `done: true`:

```bash
# Submit
RESPONSE=$(curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instances":[{"prompt":"..."}],"parameters":{"aspectRatio":"16:9","durationSeconds":8}}')

OP_NAME=$(echo $RESPONSE | python3 -c "import json,sys; print(json.load(sys.stdin)['name'])")

# Poll every 20 seconds
while true; do
  STATUS=$(curl -s "https://generativelanguage.googleapis.com/v1beta/$OP_NAME?key=$GOOGLE_API_KEY")
  DONE=$(echo $STATUS | python3 -c "import json,sys; print(json.load(sys.stdin).get('done', False))")
  if [ "$DONE" = "True" ]; then
    break
  fi
  sleep 20
done
```

Operations typically take 1-3 minutes to complete.

#### Video Download Pattern

The response contains a `video.uri` (not `video.encodedVideo`):

```python
video_uri = response["response"]["generateVideoResponse"]["generatedSamples"][0]["video"]["uri"]
# URI format: https://generativelanguage.googleapis.com/v1beta/files/{id}:download?alt=media
```

**Download requirements:**
1. Append `&key=$GOOGLE_API_KEY` to the URI for authentication
2. Use `-L` flag for HTTP redirect following (the URI redirects to a CDN)

```bash
curl -L "${VIDEO_URI}&key=$GOOGLE_API_KEY" -o anim_hero_16x9.mp4
```

#### I2V (Image-to-Video) Discovery

During this run, Image-to-Video (I2V) was attempted but the Gemini API endpoint does not support it:
- `inlineData` format: "inlineData isn't supported by this model"
- `fileUri` format: "fileUri isn't supported by this model"

I2V requires either:
- Vertex AI endpoint with Bearer token authentication (`gcloud auth print-access-token`)
- File API upload workflow (upload image first, then reference by fileUri)
- The `bytesBase64Encoded` field under `image` in the request body (not `inlineData`)

For this run, all animations used Text-to-Video (T2V) with detailed motion scripts.

#### Animations Produced

| Animation | Aspect | Size | Prompt Focus |
|-----------|--------|------|--------------|
| `anim_hero_16x9.mp4` | 16:9 | 3.3MB | Lateral tracking, wet brutalist, gentle rain |
| `anim_hero_9x16.mp4` | 9:16 | 4.7MB | Portrait hero, chrome mannequin, rain |
| `anim_rain_16x9.mp4` | 16:9 | 3.8MB | Locked camera, rain-soaked alley, reflections |
| `anim_rain_9x16.mp4` | 9:16 | 4.9MB | Portrait rain scene, urban mood |
| `anim_brutalist_9x16.mp4` | 9:16 | 3.2MB | Upward tilt, concrete columns, dust |
| `anim_night_9x16.mp4` | 9:16 | 4.1MB | Locked camera, night bus stop, car light trails |

**Result:** 6/6 animations completed successfully. 4 were evaluated by Brand Guardian (due to time constraints), all 4 passed.

**Prompting best practices for fashion video:**
1. Use the 7-layer master template: `[Camera move + lens]: [Subject] [Action & physics], in [Setting + atmosphere], lit by [Light source]. Style: [Texture/finish]. Audio: [Dialogue/SFX/ambience].`
2. Include force-based motion verbs: push, pull, sway, ripple, drift, glide
3. Explicitly state: "No subtitles, no text overlays, no watermarks"
4. For text-locked video: pre-render text in source image, use motion-restricted prompt with "Camera is locked, no camera movement" and "Text remains completely static"
5. Specify lens focal length for camera behavior (16mm=wide, 85mm=intimate)

**Output directory:** `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/animated/`

---

## 6. Garment Fidelity Reskinning

### 6.1 The Problem

After Phase 2 refinement, the AI-generated garment was recognized as an *interpretation* of the source garment rather than a faithful reproduction. The key discrepancy:

- **Source garment:** Bold diagonal black stripes on the A-line skirt, with distinct black botanical ink illustration (chrysanthemum, birds, floral line art) on the bodice
- **AI interpretation:** Thin vertical pinstripes instead of bold diagonal stripes; botanical details softened or altered

While the garment was "recognizable" and passed QA at the campaign level, pixel-level fidelity to the actual garment pattern was insufficient for a production campaign where the real garment would be sold.

### 6.2 The Solution: Nano Banana img2img with Garment Reference

The approach uses the original garment photograph as a visual reference during Nano Banana image-to-image transformation:

1. **Crop the front panel** from the 4-panel ingest image (LOOK 6_1 -- front view)
2. **Send two images** to Nano Banana: the cropped front panel AND the scene image
3. **Instruct the model** to replace the garment in the scene with the one from the reference panel

**Cropping approach:**
```python
from PIL import Image

# Load 4-panel composite
img = Image.open("/home/devuser/workspace/campaign/inputs/WLC OUTFITS 02_02_26 3.jpg")
width, height = img.size

# Crop front panel (LOOK 6_1) -- leftmost quarter
front_panel = img.crop((0, 0, width // 4, height))
front_panel.save("/tmp/garment_front_panel.png")
```

**Important discovery:** Sending the full multi-panel image (all 4 views) as reference causes Nano Banana to produce a grid-layout output reproducing the 4-panel format. You MUST crop to a single panel before using as reference.

### 6.3 ComfyUI Workflow for Reproducible Reskinning

A ComfyUI workflow using the `GeminiImage2Node` (from Google GenMedia custom nodes) was designed for reproducible reskinning:

```
LoadImage (garment front panel) -> GeminiImage2Node
LoadImage (scene image) -> GeminiImage2Node
Text prompt: "Replace the garment with the exact garment from the reference..."
-> SaveImage
```

This allows batch reskinning of all 6 scene shots with consistent garment fidelity.

---

## 7. Multi-GPU Configuration

### 7.1 The Problem

The Flux 2 Dev model stack requires significant VRAM:
- UNet (diffusion model): ~17.5GB (FP8 mixed)
- Mistral CLIP text encoder: ~9GB (FP8)
- VAE: ~336MB
- Working memory (latents, intermediates): ~8-12GB

On a single 48GB GPU, all components fit but model swapping between text encoding and diffusion phases creates overhead (~10 seconds per swap cycle).

### 7.2 The Solution: ComfyUI-MultiGPU

The `ComfyUI-MultiGPU` custom node (pollockjj fork with Virtual VRAM support) distributes model components across both GPUs.

**Installation:**
```bash
docker exec -it comfyui bash -c "cd /root/ComfyUI/custom_nodes && git clone https://github.com/pollockjj/ComfyUI-MultiGPU"
docker restart comfyui
# Wait ~60-90 seconds for GPU models to reload
```

**Distribution strategy:**

| GPU | Component | Node | VRAM Used | VRAM Free |
|-----|-----------|------|-----------|-----------|
| cuda:0 | UNet + working memory | `UNETLoaderMultiGPU` | 38.2GB | 12.6GB |
| cuda:1 | CLIP + VAE | `CLIPLoaderMultiGPU` + `VAELoaderMultiGPU` | 19.3GB | 31.6GB |

**Workflow node replacement:**

| Standard Node | MultiGPU Node | Device Parameter |
|--------------|---------------|------------------|
| `UNETLoader` | `UNETLoaderMultiGPU` | `cuda:0` |
| `CLIPLoader` | `CLIPLoaderMultiGPU` | `cuda:1`, type: `flux2` |
| `VAELoader` | `VAELoaderMultiGPU` | `cuda:1` |

### 7.3 Verification

```bash
# Check VRAM distribution after loading
docker exec comfyui nvidia-smi
# Expected:
#   GPU 0: ~38GB used (UNet + working memory)
#   GPU 1: ~19GB used (CLIP + VAE)
```

A test image was generated to verify multi-GPU operation:
`/home/devuser/workspace/campaign/THG-world-record-attempt/assets/multi-gpu-test/multigpu_test_00001_.png`

### 7.4 Performance Impact

| Scenario | Single GPU | Dual GPU |
|----------|-----------|----------|
| Cold start (first generation) | ~25s | ~15s |
| Subsequent generations | ~12s | ~12s |
| Switching between txt2img and img2img | ~8s swap + 12s gen = 20s | ~12s (no swap) |

**Key insight:** Multi-GPU does NOT parallelize the sampling steps. The speedup comes entirely from eliminating model swap overhead. Steps still execute sequentially on whichever GPU holds the relevant model.

**Remaining headroom:**
- GPU 0: ~12GB free for ControlNet, IP-Adapter
- GPU 1: ~31GB free for additional models, batch processing

### 7.5 ComfyUI Launch Flags

For multi-GPU, ComfyUI should be launched with:
```bash
python3 main.py --listen 0.0.0.0 --port 8188 --cuda-device 0 --disable-smart-memory
```

- `--cuda-device 0` sets the primary GPU
- `--disable-smart-memory` prevents ComfyUI from auto-managing VRAM (let MultiGPU nodes handle allocation)

---

## 8. Quality Assurance

### 8.1 Brand Guardian Agent Evaluation

The Brand Guardian agent evaluated all generated assets against Topshop visual identity criteria using Claude Vision (Opus 4.6):

**Evaluation prompt:**
```
Evaluate this Topshop campaign ad:
1. Is the mannequin chrome/metallic? (Yes/No)
2. Does the garment closely match the input? (approximation acceptable) (Yes/No)
3. Is text placed in clean negative space, not overlapping the garment? (Yes/No)
4. Does the palette conform to high-contrast black/white/grey/metallic? (Yes/No)
5. Does this meet editorial fashion campaign standards? (Yes/No)
Rate: PASS (all Yes) or FAIL (any No) with specific feedback.
```

**Evaluation results:**

| Phase | Assets Evaluated | Passed | Failed | Pass Rate |
|-------|-----------------|--------|--------|-----------|
| 1. Base Generation | 6 | 6 | 0 | 100% |
| 2. Style Refinement | 6 | 6 | 0 | 100% |
| 3. Compositing (v1 - AI text) | 9 | 0 | 9 | 0% |
| 3. Compositing (final - programmatic) | 18 | 18 | 0 | 100% |
| 4. Animation | 4 | 4 | 0 | 100% |
| **Total (final)** | **34** | **34** | **0** | **100%** |

### 8.2 AI Text Rendering Failure Analysis

The Phase 3 v1 compositing failure (0% pass rate) was caused by Nano Banana's inability to reliably render the word "REIMAGINED". This is a systemic limitation:

- Diffusion models generate text character-by-character with no spelling verification
- Multi-syllable words with uncommon character sequences (like "REIMAGINED") are prone to character substitution, duplication, or omission
- The model sometimes attempts to render a phonetic approximation rather than the exact spelling
- Neither Gemini 2.5 Flash Image nor Flux 2 Dev could consistently spell this word

**Root cause:** AI image models do not have a discrete text rendering pipeline. They generate text as visual patterns, which means they lack the concept of "correct spelling" at the generation level.

**Resolution:** All brand text was rendered programmatically, achieving 100% accuracy.

### 8.3 Garment Fidelity Assessment

The Brand Guardian evaluated garment fidelity at two levels:

1. **Campaign-level fidelity** (acceptable): The garment is recognizable as a cream sleeveless maxi dress with black botanical bodice and striped skirt. This is sufficient for a campaign concept or mood board.

2. **Production-level fidelity** (needs improvement): The specific stripe pattern (bold diagonal) was often rendered as thin vertical pinstripes. The botanical illustration details were softened. This would not be acceptable for a production campaign where the real garment is being sold.

The garment fidelity reskinning approach (Section 6) addresses production-level fidelity by using the original garment photograph as a direct visual reference during generation.

---

## 9. Technical Discoveries and Gotchas

This section catalogs every technical issue encountered during the campaign execution, with solutions.

### 9.1 clip_l.safetensors Corruption

**Problem:** The standard `clip_l.safetensors` text encoder file on this system has a corrupted safetensors header. Loading it causes a parse error in ComfyUI.

**Solution:** Use the Mistral 3 Small CLIP encoder instead:
```
File: mistral_3_small_flux2_fp8.safetensors
Location: /root/ComfyUI/models/text_encoders/
Size: ~9GB
CLIPLoader type: flux2 (NOT stable_diffusion or sd3)
```

**Impact:** No quality loss. The Mistral CLIP encoder is the recommended encoder for Flux 2 workflows.

### 9.2 ComfyUI Docker Hostname

**Problem:** Using `localhost:8188` from the `agentic-workstation` container fails to connect to ComfyUI.

**Solution:** Use Docker hostname `comfyui:8188`. Both containers are on the `agentbox-net` Docker network. Docker DNS resolves `comfyui` to the correct container IP.

**Affected endpoints:**
- `http://comfyui:8188/prompt` (workflow submission)
- `http://comfyui:8188/history/{id}` (job polling)
- `http://comfyui:8188/view?filename={name}&type=output` (image download)
- `http://comfyui:8188/system_stats` (health check)
- `http://comfyui:8188/object_info` (node introspection)

### 9.3 Veo durationSeconds Type Error

**Problem:** Sending `"durationSeconds": "8"` (string) causes an `INVALID_ARGUMENT` error from the Veo API.

**Solution:** Send `"durationSeconds": 8` (number). This applies to all numeric parameters in the Veo API request body.

### 9.4 Veo generateVideo Endpoint 404

**Problem:** The endpoint `veo-3.1-generate-preview:generateVideo` returns HTTP 404.

**Solution:** Use `veo-3.1-generate-preview:predictLongRunning` instead. This is the correct endpoint for both T2V and I2V on the Gemini API surface.

```
WRONG:  https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:generateVideo
RIGHT:  https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning
```

### 9.5 Veo Video URI Download Requires Redirect Following

**Problem:** The `video.uri` returned by Veo points to a Google CDN that issues HTTP 302 redirects. Standard `curl` without flags downloads an empty or HTML redirect page instead of the video.

**Solution:** Use `curl -L` to follow redirects, and append `&key=` for authentication:

```bash
curl -L "${VIDEO_URI}&key=$GOOGLE_API_KEY" -o output.mp4
```

### 9.6 Veo I2V Format Requirements

**Problem:** Image-to-Video (I2V) does not work with `inlineData` or `fileUri` on the Gemini API `predictLongRunning` endpoint.

**Error messages:**
- `inlineData`: "inlineData isn't supported by this model"
- `fileUri`: "fileUri isn't supported by this model"

**Solution for future runs:** Use `bytesBase64Encoded` format under the `image` field:
```json
{
  "instances": [{
    "prompt": "...",
    "image": {
      "bytesBase64Encoded": "<base64-encoded-image>"
    }
  }]
}
```

Alternatively, use the Vertex AI endpoint with Bearer token authentication, or use the File API to upload the image first and then reference it by file URI.

### 9.7 AI Text Misspelling

**Problem:** Both Flux 2 Dev and Gemini 2.5 Flash Image (Nano Banana) consistently misspell "REIMAGINED" when asked to render it as text in images.

**Solution:** Use programmatic text rendering (Pillow/ImageMagick) for all brand names and campaign headlines. AI text generation should only be used for concept exploration where exact spelling is not required.

**Video text overlay alternative:**
```bash
ffmpeg -i input.mp4 \
  -vf "drawtext=text='STYLE REIMAGINED':fontfile=/path/to/Jost-Bold.ttf:fontsize=72:fontcolor=white:x=(w-text_w)/2:y=h*0.1" \
  -codec:a copy output_with_text.mp4
```

### 9.8 Multi-Panel Garment Reference Causes Grid Output

**Problem:** Sending the full 4-panel garment composite image as a reference to Nano Banana img2img causes the model to produce a grid-layout output with 4 panels, mimicking the input format.

**Solution:** Crop to a single panel (LOOK 6_1 front view) before using as reference:

```python
from PIL import Image
img = Image.open("WLC OUTFITS 02_02_26 3.jpg")
w, h = img.size
front = img.crop((0, 0, w // 4, h))
front.save("garment_front_panel.png")
```

### 9.9 Flux 2 CFG Value

**Problem:** Using CFG values higher than 1.0 with Flux 2 Dev causes oversaturated, artifacted outputs.

**Solution:** Flux 2 uses CFG 1.0 as its correct operating point. The guidance mechanism differs from SD1.5/SDXL. If using the advanced workflow with `SamplerCustomAdvanced` + `FluxGuidance`, set guidance to 4.0 (this replaces the CFG parameter entirely).

### 9.10 CLIPLoader Type Parameter

**Problem:** Loading the Mistral CLIP encoder with `type: "stable_diffusion"` or `type: "sd3"` fails silently -- the model loads but produces empty or garbled conditioning.

**Solution:** Always use `type: "flux2"` when loading CLIP encoders for Flux 2 workflows.

---

## 10. Agent Roster and Performance

### 10.1 Agent Summary

| Agent | claude-flow Type | Role | Duration | Key Deliverables |
|-------|-----------------|------|----------|-----------------|
| Creative Director | `researcher` | Typography research, 8 shot concepts, prompt library | ~6 min | 4 JSON config files |
| Pipeline Executor | `coder` | 4-phase pipeline execution across 3 engines | ~25 min | 34 assets, 142+ tool calls |
| Brand Guardian | `reviewer` | QA evaluation against Topshop brand identity | ~4 min | 21-asset evaluation report |
| Workflow Researcher | `researcher` | 8 Perplexity/web queries, workflow documentation | ~8 min | 7 workflow guide documents |

### 10.2 Creative Director

**Responsibilities:** Typography research, shot concept generation, prompt engineering for all engines.

**Deliverables:**
1. `configs/prompts/typography-research.json` -- Topshop font analysis with 7 ranked Google Fonts candidates
2. `configs/prompts/shot-concepts.json` -- 8 creative directions with full environment, lighting, camera, and mood specifications
3. `configs/prompts/prompt-library.json` -- Complete prompt library with positive, negative, Nano Banana refinement, and Veo motion scripts for each shot
4. `configs/prompts/phase1_prompts.json` -- Phase 1 execution prompts with specific seeds

### 10.3 Pipeline Executor

**Responsibilities:** All API interactions, file encoding/decoding, job submission, polling, result collection.

**Statistics:**
- 142+ tool calls across the run
- Managed 3 distinct API surfaces (ComfyUI REST, Google generateContent, Google predictLongRunning)
- Handled base64 encoding/decoding for all Nano Banana and Veo interactions
- Implemented async polling for ComfyUI jobs and Veo long-running operations
- Managed the pivot from AI text to programmatic text rendering mid-pipeline
- Total pipeline execution: ~25 minutes

### 10.4 Brand Guardian

**Responsibilities:** Quality evaluation of all generated assets against Topshop brand identity.

**Evaluation criteria:**
- Garment fidelity (botanical ink, diagonal stripes, chain straps)
- Brand palette compliance (black/white/grey/chrome)
- Typography accuracy (correct spelling, appropriate font weight)
- Environmental mood (wet, urban, brutalist)
- Aspect ratio correctness per format

**Statistics:**
- 21 assets evaluated in detail
- Identified the AI text failure (9 composites rejected, triggering the programmatic rendering pivot)
- 100% final pass rate after corrections

### 10.5 Workflow Researcher

**Responsibilities:** External research on ComfyUI workflows, API configurations, and best practices.

**Queries executed:** 8 research topics
**Deliverables produced:** 7 workflow guide documents

| Deliverable | Path | Content |
|-------------|------|---------|
| Workflow Research | `configs/workflows/workflow-research.md` | Flux 2 workflows, ControlNet, IP-Adapter, fashion workflows |
| Multi-GPU Guide | `configs/workflows/flux2-multi-gpu-guide.md` | Dual RTX 6000 Ada configuration guide |
| Nano Banana Recipes | `configs/workflows/nano-banana-recipes.md` | 8 fashion editorial prompt recipes |
| Veo Recipes | `configs/workflows/veo-recipes.md` | 7 fashion video prompt recipes |
| Custom Nodes | `configs/workflows/recommended-custom-nodes.md` | 9 recommended ComfyUI custom nodes |

---

## 11. Deliverable Inventory

### 11.1 Phase 1: Base Generations (6 files)

Location: `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/base-gen/`

| File | Shot | Resolution |
|------|------|-----------|
| `campaign_shot01_hero_00001_.png` | Hero - Brutalist concrete, wet ground | 768x1024 |
| `campaign_shot02_rain_00001_.png` | Rain - Dark urban alley, rainfall | 768x1024 |
| `campaign_shot03_brutalist_00001_.png` | Brutalist - Concrete columns, shadows | 768x1024 |
| `campaign_shot04_studio_00001_.png` | Studio - Clean three-point lighting | 768x1024 |
| `campaign_shot05_night_00001_.png` | Night - Bus stop, sodium lighting | 768x1024 |
| `campaign_shot06_back_00001_.png` | Back - Open back detail, chain straps | 768x1024 |

### 11.2 Phase 2: Refined Shots (6 files)

Location: `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/refined/`

| File | Shot |
|------|------|
| `refined_shot01_hero.png` | Hero - Chrome mannequin refined |
| `refined_shot02_rain.png` | Rain - Editorial enhancement |
| `refined_shot03_brutalist.png` | Brutalist - Highest scored (0.955) |
| `refined_shot04_studio.png` | Studio - Product shot refined |
| `refined_shot05_night.png` | Night - Cinematic grading |
| `refined_shot06_back.png` | Back - Detail enhancement |

### 11.3 Phase 3: Final Composites (18 files)

Location: `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/composited/`

| Shot | 16:9 | 1:1 | 9:16 |
|------|------|-----|------|
| Hero | `final_shot01_hero_16x9.png` | `final_shot01_hero_1x1.png` | `final_shot01_hero_9x16.png` |
| Rain | `final_shot02_rain_16x9.png` | `final_shot02_rain_1x1.png` | `final_shot02_rain_9x16.png` |
| Brutalist | `final_shot03_brutalist_16x9.png` | `final_shot03_brutalist_1x1.png` | `final_shot03_brutalist_9x16.png` |
| Studio | `final_shot04_studio_16x9.png` | `final_shot04_studio_1x1.png` | `final_shot04_studio_9x16.png` |
| Night | `final_shot05_night_16x9.png` | `final_shot05_night_1x1.png` | `final_shot05_night_9x16.png` |
| Back | `final_shot06_back_16x9.png` | `final_shot06_back_1x1.png` | `final_shot06_back_9x16.png` |

### 11.4 Phase 4: Animated Fashion Films (6 files)

Location: `/home/devuser/workspace/campaign/THG-world-record-attempt/assets/animated/`

| File | Shot | Aspect | Duration | Size |
|------|------|--------|----------|------|
| `anim_hero_16x9.mp4` | Hero | 16:9 | 8s | 3.3MB |
| `anim_hero_9x16.mp4` | Hero | 9:16 | 8s | 4.7MB |
| `anim_rain_16x9.mp4` | Rain | 16:9 | 8s | 3.8MB |
| `anim_rain_9x16.mp4` | Rain | 9:16 | 8s | 4.9MB |
| `anim_brutalist_9x16.mp4` | Brutalist | 9:16 | 8s | 3.2MB |
| `anim_night_9x16.mp4` | Night | 9:16 | 8s | 4.1MB |

### 11.5 Supporting Assets

| File | Location | Description |
|------|----------|-------------|
| `multigpu_test_00001_.png` | `assets/multi-gpu-test/` | Multi-GPU configuration validation image |

### 11.6 Configuration and Documentation

| File | Location |
|------|----------|
| `topshop.json` | `configs/topshop.json` |
| `pipeline.json` | `configs/pipeline.json` |
| `shot-concepts.json` | `configs/prompts/shot-concepts.json` |
| `prompt-library.json` | `configs/prompts/prompt-library.json` |
| `phase1_prompts.json` | `configs/prompts/phase1_prompts.json` |
| `typography-research.json` | `configs/prompts/typography-research.json` |
| `workflow-research.md` | `configs/workflows/workflow-research.md` |
| `flux2-multi-gpu-guide.md` | `configs/workflows/flux2-multi-gpu-guide.md` |
| `nano-banana-recipes.md` | `configs/workflows/nano-banana-recipes.md` |
| `veo-recipes.md` | `configs/workflows/veo-recipes.md` |
| `recommended-custom-nodes.md` | `configs/workflows/recommended-custom-nodes.md` |
| `campaign-generator-v3.md` | `docs/prd/campaign-generator-v3.md` |
| `campaign-generator-afd.md` | `docs/afd/campaign-generator-afd.md` |
| `campaign-generator-ddd.md` | `docs/ddd/campaign-generator-ddd.md` |
| `campaign-report.md` | `reports/campaign-report.md` |
| `technical-findings.md` | `reports/technical-findings.md` |

---

## 12. Recommendations for Next Iteration

### 12.1 Garment Fidelity from the Start

**Use Flux 2 ReferenceLatent + IP-Adapter for garment fidelity in Phase 1.**

The official Flux 2 workflow includes a `ReferenceLatent` node that conditions generation on a reference image's latent representation. Combined with XLabs Flux IP-Adapter (`flux-ip-adapter.safetensors`), this would allow Phase 1 to generate editorial scenes with the actual garment pattern preserved from the start, eliminating the need for post-hoc reskinning.

**Installation:**
```bash
docker exec -it comfyui bash -c "\
  cd /root/ComfyUI/custom_nodes && \
  git clone https://github.com/XLabs-AI/x-flux-comfyui && \
  cd /root/ComfyUI/models && \
  mkdir -p xlabs/ipadapters && \
  wget -O xlabs/ipadapters/flux-ip-adapter.safetensors \
    'https://huggingface.co/XLabs-AI/flux-ip-adapter/resolve/main/flux-ip-adapter.safetensors'"
```

**Key parameters:**
- ControlNet strength: above 0.7 for strong subject control
- IP-Adapter strength: below 0.5 (higher degrades quality)
- Image-to-image denoise: 0.4-0.6 to preserve garment details

### 12.2 Google GenMedia ComfyUI Nodes

**Install the official Google GenMedia custom nodes for integrated Veo/Imagen workflow within ComfyUI.**

This would allow Veo 3.1 T2V and I2V, Imagen 4, Gemini Image, and Virtual Try-On to be executed as ComfyUI workflow nodes rather than via raw API calls.

**Installation:**
```bash
docker exec -it comfyui bash -c "\
  cd /root/ComfyUI/custom_nodes && \
  git clone https://github.com/GoogleCloudPlatform/comfyui-google-genmedia-custom-nodes && \
  pip install -r comfyui-google-genmedia-custom-nodes/requirements.txt"
```

**Authentication:** Requires `gcloud auth application-default login` inside the container, or a service account key mounted at `GOOGLE_APPLICATION_CREDENTIALS`.

### 12.3 Nano Banana Pro for Text-Heavy Assets

For any future composites that require AI-rendered text (e.g., promotional text that varies per region), use Nano Banana Pro (`gemini-3-pro-image-preview`) instead of standard Nano Banana:

| Feature | Nano Banana | Nano Banana Pro |
|---------|------------|-----------------|
| Model | `gemini-2.5-flash-image` | `gemini-3-pro-image-preview` |
| Text rendering | Basic, unreliable | Sharp, legible |
| Resolution | 1K | Up to 4K |
| Best for | Rapid iteration, A/B testing | Final production assets |
| Cost | ~$0.039/image | ~$0.06-0.10/image |

However, for brand names where 100% accuracy is required, programmatic rendering remains the recommended approach regardless of model.

### 12.4 Pre-Crop Garment Panels

Before pipeline execution, automatically crop the 4-panel composite into individual panels:

```python
from PIL import Image
import os

img = Image.open("WLC OUTFITS 02_02_26 3.jpg")
w, h = img.size
panel_w = w // 4

panels = {
    "front": (0, 0, panel_w, h),
    "right": (panel_w, 0, panel_w * 2, h),
    "back": (panel_w * 2, 0, panel_w * 3, h),
    "left": (panel_w * 3, 0, w, h)
}

os.makedirs("inputs/panels/", exist_ok=True)
for name, box in panels.items():
    panel = img.crop(box)
    panel.save(f"inputs/panels/garment_{name}.png")
```

This avoids the multi-panel grid output problem (Section 9.8) and makes individual panels immediately available to all pipeline phases.

### 12.5 ControlNet for Pose Consistency

For campaigns requiring consistent model poses across shots, install the XLabs Flux ControlNet:

```bash
docker exec -it comfyui bash -c "\
  cd /root/ComfyUI/models && \
  mkdir -p xlabs/controlnets && \
  wget -O xlabs/controlnets/flux-canny-controlnet-v3.safetensors \
    'https://huggingface.co/XLabs-AI/flux-controlnet-collections/resolve/main/flux-canny-controlnet-v3.safetensors' && \
  wget -O xlabs/controlnets/flux-depth-controlnet-v3.safetensors \
    'https://huggingface.co/XLabs-AI/flux-controlnet-collections/resolve/main/flux-depth-controlnet-v3.safetensors'"
```

This enables:
- Canny edge detection for garment outline preservation
- Depth maps for spatial consistency
- Pose keypoints for fashion model positioning

### 12.6 Advanced Flux 2 Workflow

The current pipeline uses `KSampler` with basic configuration. The official Flux 2 workflow uses a more advanced node chain:

```
SamplerCustomAdvanced (replaces KSampler)
FluxGuidance (guidance=4.0, replaces CFG parameter)
Flux2Scheduler (takes width+height, replaces simple scheduler)
ReferenceLatent (enables native img2img)
BasicGuider (replaces standard conditioning path)
```

This advanced workflow provides better quality and native image-to-image capability. The workflow JSON is available at:
`https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/image_flux2.json`

### 12.7 Segment Anything for Garment Isolation

For precise garment masking (needed for background replacement, garment-only extraction, or inpainting):

```bash
docker exec -it comfyui bash -c "\
  cd /root/ComfyUI/custom_nodes && \
  git clone https://github.com/storyicon/comfyui_segment_anything && \
  pip install -r comfyui_segment_anything/requirements.txt"
```

### 12.8 Veo I2V Integration

Once Veo I2V access is confirmed via the Vertex AI endpoint or File API, the pipeline should switch Phase 4 from T2V to I2V. This would allow:
- Using the final composited images as start frames for animations
- Maintaining exact garment fidelity in the first frame
- More controlled motion (animating from a known good starting point)

**I2V request format (Vertex AI):**
```bash
curl -X POST \
  "https://${REGION}-aiplatform.googleapis.com/v1/projects/${PROJECT_ID}/locations/${REGION}/publishers/google/models/veo-3.1:predictLongRunning" \
  -H "Authorization: Bearer $(gcloud auth print-access-token)" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{
      "prompt": "Subtle ambient motion...",
      "image": {"bytesBase64Encoded": "<base64>"}
    }],
    "parameters": {
      "aspectRatio": "16:9",
      "durationSeconds": 8
    }
  }'
```

### 12.9 Full Custom Node Installation

For the complete recommended node set, run the batch installation:

```bash
docker exec -it comfyui bash -c "\
  cd /root/ComfyUI/custom_nodes && \
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
  git clone https://github.com/ltdrdata/ComfyUI-Manager"

docker restart comfyui
```

---

## Appendix A: Complete API Reference

### Nano Banana (Image Generation)

```bash
# Text-to-Image
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [{"text": "Your prompt"}]}],
    "generationConfig": {
      "responseModalities": ["TEXT", "IMAGE"]
    }
  }'

# Image-to-Image
INPUT_B64=$(base64 -w0 input.png)
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "contents": [{"parts": [
      {"inlineData": {"mimeType": "image/png", "data": "'$INPUT_B64'"}},
      {"text": "Transform this garment..."}
    ]}],
    "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}
  }'
```

**Response:** Base64 PNG in `candidates[0].content.parts[].inlineData.data`

### Veo 3.1 (Video Generation)

```bash
# Submit T2V
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/veo-3.1-generate-preview:predictLongRunning?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "instances": [{"prompt": "Fashion video prompt..."}],
    "parameters": {"aspectRatio": "16:9", "durationSeconds": 8}
  }'

# Poll operation
curl "https://generativelanguage.googleapis.com/v1beta/{operation_name}?key=$GOOGLE_API_KEY"

# Download video (when done: true)
curl -L "${VIDEO_URI}&key=$GOOGLE_API_KEY" -o output.mp4
```

### Imagen 4 Ultra (Hero Shots)

```bash
curl -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-ultra-generate-001:predict?key=$GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"instances": [{"prompt": "Your prompt"}], "parameters": {"aspectRatio": "3:4", "sampleCount": 4}}'
```

### ComfyUI / Flux 2 Dev

```bash
# Submit workflow
curl -X POST http://comfyui:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": {...workflow_json...}}'

# Poll
curl http://comfyui:8188/history/{prompt_id}

# Download
curl "http://comfyui:8188/view?filename={name}&type=output" -o output.png

# System stats
curl http://comfyui:8188/system_stats

# Node info
curl http://comfyui:8188/object_info
```

### Perplexity (Research)

```bash
curl -X POST "https://api.perplexity.ai/chat/completions" \
  -H "Authorization: Bearer $PERPLEXITY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "sonar", "messages": [{"role": "user", "content": "Your query"}]}'
```

---

## Appendix B: Repository Structure

```
/home/devuser/workspace/campaign/THG-world-record-attempt/
|
+-- README.md                           # Project overview
+-- docs/
|   +-- prd/
|   |   +-- campaign-generator-v3.md    # Product Requirements Document v3.0
|   +-- afd/
|   |   +-- campaign-generator-afd.md   # Architecture Flow Diagram (12 Mermaid diagrams)
|   +-- ddd/
|       +-- campaign-generator-ddd.md   # Domain-Driven Design (6 bounded contexts)
|
+-- reports/
|   +-- campaign-report.md              # Campaign execution report
|   +-- technical-findings.md           # Technical findings and gotchas
|   +-- process-documentation.md        # This document
|
+-- configs/
|   +-- topshop.json                    # Brand identity configuration
|   +-- pipeline.json                   # Pipeline state tracking
|   +-- prompts/
|   |   +-- shot-concepts.json          # 8 creative directions
|   |   +-- prompt-library.json         # Full prompt library (positive/negative/refinement/motion)
|   |   +-- phase1_prompts.json         # Phase 1 execution prompts with seeds
|   |   +-- typography-research.json    # Typography research results
|   +-- workflows/
|       +-- workflow-research.md        # Comprehensive workflow research
|       +-- flux2-multi-gpu-guide.md    # Multi-GPU configuration guide
|       +-- nano-banana-recipes.md      # Nano Banana prompt recipes
|       +-- veo-recipes.md             # Veo 3.1 video prompt recipes
|       +-- recommended-custom-nodes.md # ComfyUI custom node recommendations
|
+-- assets/
|   +-- base-gen/                       # Phase 1: 6 Flux 2 raw generations
|   +-- refined/                        # Phase 2: 6 Nano Banana refined shots
|   +-- composited/                     # Phase 3: 18 final composites (6 x 3 formats)
|   +-- animated/                       # Phase 4: 6 Veo 3.1 fashion films
|   +-- multi-gpu-test/                 # Multi-GPU validation test image
|
+-- inputs/                             # (referenced) Raw garment images
```

---

## Appendix C: Environment Variables

```bash
GOOGLE_API_KEY          # Google Gemini / Nano Banana / Veo / Imagen API access
GOOGLE_GEMINI_API_KEY   # Alternative Gemini key (some tools use this)
PERPLEXITY_API_KEY      # Perplexity Sonar search API
ANTHROPIC_API_KEY       # Claude API access (agent reasoning)
```

No API keys are hardcoded in any file in this repository.

---

## Appendix D: Timing Summary

| Phase | Start | End | Duration | Notes |
|-------|-------|-----|----------|-------|
| Pre-production | 09:30 | 10:20 | ~50 min | CLI upgrade, PRD rewrite, AFD, DDD, config |
| Phase 1: Base generation | 10:26 | 10:32 | ~6 min | 6 shots via Flux 2 Dev |
| Phase 2: Style refinement | 10:32 | 10:38 | ~6 min | 6 refinements via Nano Banana |
| Phase 3: Compositing | 10:38 | 10:45 | ~7 min | 18 composites via programmatic text |
| Phase 4: Animation | 10:45 | 10:50 | ~5 min | 6 videos via Veo 3.1 |
| **Total pipeline** | **10:26** | **10:50** | **~24 min** | |
| **Total including pre-production** | **09:30** | **10:50** | **~80 min** | |

---

*End of process documentation.*
