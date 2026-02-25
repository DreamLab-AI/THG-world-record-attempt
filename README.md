# THG World Record Attempt: Autonomous Campaign Generator

**Topshop SS26 - Style Reimagined**

An autonomous AI swarm that transforms a single garment photograph into a complete fashion advertising campaign - static composites across 3 aspect ratios and animated fashion films - using a multi-engine pipeline orchestrated by Claude Flow v3.

## Campaign: Look 6

**Garment:** Cream/beige sleeveless maxi dress with black botanical ink illustration bodice (chrysanthemum, birds, floral line art), diagonal black striped A-line skirt, chain link straps, open back, fitted waist.

## Pipeline Overview

| Phase | Engine | Input | Output | Status |
|-------|--------|-------|--------|--------|
| 1. Base Generation | Flux 2 Dev (ComfyUI) | Garment photo + prompts | 6 hero shots | Complete |
| 2. Style Refinement | Nano Banana (Gemini 2.5 Flash Image) | Phase 1 images + editorial prompts | 6 refined shots | Complete |
| 3. Static Compositing | Programmatic (Pillow/ImageMagick) | Phase 2 images + typography | 18 composites (6 shots x 3 formats) | Complete |
| 4. Animation | Veo 3.1 | Fashion video prompts | 6 animated fashion films | Complete |

## Asset Summary

| Category | Count | Formats |
|----------|-------|---------|
| Base generations | 6 | 512x512 PNG |
| Refined shots | 6 | Various PNG |
| Final composites | 18 | 16:9, 1:1, 9:16 PNG |
| Animated videos | 6 | 16:9 + 9:16 MP4 |
| **Total deliverables** | **36** | |

## Shot Concepts

1. **Hero** - Chrome mannequin on wet brutalist concrete, key light from above
2. **Rain** - Dark urban alley, heavy rainfall, reflections on wet asphalt
3. **Brutalist** - Between massive concrete columns, dramatic overhead shadows
4. **Studio** - Clean studio environment, three-point lighting
5. **Night** - Rain-soaked bus stop, sodium street lighting, car light trails
6. **Back** - Open back detail, chain link straps, botanical ink visible from behind

## Infrastructure

| Component | Specification |
|-----------|--------------|
| GPU | 2x NVIDIA RTX 6000 Ada Generation (48GB each) |
| Multi-GPU | ComfyUI-MultiGPU: UNet on cuda:0, CLIP+VAE on cuda:1 |
| Image Gen (Local) | Flux 2 Dev FP8 + Mistral 3 Small CLIP + Flux2 VAE |
| Image Gen (Cloud) | Gemini 2.5 Flash Image (Nano Banana) |
| Video Gen | Veo 3.1 (predictLongRunning API) |
| Orchestration | Claude Flow v3 hierarchical swarm (6 agents) |
| Container | SaladTechnologies ComfyUI API on Docker |

## Repository Structure

```
docs/                  # PRD, Architecture Flow Diagram, Domain-Driven Design
  prd/                 # Product Requirements Document v3.0
  afd/                 # Architecture Flow Diagram with Mermaid diagrams
  ddd/                 # Domain-Driven Design with bounded contexts
reports/               # Campaign execution reports
configs/               # Brand config, prompts, workflows
  prompts/             # Shot concepts, prompt library, typography research
  workflows/           # Flux2, multi-GPU, Nano Banana, Veo workflow guides
assets/                # All generated campaign assets
  base-gen/            # Phase 1: Flux 2 raw generations
  refined/             # Phase 2: Nano Banana style refinement
  composited/          # Phase 3: Final composites with typography
  animated/            # Phase 4: Veo 3.1 fashion films
  multi-gpu-test/      # Multi-GPU configuration validation
```

## Agents

| Agent | Role | Status |
|-------|------|--------|
| Creative Director | Typography research, shot concepts, prompt engineering | Complete |
| Pipeline Executor | 4-phase pipeline execution across all engines | Running |
| Brand Guardian | QA evaluation of all generated assets | Complete |
| Workflow Researcher | Perplexity research on latest workflows | Complete |

## Brand Identity

- **Palette:** Black (#000000), White (#FFFFFF), Grey (#808080), Chrome accents
- **Typography:** Jost 700 (headlines), Bebas Neue 400 (taglines), Work Sans 400 (body)
- **Tone:** Stark high-contrast, editorial, urban, confident, modern, architectural
- **Environment:** Wet UK city streets, brutalist concrete, overcast diffused lighting

## Technical Highlights

- **Multi-GPU Flux 2**: UNet (17.5GB) on GPU 0, Mistral CLIP (9GB) + VAE on GPU 1
- **Programmatic Text Rendering**: Solved AI text misspelling via Pillow/ImageMagick overlay
- **Veo I2V Discovery**: `predictLongRunning` T2V works; I2V requires Vertex AI or File API upload
- **Video Download**: Veo returns `video.uri` (not `encodedVideo`), requires `-L` for redirects
