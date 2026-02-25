# IRIS World Record Attempt: Agentic Campaign Generation

## Topshop SS26 - Style Reimagined

**An AI system that generated 100+ production-ready fashion campaign assets in under 60 minutes from a single garment photograph and 15 voice prompts.**

This repository documents a world record attempt in autonomous AI fashion campaign generation, conducted on February 25, 2026. The **IRIS** (Intelligent Rendering and Imaging System) agentically recreated and dramatically expanded a workflow originally built by **THG Ingenuity** for the **Agentic Catwalk** event in February 2026.

### The Challenge

THG Ingenuity built a fashion campaign generation workflow in **Freepik Spaces** that takes approximately **4 hours** for an expert to construct and produces assets at **15 minutes per image**. Our challenge: use IRIS to autonomously recreate and surpass this workflow using voice-captured creative direction alone.

### Standing Start

This entire body of work was produced **from a standing start in 3 hours on-site at THG** - no pre-built workflows, no pre-existing assets, no creative brief. The system was pointed at a garment photograph and given voice instructions. Everything - the pipeline architecture, multi-GPU configuration, API integrations, creative direction, asset generation, quality assurance, documentation, and this formal report - was produced within that 3-hour window using a mix of local GPU compute and cloud AI services.

### The Result

| Metric | Traditional (THG Baseline) | IRIS System | Multiplier |
|--------|---------------------------|-------------|------------|
| Per-image generation | 15 min | ~1 min | **15x faster** |
| Full campaign (36 assets) | ~4 hours | 30 min | **8x faster** |
| Extended campaign (100+ assets) | ~12+ hours | ~60 min | **12.6x faster** |
| Human input required | Continuous expert operation | 15 voice prompts (~5 min) | **1:12 ratio** |
| Creative concepts | 6-8 per session | 45+ variations | **5.6x more** |

### How It Works

A human creative director provides **voice-captured natural language prompts** - spoken conversational instructions, not CLI commands. The IRIS autonomous agent swarm interprets each instruction, decomposes it into tasks, selects appropriate AI engines, generates and quality-checks all assets, and handles error recovery - all without further human intervention.

---

## The Topshop Story

Topshop - once the crown jewel of British high street fashion with 500+ stores across 37 countries - collapsed in November 2020 when parent company Arcadia Group entered administration. ASOS acquired the brand in February 2021 for ~$330M, pivoting to digital-only. Now, under the banner "Style Reimagined," Topshop is being reborn through the convergence of heritage fashion and cutting-edge AI technology.

This campaign demonstrates that future: a single garment photograph transformed into a complete multi-platform advertising campaign by an autonomous AI system, with the human creative director providing only high-level artistic voice direction.

---

## Campaign: Look 6

**Garment:** Cream sleeveless maxi dress with black ink botanical chrysanthemum illustrations on the bodice, thin vertical pinstripes on the A-line skirt, and thin chain link straps.

**The dress is the single constant** across all 100+ generated assets - placed into brutalist architecture, neon corridors, surreal smiley-filled voids, underwater dreamscapes, Victorian greenhouses, Tron-like grid rooms, thunderstorms, and more.

## Pipeline Overview

| Phase | Engine | Output | Duration |
|-------|--------|--------|----------|
| 1. Base Generation | Flux 2 Dev (dual RTX 6000 Ada) | 6 editorial shots | 6 min |
| 2. Style Refinement | Nano Banana (Gemini 2.5 Flash) | 6 refined shots | 6 min |
| 3. Static Compositing | PIL/Pillow programmatic | 18 composites (3 formats) | 7 min |
| 4. Animation | Veo 3.1 | 6 fashion films (8s each) | 5 min |
| 4b. Garment Reskinning | Nano Banana img2img | 24 garment-faithful variants | 22 min |
| 5. Scene Riffs | 5-agent parallel swarm | 45+ creative variations | ~12 min |

## Scene Riff Creative Expansion

Three surreal scene references drove the creative expansion:

| Scene | Theme | Variations |
|-------|-------|------------|
| White Grid Room | Surreal pop, floating smiley balloons | 3 composites + smiley riffs |
| Neon Corridor | Moody futuristic, vertical light bars | 3 composites + cyberpunk riffs |
| Black Grid Room | Tron-like, neon edge lighting | 3 composites + tech riffs |
| **Creative Riffs** | Architecture, nature, pop art, surreal | 25 high-concept variations |
| **Flux 2 Local** | GPU-rendered editorial scenes | 8 photorealistic renders |

## Asset Summary

| Category | Count |
|----------|-------|
| Base generations | 6 |
| Refined editorial shots | 6 |
| Garment-faithful reskins | 6 |
| Composited images (3 formats each) | 36 |
| Animated fashion films | 6 |
| Cleaned scene backgrounds | 3 |
| Direct scene composites | 9 |
| Creative riff variations | 25 |
| Flux 2 local GPU renders | 8 |
| **Total deliverables** | **100+** |

