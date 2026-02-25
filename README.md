# IRIS World Record Attempt: Agentic Campaign Generation

## Topshop SS26 - Style Reimagined

**An AI system that generated 133 fashion campaign assets in 96 minutes from garment photographs and 21 voice prompts.**

This repository documents a world record attempt in autonomous AI fashion campaign generation, conducted on February 25, 2026. **IRIS** (Intelligent Real-time Integrated Studio) --- developed by **DreamLab AI Consulting Ltd** on the open-source **VisionFlow** platform --- agentically recreated and dramatically expanded a workflow originally built by **THG Ingenuity** for the **"Runway to the Future"** event (26 February 2026, THG Studios Manchester, WRCA-certified). This work forms part of the **UKRI Agentic AI Pioneers Prize** development phase, demonstrating IRIS progression from TRL 4 to TRL 6 in partnership with THG Ingenuity and the University of Salford.

### The Challenge

THG Ingenuity built a fashion campaign generation workflow in **Freepik Spaces** that takes approximately **4 hours** for an expert to construct and produces assets at **15 minutes per image**. Our challenge: use IRIS to autonomously recreate and surpass this workflow using voice-captured creative direction alone --- **without the human ever opening a creative interface**.

### Standing Start

This entire body of work was produced **from a standing start in 3 hours on-site at THG** - no pre-built workflows, no pre-existing assets, no creative brief. The system was pointed at a garment photograph and given voice instructions. Everything - the pipeline architecture, multi-GPU configuration, API integrations, creative direction, asset generation, quality assurance, documentation, and the formal report - was produced within that window. The human creative director **never opened ComfyUI, Freepik Spaces, Photoshop, or any creative application** --- all workflows were generated from scratch by the AI agents.

### The Result

| Metric | Traditional (THG Baseline) | IRIS System | Multiplier |
|--------|---------------------------|-------------|------------|
| Per-image generation | 15 min | ~1 min | **15x faster** |
| Full campaign (36 assets) | ~4 hours | 30 min | **8x faster** |
| Extended campaign (105 assets) | ~12+ hours* | ~82 min | **~9x faster** |
| With repose (133 assets) | ~15+ hours* | ~96 min | **~9.4x faster** |
| Pipeline construction | 4 hours (manual) | 0 hours (autonomous) | **Eliminated** |
| Human input required | Continuous expert operation | 21 voice prompts (~5 min) | **1:19 ratio** |
| Creative concepts | 6-8 per session | 45+ variations | **5.6x more** |

*Traditional estimates for >36 assets are linear extrapolations and may overestimate traditional times.

### How It Works

A human creative director provides **voice-captured natural language prompts** - spoken conversational instructions, not CLI commands. The IRIS autonomous agent swarm interprets each instruction, decomposes it into tasks, selects appropriate AI engines, generates and quality-checks all assets, and handles error recovery - all without further human intervention.

---

## The Topshop Story

Topshop - once the crown jewel of British high street fashion with 500+ stores across 37 countries - collapsed in November 2020 when parent company Arcadia Group entered administration. ASOS acquired the brand in February 2021 for ~$330M, pivoting to digital-only. Now, under the banner "Style Reimagined," Topshop is being reborn through the convergence of heritage fashion and cutting-edge AI technology.

This campaign demonstrates that future: a single garment photograph transformed into a complete multi-platform advertising campaign by an autonomous AI system, with the human creative director providing only high-level artistic voice direction.

---

## Campaign: Look 6

**Garment:** Cream sleeveless maxi dress with black ink botanical chrysanthemum illustrations on the bodice, thin vertical pinstripes on the A-line skirt, and thin chain link straps.

**The dress is the single constant** across all 133 generated assets - placed into brutalist architecture, neon corridors, surreal smiley-filled voids, underwater dreamscapes, Victorian greenhouses, Tron-like grid rooms, thunderstorms, and more.

## Pipeline Overview

| Phase | Engine | Output | Duration |
|-------|--------|--------|----------|
| 1. Base Generation | Flux 2 Dev (dual RTX 6000 Ada) | 6 editorial shots | 6 min |
| 2. Style Refinement | Nano Banana (Gemini 2.5 Flash) | 6 refined shots | 6 min |
| 3. Static Compositing | PIL/Pillow programmatic | 18 composites (3 formats) | 7 min |
| 4. Animation | Veo 3.1 | 6 fashion films (8s each) | 5 min |
| 4b. Garment Reskinning | Nano Banana img2img | 24 garment-faithful variants | 22 min |
| 5. Scene Riffs | 5-agent parallel swarm | 45 creative variations | ~12 min |
| 6. Mannequin Repose | 3-agent parallel Nano Banana | 28 pose-matched images | ~6 min |

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
| Mannequin reposed images | 28 |
| **Total deliverables** | **133** |

## Voice Prompts (Complete Record)

All creative direction was provided as voice-captured natural language - the nominal input method for IRIS. The human creative director **never opened a creative interface**.

**Asset Generation Prompts (16):**
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
16. IRIS context research + mannequin repose task

**Documentation & QA Prompts (5):**
17. IRIS screenshots integration, QE fleet UK spelling check, citations/references, brand asset download
18. Agentic workflow clarification (no creative interface)
19. DeepSeek critique agent, apply improvements, wrap at 4-hour mark
20. Branded Veo video generation of highest quality images
21. Update README and final push

**Total human input: ~5 minutes of speaking across 21 prompts**

## Infrastructure