## Voice Prompts (Complete Record)

All creative direction was provided as voice-captured natural language - the nominal input method for IRIS:

1. Campaign launch (4-agent swarm deployment)
2. Garment fidelity correction (thin vertical pinstripes vs bold diagonal)
3. ComfyUI workflow direction
4. Continuous delivery instruction
5. Documentation and workflow creation
6. Scene riffs creative brief (5-agent parallel swarm)
7. Parallel execution confirmation
8. Push documentation
9. Local GPU clarification
10. Expand creative diversity
11. Metrics and traditional comparison
12. Formal report with Topshop/THG research
13. Include all prompts
14. Inline images with explanations
15. Voice capture clarification

**Total human input: ~5 minutes of speaking across 15 prompts**

## Infrastructure

| Component | Specification |
|-----------|--------------|
| GPU | 2x NVIDIA RTX 6000 Ada Generation (48GB each) |
| Multi-GPU | ComfyUI-MultiGPU: UNet on cuda:0, CLIP+VAE on cuda:1 |
| Image Gen (Local) | Flux 2 Dev FP8 + Mistral 3 Small CLIP + Flux 2 VAE |
| Image Gen (Cloud) | Gemini 2.5 Flash Image (Nano Banana) |
| Video Gen | Veo 3.1 (predictLongRunning API) |
| Orchestration | IRIS via Claude Flow v3 hierarchical swarm |
| Max Parallel Agents | 5 simultaneous (Wave 2) |

## Agent Roster

**Wave 1 - Core Pipeline:**
| Agent | Role | Tool Calls | Duration |
|-------|------|------------|----------|
| Creative Director | Typography, shot concepts, prompts | ~30 | ~6 min |
| Pipeline Executor | 4-phase multi-engine pipeline | 142+ | ~25 min |
| Brand Guardian | QA evaluation against brand criteria | ~20 | ~4 min |
| Workflow Researcher | API docs, workflow guides | ~40 | ~8 min |

**Wave 2 - Scene Riffs:**
| Agent | Role | Images | Duration |
|-------|------|--------|----------|
| Scene Cleaner | Remove mannequins, preserve environments | 3 | ~4 min |
| Direct Composite | Dress into scene environments | 9 | ~4 min |
| Creative Riff | Surreal editorial variations | 10 | ~3 min |
| Expanded Riffs | High-concept diverse variations | 15 | ~3 min |
| Flux 2 Local | GPU-rendered editorial scenes | 8 | ~12 min |

## Repository Structure

```
reports/                    # Campaign reports and formal documentation
  world-record-report.pdf   # 20-page LaTeX-compiled formal report
  campaign-report.md        # Execution report with all phases
  process-documentation.md  # 1,496-line technical process document
  voice-prompts-and-timing.md # Voice prompt record + timing analysis
  technical-findings.md     # API discoveries and gotchas
docs/                       # PRD v3.0, Architecture Flow Diagram, DDD analysis
configs/                    # Brand config, prompts, workflows
  workflows/                # ComfyUI JSON workflows (loadable)
  prompts/                  # Shot concepts, prompt library
input-scenes/               # Scene reference images
assets/
  garment-panels/           # Cropped garment reference panels
  base-gen/                 # Phase 1: Flux 2 raw generations
  refined/                  # Phase 2: Nano Banana refinement
  reskinned/                # Phase 4b: Garment-faithful reskins
  composited/               # Phase 3: Final composites with typography
  reskinned-composited/     # Reskinned composites with typography
  animated/                 # Phase 4: Veo 3.1 fashion films
  scene-riffs/
    cleaned/                # Scene backgrounds with mannequins removed
    composited/             # Direct scene composites (9 images)
    variations/             # Creative riffs + Flux 2 renders (33+ images)
scripts/                    # Generation and processing scripts
```

## Key Technical Discoveries

- **Multi-GPU Flux 2**: UNet (~38GB) on GPU 0, CLIP+VAE (~19GB) on GPU 1 via ComfyUI-MultiGPU
- **Programmatic Text**: AI models consistently misspell "REIMAGINED" - solved via Pillow overlay
- **Single-Panel References**: Full 4-panel garment images cause grid output - crop to individual panels
- **Veo 3.1 API**: Use `predictLongRunning` (not `generateVideo`), download with `-L` flag
- **Parallel Swarm Peak**: 4.4 images/minute with 5 concurrent agents

## Links

- **Repository:** [DreamLab-AI/THG-world-record-attempt](https://github.com/DreamLab-AI/THG-world-record-attempt)
- **Formal Report:** [`reports/world-record-report.pdf`](reports/world-record-report.pdf)

---

*Generated by IRIS (Intelligent Rendering and Imaging System) via Claude Flow v3 hierarchical agent swarm. February 25, 2026.*