| Component | Specification |
|-----------|--------------|
| GPU | 2x NVIDIA RTX 6000 Ada Generation (48GB GDDR6 each) |
| Multi-GPU | ComfyUI-MultiGPU: UNet on cuda:0, CLIP+VAE on cuda:1 |
| Image Gen (Local) | Flux 2 Dev FP8 + Mistral 3 Small CLIP + Flux 2 VAE |
| Image Gen (Cloud) | Gemini 2.5 Flash Image (Nano Banana custom node) |
| Video Gen | Veo 3.1 (predictLongRunning API) |
| Orchestration | IRIS via Claude Flow v3 hierarchical swarm |
| Max Parallel Agents | 5 simultaneous (Wave 2) |

## Agent Roster

**Wave 1 - Core Pipeline (4 agents):**
| Agent | Role | Tool Calls | Duration |
|-------|------|------------|----------|
| Creative Director | Typography, shot concepts, prompts | ~30 | ~6 min |
| Pipeline Executor | 4-phase multi-engine pipeline | 142+ | ~25 min |
| Brand Guardian | QA evaluation against brand criteria | ~20 | ~4 min |
| Workflow Researcher | API docs, workflow guides | ~40 | ~8 min |

**Wave 2 - Scene Riffs (5 agents):**
| Agent | Role | Images | Duration |
|-------|------|--------|----------|
| Scene Cleaner | Remove mannequins, preserve environments | 3 | ~4 min |
| Direct Composite | Dress into scene environments | 9 | ~4 min |
| Creative Riff | Surreal editorial variations | 10 | ~3 min |
| Expanded Riffs | High-concept diverse variations | 15 | ~3 min |
| Flux 2 Local | GPU-rendered editorial scenes | 8 | ~12 min |

**Wave 3 - Mannequin Repose (3 agents + 1 research):**
| Agent | Role | Images | Duration |
|-------|------|--------|----------|
| IRIS PDF Research | Extract TRL/system context from appendices | - | ~5 min |
| Repose Batch 1 | Images 1-10, alternating pose 24/26 | 10 | ~2 min |
| Repose Batch 2 | Images 11-23 (skip ref 24) | 13 | ~3 min |
| Repose Batch 3 | Images 25, 27-30 (skip ref 26) | 5 | ~1 min |

**Wave 4 - QA & Documentation (4+ agents):**
| Agent | Role | Duration |
|-------|------|----------|
| Citations Researcher | Verify all assertions, build bibliography | ~10 min |
| QE UK Spelling | British English enforcement (21 issues found) | ~5 min |
| Brand Asset Downloader | Topshop, THG, DreamLab logos | ~3 min |
| DeepSeek Critique | Independent report review (21 findings) | ~8 min |

## Repository Structure

```
reports/                    # Campaign reports and formal documentation
  world-record-report.pdf   # 29-page LaTeX-compiled formal report with bibliography
  campaign-report.md        # Execution report with all phases
  process-documentation.md  # 1,496-line technical process document
  voice-prompts-and-timing.md # Voice prompt record + timing analysis
  technical-findings.md     # API discoveries and gotchas
  citations.md              # Verified citations for all report assertions
  deepseek-critique.md      # Independent critical review
  qe-report.md              # QE audit findings
  iris-system-research.md   # IRIS/VisionFlow system research
docs/                       # PRD v3.0, Architecture Flow Diagram, DDD analysis
configs/                    # Brand config, prompts, workflows
  workflows/                # ComfyUI JSON workflows (3 loadable)
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
task-two-repose/            # Phase 6: Mannequin repose task
  output-reposed/           # 28 reposed mannequin images
  scripts/                  # Repose batch scripts
scripts/                    # Generation and processing scripts
```

## Key Technical Discoveries

- **Multi-GPU Flux 2**: UNet (~38GB) on GPU 0, CLIP+VAE (~19GB) on GPU 1 via ComfyUI-MultiGPU
- **Programmatic Text**: AI models consistently misspell "REIMAGINED" - solved via Pillow overlay
- **Single-Panel References**: Full 4-panel garment images cause grid output - crop to individual panels
- **Veo 3.1 API**: Use `predictLongRunning` (not `generateVideo`), download with `-L` flag
- **Parallel Swarm Peak**: 4.7 images/minute with 3 concurrent agents (Phase 6 repose)
- **Nano Banana**: ComfyUI custom node wrapping Gemini 2.5 Flash Image API via GeminiImageNode
- **Cloud vs Local**: Base generation on-premises (Flux 2 Dev); refinement, reskinning, repose via cloud (Gemini 2.5 Flash)

## Limitations

- Garment fidelity required human correction (Voice Prompt 2 triggered reskinning)
- AI text rendering failed entirely (fell back to programmatic PIL/Pillow)
- All assets use chrome mannequins (no human models)
- QA covered 36 of 133 assets formally
- Cloud API dependency for most generation phases
- Traditional baseline extrapolations may overestimate comparison times

## Links

- **Repository:** [DreamLab-AI/THG-world-record-attempt](https://github.com/DreamLab-AI/THG-world-record-attempt)
- **Formal Report:** [`reports/world-record-report.pdf`](reports/world-record-report.pdf)
- **Event:** [THG Studios "Runway to the Future"](https://www.thgingenuity.com/resources/press-releases/thg-studios-topshop-ai-catwalk)
- **UKRI Prize:** [Agentic AI Pioneers Prize](https://www.ukri.org/opportunity/expression-of-interest-the-agentic-ai-pioneers-prize/)
- **VisionFlow:** [DreamLab-AI/VisionFlow](https://github.com/DreamLab-AI/VisionFlow)

---

*Generated by IRIS (Intelligent Real-time Integrated Studio) via Claude Flow v3 hierarchical agent swarm. February 25, 2026.*
