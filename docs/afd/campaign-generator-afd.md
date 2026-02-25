# Architecture Flow Diagram: Autonomous Campaign Generator Swarm

**Version:** 1.0.0
**Date:** 2026-02-25
**Source PRD:** campaign-generator-v3.md
**System:** claude-flow v3 hierarchical agent swarm for Topshop campaign generation

---

## Table of Contents

1. [High-Level System Architecture](#1-high-level-system-architecture)
2. [Agent Communication Topology](#2-agent-communication-topology)
3. [Phase 1: Base Image Generation Flow](#3-phase-1-base-image-generation-flow)
4. [Phase 2: Style Refinement and Scaling Flow](#4-phase-2-style-refinement-and-scaling-flow)
5. [Phase 3: Static Ad Compositing Flow](#5-phase-3-static-ad-compositing-flow)
6. [Phase 4: Animation Flow](#6-phase-4-animation-flow)
7. [QA Feedback Loop Detail](#7-qa-feedback-loop-detail)
8. [Full Pipeline Sequence Diagram](#8-full-pipeline-sequence-diagram)
9. [File System Data Flow](#9-file-system-data-flow)
10. [Error Handling and Fallback Paths](#10-error-handling-and-fallback-paths)
11. [Initialization Sequence](#11-initialization-sequence)
12. [Parallel and Sequential Dependency Map](#12-parallel-and-sequential-dependency-map)

---

## 1. High-Level System Architecture

This diagram shows the complete system boundary, all agents, external services, storage layers, and their interconnections.

```mermaid
graph TB
    subgraph "Client Layer"
        USER["User / Campaign Manager"]
    end

    subgraph "Orchestration Layer (claude-flow v3)"
        CC["Campaign Coordinator<br/>(sparc-coord)"]
        WA["Workflow Architect<br/>(coder)"]
        CD["Creative Director<br/>(researcher)"]
        BG["Brand Guardian<br/>(reviewer)"]
        PO["Pipeline Operator<br/>(coder)"]
        QA["QA Engineer<br/>(tester)"]
    end

    subgraph "External Services"
        COMFY["ComfyUI / Flux2 Dev<br/>comfyui:8188<br/>RTX 6000 Ada 48GB"]
        NB["Nano Banana<br/>gemini-2.5-flash-image"]
        NBP["Nano Banana Pro<br/>gemini-3-pro-image-preview"]
        IMG4["Imagen 4 Ultra<br/>imagen-4.0-ultra-generate-001"]
        VEO["Veo 3.1<br/>veo-3.1-generate-preview"]
        PERP["Perplexity Sonar<br/>api.perplexity.ai"]
        CLAUDE_V["Claude Vision<br/>(Opus 4.6)"]
    end

    subgraph "File System (campaign/)"
        INPUTS["inputs/<br/>Raw garment images"]
        CONFIGS["configs/<br/>Brand, workflows, prompts"]
        PROC["processing/<br/>base-gen, refined,<br/>composited, animated"]
        OUTPUTS["outputs/<br/>static, animated, rejected"]
        STATE["state/<br/>pipeline.json, evaluations/"]
    end

    USER -->|"Upload garment images"| INPUTS
    USER -->|"Trigger pipeline"| CC

    CC -->|"Assign tasks"| WA
    CC -->|"Assign tasks"| CD
    CC -->|"Request evaluation"| BG
    CC -->|"Dispatch API calls"| PO
    CC -->|"Request validation"| QA
    CC -->|"Read/Write state"| STATE

    WA -->|"Build workflow JSON"| CONFIGS
    WA -->|"Submit workflow"| COMFY

    CD -->|"Research typography"| PERP
    CD -->|"Write prompts"| CONFIGS

    BG -->|"Evaluate outputs"| CLAUDE_V
    BG -->|"Feedback to"| WA
    BG -->|"Feedback to"| CD

    PO -->|"Image generation"| COMFY
    PO -->|"Image-to-image"| NB
    PO -->|"Hero shots"| IMG4
    PO -->|"Text composite"| NB
    PO -->|"Animate"| VEO
    PO -->|"Read inputs"| INPUTS
    PO -->|"Write intermediates"| PROC
    PO -->|"Write finals"| OUTPUTS

    QA -->|"Read outputs"| PROC
    QA -->|"Write evaluations"| STATE
    QA -->|"Move approved"| OUTPUTS
    QA -->|"Move rejected"| OUTPUTS

    NBP -.->|"Fallback for NB"| PO
    CLAUDE_V -.->|"Fallback for NB text"| BG
```

---

## 2. Agent Communication Topology

This diagram details the hierarchical agent relationships, message types, and data payloads exchanged between agents.

```mermaid
graph TD
    CC["Campaign Coordinator"]

    CC -->|"TaskAssign: build_workflow<br/>payload: garment_id, phase"| WA["Workflow Architect"]
    CC -->|"TaskAssign: generate_prompts<br/>payload: garment_id, scene_desc"| CD["Creative Director"]
    CC -->|"TaskAssign: evaluate_asset<br/>payload: asset_path, criteria"| BG["Brand Guardian"]
    CC -->|"TaskAssign: execute_api_call<br/>payload: engine, request_body"| PO["Pipeline Operator"]
    CC -->|"TaskAssign: validate_output<br/>payload: asset_path, format_spec"| QA["QA Engineer"]

    WA -->|"WorkflowReady: workflow_json<br/>payload: comfyui_workflow"| PO
    CD -->|"PromptsReady: prompt_set<br/>payload: positive, negative, motion"| WA
    CD -->|"PromptsReady: prompt_set"| PO

    BG -->|"EvalResult: PASS/FAIL<br/>payload: score, feedback[]"| CC
    BG -->|"AdjustRequest: param_changes<br/>payload: prompt_delta, cfg_delta"| WA
    BG -->|"AdjustRequest: prompt_feedback<br/>payload: tone_delta, detail_delta"| CD

    QA -->|"QAResult: PASS/FAIL<br/>payload: checks[], metrics{}"| CC
    QA -->|"TechFail: format_error<br/>payload: error_type, expected, actual"| PO

    PO -->|"AssetReady: file_path<br/>payload: path, engine, metadata"| QA
    PO -->|"AssetReady: file_path"| BG
    PO -->|"APIError: error_detail<br/>payload: engine, status, retry_count"| CC
```

---

## 3. Phase 1: Base Image Generation Flow

Detailed flow for transforming raw garment images into base campaign shots using Flux2 Dev on the local GPU.

```mermaid
flowchart TD
    START_P1["Phase 1 Start"]
    LOAD_IMG["Pipeline Operator:<br/>Load garment from inputs/"]
    GEN_PROMPT["Creative Director:<br/>Generate editorial prompt<br/>(chrome mannequin, urban scene)"]
    BUILD_WF["Workflow Architect:<br/>Build ComfyUI workflow JSON<br/>UNETLoader -> Flux2 Dev FP8<br/>CLIPLoader -> Mistral text encoder<br/>VAELoader -> flux2-vae<br/>KSampler: steps=25, cfg=1.0"]
    SUBMIT_COMFY["Pipeline Operator:<br/>POST /prompt to comfyui:8188"]
    POLL_COMFY["Pipeline Operator:<br/>Poll /history/{prompt_id}"]

    COMFY_DONE{{"ComfyUI<br/>job complete?"}}
    DOWNLOAD["Pipeline Operator:<br/>GET /view?filename=...&type=output<br/>Save to processing/base-gen/"]

    VARIATION_LOOP{{"4-6 variations<br/>generated?"}}
    VARY_SEED["Workflow Architect:<br/>Increment seed,<br/>adjust prompt variation"]

    TECH_QA["QA Engineer:<br/>Resolution >= 512x512?<br/>Format = PNG?"]
    TECH_PASS{{"Technical<br/>QA Pass?"}}
    BRAND_QA["Brand Guardian:<br/>Claude Vision evaluation<br/>- Chrome mannequin present?<br/>- Garment recognizable?<br/>- Urban environment?"]
    BRAND_PASS{{"Brand<br/>QA Pass?"}}
    SAVE_P1["Save approved bases<br/>to processing/base-gen/approved/"]
    END_P1["Phase 1 Complete:<br/>Proceed to Phase 2"]

    RETRY_P1{{"Retry count<br/>< 3?"}}
    ADJUST_P1["Brand Guardian feedback:<br/>Adjust prompts/workflow"]
    REJECT_P1["Escalate to human review"]

    COMFY_FAIL{{"ComfyUI<br/>API error?"}}
    FALLBACK_NB["Fallback:<br/>Pipeline Operator sends<br/>to Nano Banana instead"]

    START_P1 --> LOAD_IMG
    LOAD_IMG --> GEN_PROMPT
    GEN_PROMPT --> BUILD_WF
    BUILD_WF --> SUBMIT_COMFY
    SUBMIT_COMFY --> COMFY_FAIL
    COMFY_FAIL -->|"No"| POLL_COMFY
    COMFY_FAIL -->|"Yes"| FALLBACK_NB
    FALLBACK_NB --> DOWNLOAD
    POLL_COMFY --> COMFY_DONE
    COMFY_DONE -->|"No"| POLL_COMFY
    COMFY_DONE -->|"Yes"| DOWNLOAD
    DOWNLOAD --> VARIATION_LOOP
    VARIATION_LOOP -->|"No"| VARY_SEED
    VARY_SEED --> SUBMIT_COMFY
    VARIATION_LOOP -->|"Yes"| TECH_QA
    TECH_QA --> TECH_PASS
    TECH_PASS -->|"Yes"| BRAND_QA
    TECH_PASS -->|"No"| RETRY_P1
    BRAND_QA --> BRAND_PASS
    BRAND_PASS -->|"Yes"| SAVE_P1
    BRAND_PASS -->|"No"| RETRY_P1
    RETRY_P1 -->|"Yes"| ADJUST_P1
    ADJUST_P1 --> BUILD_WF
    RETRY_P1 -->|"No"| REJECT_P1
    SAVE_P1 --> END_P1
```

---

## 4. Phase 2: Style Refinement and Scaling Flow

Detailed flow for refining base images through Nano Banana image-to-image and generating 16-24 cohesive variations with hero shots via Imagen 4 Ultra.

```mermaid
flowchart TD
    START_P2["Phase 2 Start:<br/>Receive approved bases<br/>from processing/base-gen/"]

    subgraph "Refinement Track (Sequential per image)"
        ENCODE_B64["Pipeline Operator:<br/>Base64 encode base image"]
        NB_REFINE["Pipeline Operator:<br/>POST to Nano Banana<br/>Image-to-image refinement<br/>Chrome fidelity enhancement"]
        NB_RESP{{"Nano Banana<br/>response OK?"}}
        NB_FALLBACK["Fallback:<br/>POST to Nano Banana Pro<br/>gemini-3-pro-image-preview"]
        DECODE_SAVE["Pipeline Operator:<br/>Decode base64 response<br/>Save to processing/refined/"]
    end

    subgraph "Variation Scaling (Parallel)"
        SCALE_NB["Track A: Nano Banana<br/>Vary lighting, angles,<br/>backgrounds<br/>(8-10 variations)"]
        SCALE_FLUX["Track B: Flux2 Dev<br/>Batch generation with<br/>different seeds<br/>(8-10 variations)"]
        SCALE_HERO["Track C: Imagen 4 Ultra<br/>2-3 hero shots<br/>Maximum fidelity"]
    end

    COLLECT["Pipeline Operator:<br/>Collect all variations<br/>(target: 24 total)"]

    QA_BATCH["QA Engineer:<br/>Batch technical validation<br/>- Resolution check<br/>- Format check<br/>- Aspect ratio check"]
    BRAND_BATCH["Brand Guardian:<br/>Batch brand evaluation<br/>- Chrome material quality<br/>- Garment preservation<br/>- Editorial tone consistency"]

    FILTER{{">=16 variations<br/>pass QA?"}}
    SAVE_P2["Move passing assets<br/>to processing/refined/approved/"]
    END_P2["Phase 2 Complete:<br/>Proceed to Phase 3"]

    REGEN["Regenerate failing<br/>variations with<br/>adjusted parameters"]
    REGEN_COUNT{{"Total attempts<br/>< 3?"}}
    ESCALATE["Escalate:<br/>Proceed with available<br/>passing assets"]

    START_P2 --> ENCODE_B64
    ENCODE_B64 --> NB_REFINE
    NB_REFINE --> NB_RESP
    NB_RESP -->|"Yes"| DECODE_SAVE
    NB_RESP -->|"No"| NB_FALLBACK
    NB_FALLBACK --> DECODE_SAVE

    DECODE_SAVE --> SCALE_NB
    DECODE_SAVE --> SCALE_FLUX
    DECODE_SAVE --> SCALE_HERO

    SCALE_NB --> COLLECT
    SCALE_FLUX --> COLLECT
    SCALE_HERO --> COLLECT

    COLLECT --> QA_BATCH
    QA_BATCH --> BRAND_BATCH
    BRAND_BATCH --> FILTER
    FILTER -->|"Yes"| SAVE_P2
    FILTER -->|"No"| REGEN
    REGEN --> REGEN_COUNT
    REGEN_COUNT -->|"Yes"| SCALE_NB
    REGEN_COUNT -->|"No"| ESCALATE
    ESCALATE --> SAVE_P2
    SAVE_P2 --> END_P2
```

---

## 5. Phase 3: Static Ad Compositing Flow

Detailed flow for typography overlay, negative space analysis, and multi-aspect-ratio adaptation.

```mermaid
flowchart TD
    START_P3["Phase 3 Start:<br/>Load approved refined images<br/>from processing/refined/"]

    NEG_SPACE["Brand Guardian:<br/>Send image to Claude Vision<br/>'Identify largest negative space<br/>for text overlay. Return coords<br/>as % of image dimensions.'"]
    COORDS["Receive: negative space<br/>coordinates {x%, y%, w%, h%}"]

    PROMPT_TEXT["Creative Director:<br/>Select text content<br/>STYLE REIMAGINED /<br/>NEW COLLECTION /<br/>TOPSHOP SS26"]

    subgraph "Text Compositing (Primary Route)"
        NB_TEXT["Pipeline Operator:<br/>POST to Nano Banana<br/>Image + text overlay instruction<br/>placed in identified negative space"]
        NB_TEXT_OK{{"Text quality<br/>acceptable?"}}
    end

    subgraph "Text Compositing (Fallback Route)"
        COMFY_TEXT["Workflow Architect:<br/>Build ComfyUI workflow with<br/>text overlay nodes +<br/>downloaded font files"]
        COMFY_EXEC["Pipeline Operator:<br/>Execute ComfyUI text workflow"]
    end

    subgraph "Aspect Ratio Adaptation (Parallel)"
        AR_16_9["Generate 16:9<br/>(Landscape)<br/>YouTube / Display"]
        AR_1_1["Generate 1:1<br/>(Square)<br/>Instagram Feed"]
        AR_9_16["Generate 9:16<br/>(Portrait)<br/>Stories / Reels / TikTok"]
    end

    TECH_QA_P3["QA Engineer:<br/>- Text legible at 50% scale?<br/>- Correct aspect ratio (1% tol)?<br/>- File size within limits?<br/>- PNG format?"]
    BRAND_QA_P3["Brand Guardian:<br/>- Text in clean negative space?<br/>- No garment overlap?<br/>- Topshop typography match?<br/>- High-contrast text?"]

    P3_PASS{{"QA Pass?"}}
    SAVE_P3["Save to processing/composited/"]
    END_P3["Phase 3 Complete:<br/>Proceed to Phase 4"]

    P3_RETRY{{"Retry < 3?"}}
    P3_ADJUST["Adjust text placement,<br/>font size, or compositing engine"]
    P3_REJECT["Move to outputs/rejected/<br/>with rejection reason"]

    START_P3 --> NEG_SPACE
    NEG_SPACE --> COORDS
    COORDS --> PROMPT_TEXT
    PROMPT_TEXT --> NB_TEXT
    NB_TEXT --> NB_TEXT_OK
    NB_TEXT_OK -->|"Yes"| AR_16_9
    NB_TEXT_OK -->|"Yes"| AR_1_1
    NB_TEXT_OK -->|"Yes"| AR_9_16
    NB_TEXT_OK -->|"No"| COMFY_TEXT
    COMFY_TEXT --> COMFY_EXEC
    COMFY_EXEC --> AR_16_9
    COMFY_EXEC --> AR_1_1
    COMFY_EXEC --> AR_9_16

    AR_16_9 --> TECH_QA_P3
    AR_1_1 --> TECH_QA_P3
    AR_9_16 --> TECH_QA_P3

    TECH_QA_P3 --> BRAND_QA_P3
    BRAND_QA_P3 --> P3_PASS
    P3_PASS -->|"Yes"| SAVE_P3
    P3_PASS -->|"No"| P3_RETRY
    P3_RETRY -->|"Yes"| P3_ADJUST
    P3_ADJUST --> NB_TEXT
    P3_RETRY -->|"No"| P3_REJECT
    SAVE_P3 --> END_P3
```

---

## 6. Phase 4: Animation Flow

Detailed flow for converting static composited ads into 8-second animated videos using Veo 3.1 with long-running operation polling.

```mermaid
flowchart TD
    START_P4["Phase 4 Start:<br/>Load approved composited ads<br/>from processing/composited/"]

    MOTION_SCRIPT["Creative Director:<br/>Generate Veo motion script<br/>'Subtle chrome shimmer,<br/>gentle rain particles,<br/>static text overlay,<br/>locked camera'"]

    subgraph "Per Aspect Ratio (Parallel)"
        direction TB
        subgraph "16:9 Track"
            ENCODE_16["Base64 encode<br/>16:9 composited ad"]
            VEO_16["Pipeline Operator:<br/>POST predictLongRunning<br/>aspectRatio: 16:9<br/>duration: 8s, res: 1080p"]
            POLL_16["Poll GET /v1beta/{op_name}<br/>every 10 seconds"]
            DONE_16{{"done: true?"}}
            DL_16["Download video from<br/>generatedSamples[].video.uri"]
        end

        subgraph "1:1 Track"
            ENCODE_1["Base64 encode<br/>1:1 composited ad"]
            VEO_1["Pipeline Operator:<br/>POST predictLongRunning<br/>aspectRatio: 1:1<br/>duration: 8s"]
            POLL_1["Poll GET /v1beta/{op_name}<br/>every 10 seconds"]
            DONE_1{{"done: true?"}}
            DL_1["Download video from<br/>generatedSamples[].video.uri"]
        end

        subgraph "9:16 Track"
            ENCODE_9["Base64 encode<br/>9:16 composited ad"]
            VEO_9["Pipeline Operator:<br/>POST predictLongRunning<br/>aspectRatio: 9:16<br/>duration: 8s"]
            POLL_9["Poll GET /v1beta/{op_name}<br/>every 10 seconds"]
            DONE_9{{"done: true?"}}
            DL_9["Download video from<br/>generatedSamples[].video.uri"]
        end
    end

    SAVE_ANIM["Pipeline Operator:<br/>Save all videos to<br/>processing/animated/"]

    QA_VIDEO["QA Engineer:<br/>- MP4 format?<br/>- Resolution >= 1080p (16:9)?<br/>- Duration = 8s?<br/>- File size < 50MB?<br/>- Loop seamlessness check"]

    BRAND_VIDEO["Brand Guardian (Claude Vision):<br/>- Text remains static?<br/>- Chrome reflections animate?<br/>- Ambient motion subtle?<br/>- Editorial quality maintained?"]

    V_PASS{{"QA Pass?"}}
    SAVE_FINAL["Move to outputs/animated/"]
    END_P4["Phase 4 Complete"]

    V_RETRY{{"Retry < 3?"}}
    V_ADJUST["Adjust motion script:<br/>reduce motion intensity,<br/>reinforce text lock directive"]
    V_REJECT["Move to outputs/rejected/<br/>with frame-by-frame notes"]

    VEO_FAIL{{"Veo 3.1<br/>API error?"}}
    VEO_FALLBACK["Fallback:<br/>Retry with Veo 3.0 Fast<br/>or reduce resolution"]

    START_P4 --> MOTION_SCRIPT

    MOTION_SCRIPT --> ENCODE_16
    MOTION_SCRIPT --> ENCODE_1
    MOTION_SCRIPT --> ENCODE_9

    ENCODE_16 --> VEO_16
    VEO_16 --> VEO_FAIL
    VEO_FAIL -->|"No"| POLL_16
    VEO_FAIL -->|"Yes"| VEO_FALLBACK
    VEO_FALLBACK --> POLL_16
    POLL_16 --> DONE_16
    DONE_16 -->|"No"| POLL_16
    DONE_16 -->|"Yes"| DL_16

    ENCODE_1 --> VEO_1
    VEO_1 --> POLL_1
    POLL_1 --> DONE_1
    DONE_1 -->|"No"| POLL_1
    DONE_1 -->|"Yes"| DL_1

    ENCODE_9 --> VEO_9
    VEO_9 --> POLL_9
    POLL_9 --> DONE_9
    DONE_9 -->|"No"| POLL_9
    DONE_9 -->|"Yes"| DL_9

    DL_16 --> SAVE_ANIM
    DL_1 --> SAVE_ANIM
    DL_9 --> SAVE_ANIM

    SAVE_ANIM --> QA_VIDEO
    QA_VIDEO --> BRAND_VIDEO
    BRAND_VIDEO --> V_PASS
    V_PASS -->|"Yes"| SAVE_FINAL
    V_PASS -->|"No"| V_RETRY
    V_RETRY -->|"Yes"| V_ADJUST
    V_ADJUST --> VEO_16
    V_RETRY -->|"No"| V_REJECT
    SAVE_FINAL --> END_P4
```

---

## 7. QA Feedback Loop Detail

This diagram isolates the QA feedback loop that applies uniformly to every asset across all four phases.

```mermaid
flowchart TD
    ASSET_IN["Asset Generated<br/>(any phase output)"]

    subgraph "Stage 1: Technical Validation (QA Engineer)"
        TV_FORMAT["Check file format<br/>(PNG for images, MP4 for video)"]
        TV_RES["Check resolution<br/>>= minimum per format"]
        TV_AR["Check aspect ratio<br/>within 1% tolerance of target"]
        TV_SIZE["Check file size<br/>within platform limits"]
        TV_LOOP["Video only: check<br/>loop seamlessness"]
        TV_TEXT["Static only: check<br/>text legibility at 50% scale"]
    end

    TV_RESULT{{"Technical<br/>Validation<br/>PASS?"}}

    subgraph "Stage 2: Brand Compliance (Brand Guardian via Claude Vision)"
        BC_CHROME["1. Is mannequin chrome/metallic?"]
        BC_GARMENT["2. Does garment match input?<br/>(approximation acceptable)"]
        BC_TEXT_POS["3. Is text in clean negative space?<br/>No garment overlap?"]
        BC_PALETTE["4. High-contrast black/white/<br/>grey/metallic palette?"]
        BC_EDITORIAL["5. Meets editorial fashion<br/>campaign standards?"]
    end

    BC_RESULT{{"Brand<br/>Compliance<br/>PASS?<br/>(all 5 = Yes)"}}

    PASS_PATH["PASS:<br/>Move asset to<br/>outputs/static/ or outputs/animated/"]

    FAIL_PATH["FAIL:<br/>Extract specific feedback"]

    RETRY_CHECK{{"retry_count<br/>< 3?"}}

    subgraph "Retry Path"
        FEEDBACK_WA["Brand Guardian -> Workflow Architect:<br/>Adjust workflow parameters<br/>(cfg, steps, sampler settings)"]
        FEEDBACK_CD["Brand Guardian -> Creative Director:<br/>Adjust prompts<br/>(tone, detail, emphasis)"]
        FEEDBACK_PO["QA Engineer -> Pipeline Operator:<br/>Fix technical issue<br/>(resize, reformat, re-encode)"]
        RESUBMIT["Pipeline Operator:<br/>Resubmit to engine<br/>with adjusted parameters"]
    end

    ESCALATE["ESCALATE:<br/>Move to outputs/rejected/<br/>Log rejection reason in<br/>state/evaluations/<br/>Flag for human review"]

    EVAL_LOG["Write evaluation report<br/>to state/evaluations/<br/>{asset_id}_eval.json"]

    ASSET_IN --> TV_FORMAT
    TV_FORMAT --> TV_RES
    TV_RES --> TV_AR
    TV_AR --> TV_SIZE
    TV_SIZE --> TV_LOOP
    TV_LOOP --> TV_TEXT
    TV_TEXT --> TV_RESULT

    TV_RESULT -->|"PASS"| BC_CHROME
    TV_RESULT -->|"FAIL"| FAIL_PATH

    BC_CHROME --> BC_GARMENT
    BC_GARMENT --> BC_TEXT_POS
    BC_TEXT_POS --> BC_PALETTE
    BC_PALETTE --> BC_EDITORIAL
    BC_EDITORIAL --> BC_RESULT

    BC_RESULT -->|"PASS"| PASS_PATH
    BC_RESULT -->|"FAIL"| FAIL_PATH

    FAIL_PATH --> EVAL_LOG
    EVAL_LOG --> RETRY_CHECK

    RETRY_CHECK -->|"Yes"| FEEDBACK_WA
    RETRY_CHECK -->|"Yes"| FEEDBACK_CD
    RETRY_CHECK -->|"Yes"| FEEDBACK_PO
    FEEDBACK_WA --> RESUBMIT
    FEEDBACK_CD --> RESUBMIT
    FEEDBACK_PO --> RESUBMIT
    RESUBMIT --> ASSET_IN

    RETRY_CHECK -->|"No"| ESCALATE

    PASS_PATH --> EVAL_LOG
```

---

## 8. Full Pipeline Sequence Diagram

This sequence diagram shows the complete pipeline lifecycle from user trigger through all four phases, including agent interactions, API calls, and QA gates.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant CC as Campaign Coordinator
    participant CD as Creative Director
    participant WA as Workflow Architect
    participant PO as Pipeline Operator
    participant BG as Brand Guardian
    participant QA as QA Engineer
    participant Flux as ComfyUI/Flux2
    participant NB as Nano Banana
    participant NBP as Nano Banana Pro
    participant IMG4 as Imagen 4 Ultra
    participant Veo as Veo 3.1
    participant Perp as Perplexity
    participant CV as Claude Vision
    participant FS as File System

    rect rgb(40, 40, 60)
        Note over CC,FS: INITIALIZATION SEQUENCE
        User->>CC: Trigger pipeline (garment images in inputs/)
        CC->>PO: Validate infrastructure
        PO->>Flux: GET /system_stats
        Flux-->>PO: 200 OK (RTX 6000 Ada ready)
        PO->>NB: POST test prompt
        NB-->>PO: 200 OK
        PO->>Veo: POST test prompt
        Veo-->>PO: 200 OK (operation started)
        PO->>Perp: POST test query
        Perp-->>PO: 200 OK
        PO-->>CC: Infrastructure validated

        CC->>CD: Research typography
        CD->>Perp: POST "Topshop brand typography font family"
        Perp-->>CD: Futura/Gotham/Proxima Nova matches
        CD->>FS: Write configs/topshop.json

        CC->>WA: Build workflow templates
        WA->>FS: Write configs/workflows/*.json
        WA-->>CC: Templates ready

        CC->>CD: Generate prompt library
        CD->>FS: Write configs/prompts/*.json
        CD-->>CC: Prompts ready
    end

    rect rgb(50, 30, 30)
        Note over CC,FS: PHASE 1 - BASE IMAGE GENERATION (Flux2 Dev Local GPU)
        CC->>FS: Read inputs/ (garment images)
        CC->>CD: Generate editorial prompts for garment
        CD-->>CC: Prompt set (positive + negative)

        CC->>WA: Build Flux2 ComfyUI workflow
        WA-->>CC: Workflow JSON (UNET + CLIP + VAE + KSampler)

        loop 4-6 variations per garment
            CC->>PO: Execute generation (workflow + seed N)
            PO->>Flux: POST /prompt {workflow_json}
            Flux-->>PO: prompt_id
            loop Poll until complete
                PO->>Flux: GET /history/{prompt_id}
                Flux-->>PO: status (running/complete)
            end
            PO->>Flux: GET /view?filename=...&type=output
            Flux-->>PO: PNG image data
            PO->>FS: Save to processing/base-gen/
        end

        CC->>QA: Validate base images (batch)
        QA->>FS: Read processing/base-gen/*
        QA-->>CC: Technical QA results

        CC->>BG: Evaluate brand compliance (batch)
        BG->>CV: Analyze chrome mannequin + garment fidelity
        CV-->>BG: Evaluation scores
        BG-->>CC: PASS/FAIL per image with feedback

        alt Any FAIL and retry < 3
            CC->>WA: Adjust workflow per BG feedback
            CC->>CD: Adjust prompts per BG feedback
            Note over CC: Re-enter generation loop
        end
    end

    rect rgb(30, 50, 30)
        Note over CC,FS: PHASE 2 - STYLE REFINEMENT & SCALING (Nano Banana + Imagen 4)
        CC->>PO: Refine approved bases via Nano Banana

        loop Per approved base image
            PO->>FS: Read base image, encode base64
            PO->>NB: POST image-to-image (chrome refinement)
            alt Nano Banana error
                PO->>NBP: POST fallback to Nano Banana Pro
                NBP-->>PO: Refined image (base64)
            else Success
                NB-->>PO: Refined image (base64)
            end
            PO->>FS: Decode and save to processing/refined/
        end

        par Variation Scaling (Parallel Tracks)
            Note over PO,NB: Track A: Nano Banana variations (8-10)
            loop 8-10 Nano Banana variations
                PO->>NB: POST varied prompts (lighting/angle/bg)
                NB-->>PO: Variation image
            end
        and
            Note over PO,Flux: Track B: Flux2 batch variations (8-10)
            loop 8-10 Flux2 variations
                PO->>Flux: POST /prompt (different seeds)
                Flux-->>PO: Variation image
            end
        and
            Note over PO,IMG4: Track C: Imagen 4 hero shots (2-3)
            loop 2-3 Imagen 4 hero shots
                PO->>IMG4: POST predict (maximum fidelity)
                IMG4-->>PO: Hero image
            end
        end

        PO->>FS: Save all 24 variations to processing/refined/

        CC->>QA: Batch technical validation
        CC->>BG: Batch brand evaluation
        BG->>CV: Analyze all variations
        CV-->>BG: Per-image evaluation

        alt >= 16 pass
            BG-->>CC: Sufficient variations approved
        else < 16 pass and retry < 3
            BG-->>CC: Regenerate failing variations
            Note over CC: Re-enter scaling loop
        else < 16 pass and retry >= 3
            BG-->>CC: Proceed with available passing assets
        end
    end

    rect rgb(30, 30, 50)
        Note over CC,FS: PHASE 3 - STATIC AD COMPOSITING (Nano Banana + Claude Vision)
        loop Per approved refined image
            CC->>BG: Analyze negative space
            BG->>CV: "Identify largest negative space for text overlay"
            CV-->>BG: Coordinates {x%, y%, w%, h%}

            CC->>CD: Select typography content
            CD-->>CC: "STYLE REIMAGINED" / "NEW COLLECTION" / "TOPSHOP SS26"

            CC->>PO: Composite text via Nano Banana
            PO->>NB: POST image + text overlay instruction
            NB-->>PO: Composited image

            alt Text quality insufficient
                CC->>WA: Build ComfyUI text overlay workflow
                WA-->>PO: Text workflow JSON
                PO->>Flux: POST /prompt (text overlay nodes)
                Flux-->>PO: Composited image
            end

            par Aspect Ratio Adaptation (Parallel)
                PO->>NB: Generate 16:9 version
                NB-->>PO: 16:9 ad
            and
                PO->>NB: Generate 1:1 version
                NB-->>PO: 1:1 ad
            and
                PO->>NB: Generate 9:16 version
                NB-->>PO: 9:16 ad
            end

            PO->>FS: Save all formats to processing/composited/
        end

        CC->>QA: Validate text legibility + aspect ratios
        CC->>BG: Validate text placement + brand compliance
        BG->>CV: Analyze text overlay quality
        CV-->>BG: Evaluation results
        BG-->>CC: PASS/FAIL per asset
    end

    rect rgb(50, 40, 30)
        Note over CC,FS: PHASE 4 - ANIMATION (Veo 3.1)
        CC->>CD: Generate Veo motion scripts
        CD-->>CC: Motion scripts (shimmer, rain, locked camera)

        par Animate All Aspect Ratios (Parallel)
            PO->>FS: Encode 16:9 composited ad (base64)
            PO->>Veo: POST predictLongRunning (16:9, 8s, 1080p)
            Veo-->>PO: operation_name
            loop Poll every 10s
                PO->>Veo: GET /v1beta/{operation_name}
                Veo-->>PO: {done: false} / {done: true, video_uri}
            end
            PO->>Veo: Download video from URI
            Veo-->>PO: MP4 video data
        and
            PO->>Veo: POST predictLongRunning (1:1, 8s)
            Note over PO,Veo: Same poll/download cycle
        and
            PO->>Veo: POST predictLongRunning (9:16, 8s)
            Note over PO,Veo: Same poll/download cycle
        end

        PO->>FS: Save all videos to processing/animated/

        CC->>QA: Validate video specs (format, duration, size)
        QA-->>CC: Technical results

        CC->>BG: Evaluate video brand compliance
        BG->>CV: Analyze video frames (text static? chrome animates?)
        CV-->>BG: Video evaluation
        BG-->>CC: PASS/FAIL per video

        alt PASS
            PO->>FS: Move to outputs/animated/
        else FAIL and retry < 3
            CC->>CD: Adjust motion script
            Note over CC: Re-enter animation loop
        else FAIL and retry >= 3
            PO->>FS: Move to outputs/rejected/
        end
    end

    rect rgb(40, 50, 40)
        Note over CC,FS: PIPELINE COMPLETE
        CC->>FS: Update state/pipeline.json (status: complete)
        CC->>FS: Write final evaluation summary to state/evaluations/
        CC-->>User: Pipeline complete. Assets in outputs/
    end
```

---

## 9. File System Data Flow

This diagram traces the complete lifecycle of data through the file system, from raw inputs to final approved outputs.

```mermaid
flowchart LR
    subgraph "INPUTS"
        RAW["inputs/<br/>garment_001.png<br/>garment_002.png<br/>..."]
    end

    subgraph "CONFIGS (Read-Only at Runtime)"
        BRAND["configs/topshop.json<br/>(brand identity)"]
        WF["configs/workflows/<br/>flux2_base.json<br/>nb_refine.json<br/>veo_animate.json"]
        PROMPTS["configs/prompts/<br/>editorial.json<br/>motion.json<br/>typography.json"]
    end

    subgraph "PROCESSING (Intermediate)"
        P1["processing/base-gen/<br/>base_001_v1.png<br/>base_001_v2.png<br/>...<br/>base_001_v6.png"]
        P2["processing/refined/<br/>refined_001_v01.png<br/>...<br/>refined_001_v24.png<br/>hero_001_01.png"]
        P3["processing/composited/<br/>ad_001_16x9_v01.png<br/>ad_001_1x1_v01.png<br/>ad_001_9x16_v01.png"]
        P4["processing/animated/<br/>ad_001_16x9.mp4<br/>ad_001_1x1.mp4<br/>ad_001_9x16.mp4"]
    end

    subgraph "OUTPUTS (Final)"
        STATIC["outputs/static/<br/>Approved static ads<br/>(16:9, 1:1, 9:16 PNGs)"]
        ANIM["outputs/animated/<br/>Approved animated ads<br/>(16:9, 1:1, 9:16 MP4s)"]
        REJECTED["outputs/rejected/<br/>Failed QA assets +<br/>rejection_reason.json"]
    end

    subgraph "STATE"
        PIPE_STATE["state/pipeline.json<br/>{phase, progress,<br/>retry_counts, timestamps}"]
        EVALS["state/evaluations/<br/>{asset_id}_eval.json<br/>{scores, feedback,<br/>pass_fail, retry_history}"]
    end

    RAW -->|"Phase 1: Load"| P1
    BRAND -->|"All phases: Brand rules"| P1
    WF -->|"Phase 1: Flux2 workflow"| P1
    PROMPTS -->|"Phase 1: Editorial prompts"| P1

    P1 -->|"Phase 2: Base images"| P2
    WF -->|"Phase 2: Refinement templates"| P2
    PROMPTS -->|"Phase 2: Variation prompts"| P2

    P2 -->|"Phase 3: Refined images"| P3
    PROMPTS -->|"Phase 3: Typography content"| P3

    P3 -->|"Phase 4: Composited stills"| P4
    PROMPTS -->|"Phase 4: Motion scripts"| P4
    WF -->|"Phase 4: Veo templates"| P4

    P3 -->|"QA PASS"| STATIC
    P4 -->|"QA PASS"| ANIM
    P1 -->|"QA FAIL (max retries)"| REJECTED
    P2 -->|"QA FAIL (max retries)"| REJECTED
    P3 -->|"QA FAIL (max retries)"| REJECTED
    P4 -->|"QA FAIL (max retries)"| REJECTED

    P1 -.->|"Log evaluations"| EVALS
    P2 -.->|"Log evaluations"| EVALS
    P3 -.->|"Log evaluations"| EVALS
    P4 -.->|"Log evaluations"| EVALS
    CC_STATE["All phases"] -.->|"Update progress"| PIPE_STATE
```

---

## 10. Error Handling and Fallback Paths

This diagram documents every error condition, its fallback path, and the escalation chain.

```mermaid
flowchart TD
    subgraph "ComfyUI / Flux2 Errors"
        COMFY_ERR["ComfyUI API unreachable<br/>or workflow execution error"]
        COMFY_F1["Fallback 1: Retry with<br/>exponential backoff (3 attempts)"]
        COMFY_F2["Fallback 2: Route to<br/>Nano Banana for base gen"]
        COMFY_F3["Fallback 3: Route to<br/>Imagen 4 Fast for batch gen"]
        COMFY_ESC["Escalate: Log error,<br/>mark garment as blocked,<br/>continue with other garments"]

        COMFY_ERR --> COMFY_F1
        COMFY_F1 -->|"Still failing"| COMFY_F2
        COMFY_F2 -->|"Still failing"| COMFY_F3
        COMFY_F3 -->|"Still failing"| COMFY_ESC
    end

    subgraph "Nano Banana Errors"
        NB_ERR["Nano Banana API error<br/>(rate limit, 500, timeout)"]
        NB_F1["Fallback 1: Retry with<br/>exponential backoff (3 attempts)"]
        NB_F2["Fallback 2: Route to<br/>Nano Banana Pro<br/>(gemini-3-pro-image-preview)"]
        NB_F3["Fallback 3: Route to<br/>Flux2 Dev local for gen,<br/>Claude Vision for eval"]
        NB_ESC["Escalate: Log error,<br/>proceed with available assets"]

        NB_ERR --> NB_F1
        NB_F1 -->|"Still failing"| NB_F2
        NB_F2 -->|"Still failing"| NB_F3
        NB_F3 -->|"Still failing"| NB_ESC
    end

    subgraph "Imagen 4 Ultra Errors"
        IMG_ERR["Imagen 4 API error<br/>(quota, auth, timeout)"]
        IMG_F1["Fallback 1: Retry with<br/>exponential backoff (3 attempts)"]
        IMG_F2["Fallback 2: Route to<br/>Nano Banana Pro for hero shots"]
        IMG_F3["Fallback 3: Use best<br/>Flux2 Dev output as hero"]
        IMG_ESC["Escalate: Skip hero shots,<br/>proceed with standard assets"]

        IMG_ERR --> IMG_F1
        IMG_F1 -->|"Still failing"| IMG_F2
        IMG_F2 -->|"Still failing"| IMG_F3
        IMG_F3 -->|"Still failing"| IMG_ESC
    end

    subgraph "Veo 3.1 Errors"
        VEO_ERR["Veo 3.1 API error<br/>(timeout, generation fail,<br/>content filter)"]
        VEO_F1["Fallback 1: Retry with<br/>adjusted prompt (remove<br/>flagged terms)"]
        VEO_F2["Fallback 2: Route to<br/>Veo 3.0 Fast<br/>(lower quality, faster)"]
        VEO_F3["Fallback 3: Reduce resolution<br/>or duration (4s instead of 8s)"]
        VEO_ESC["Escalate: Skip animation<br/>for this asset, deliver<br/>static-only version"]

        VEO_ERR --> VEO_F1
        VEO_F1 -->|"Still failing"| VEO_F2
        VEO_F2 -->|"Still failing"| VEO_F3
        VEO_F3 -->|"Still failing"| VEO_ESC
    end

    subgraph "Perplexity Errors"
        PERP_ERR["Perplexity API error"]
        PERP_F1["Fallback: Use hardcoded<br/>typography defaults<br/>(Futura/Gotham)"]

        PERP_ERR --> PERP_F1
    end

    subgraph "QA Loop Exhaustion"
        QA_EXHAUST["Asset fails QA<br/>3 times consecutively"]
        QA_F1["Move to outputs/rejected/<br/>with detailed rejection log"]
        QA_F2["Write evaluation to<br/>state/evaluations/"]
        QA_F3["Campaign Coordinator:<br/>Flag for human review<br/>in pipeline.json"]

        QA_EXHAUST --> QA_F1
        QA_F1 --> QA_F2
        QA_F2 --> QA_F3
    end

    subgraph "Pipeline State Recovery"
        STATE_ERR["Container restart or<br/>unexpected termination"]
        STATE_F1["Read state/pipeline.json<br/>to determine last<br/>completed phase"]
        STATE_F2["Resume from last<br/>checkpoint, skip<br/>completed assets"]
        STATE_F3["Re-validate all<br/>processing/ intermediates<br/>before continuing"]

        STATE_ERR --> STATE_F1
        STATE_F1 --> STATE_F2
        STATE_F2 --> STATE_F3
    end
```

---

## 11. Initialization Sequence

This diagram shows the detailed startup sequence including infrastructure validation, configuration loading, and the transition to the main pipeline.

```mermaid
sequenceDiagram
    autonumber
    participant User
    participant CC as Campaign Coordinator
    participant PO as Pipeline Operator
    participant CD as Creative Director
    participant WA as Workflow Architect
    participant BG as Brand Guardian
    participant Flux as ComfyUI/Flux2
    participant NB as Nano Banana
    participant Veo as Veo 3.1
    participant Perp as Perplexity
    participant FS as File System

    Note over CC: STEP 1: VALIDATE INFRASTRUCTURE

    par Infrastructure Health Checks
        CC->>PO: Ping ComfyUI
        PO->>Flux: GET /system_stats
        Flux-->>PO: {gpu: "RTX 6000 Ada", vram: "48GB"}
    and
        CC->>PO: Test Nano Banana
        PO->>NB: POST generateContent (test prompt)
        NB-->>PO: 200 OK
    and
        CC->>PO: Test Veo 3.1
        PO->>Veo: POST predictLongRunning (test)
        Veo-->>PO: 200 OK (operation created)
    and
        CC->>PO: Test Perplexity
        PO->>Perp: POST chat/completions (test query)
        Perp-->>PO: 200 OK
    and
        CC->>PO: Verify input images
        PO->>FS: List inputs/*.png
        FS-->>PO: [garment_001.png, ...]
    end

    PO-->>CC: All services operational, N garment images found

    alt Any service unreachable
        CC-->>User: ERROR: Service X unavailable. Details in state/pipeline.json
        CC->>FS: Write error state to state/pipeline.json
    end

    Note over CC: STEP 2: RESEARCH TYPOGRAPHY

    CC->>CD: Research Topshop typography
    CD->>Perp: "Topshop brand typography font family geometric sans-serif closest match"
    Perp-->>CD: {fonts: ["Futura", "Gotham", "Proxima Nova"], reasoning: "..."}
    CD->>FS: Update configs/topshop.json with typography results

    Note over CC: STEP 3: LOAD BRAND CONFIG

    CC->>FS: Read configs/topshop.json
    FS-->>CC: {palette, typography, tone, identity_rules}
    CC->>BG: Initialize brand evaluation criteria
    CC->>CD: Initialize prompt generation context

    Note over CC: STEP 4: BUILD WORKFLOW TEMPLATES

    CC->>WA: Create Flux2 base generation workflow
    WA->>FS: Write configs/workflows/flux2_base_gen.json
    CC->>WA: Create Nano Banana refinement templates
    WA->>FS: Write configs/workflows/nb_refinement.json
    CC->>WA: Create Veo animation templates
    WA->>FS: Write configs/workflows/veo_animation.json

    CC->>CD: Build prompt template library
    CD->>FS: Write configs/prompts/editorial_prompts.json
    CD->>FS: Write configs/prompts/motion_scripts.json
    CD->>FS: Write configs/prompts/typography_content.json

    Note over CC: STEP 5: BEGIN PIPELINE

    CC->>FS: Write state/pipeline.json {status: "running", phase: 1}
    CC-->>User: Initialization complete. Beginning Phase 1.
    Note over CC: Transition to Phase 1 (see Section 3)
```

---

## 12. Parallel and Sequential Dependency Map

This diagram maps all operations in the pipeline, identifying which can run in parallel and which have hard sequential dependencies.

```mermaid
graph LR
    subgraph "INIT (Sequential)"
        I1["Validate<br/>Infrastructure"]
        I2["Research<br/>Typography"]
        I3["Load Brand<br/>Config"]
        I4["Build Workflow<br/>Templates"]
        I5["Build Prompt<br/>Library"]

        I1 --> I2
        I2 --> I3
        I3 --> I4
        I3 --> I5
    end

    subgraph "PHASE 1 (Per Garment: Parallel Across Garments)"
        P1A["Generate<br/>Prompts"]
        P1B["Build ComfyUI<br/>Workflow"]
        P1C["Submit to<br/>Flux2 Dev"]
        P1D["Variation Loop<br/>(4-6 seeds)"]
        P1E["Technical QA"]
        P1F["Brand QA"]

        P1A --> P1B
        P1B --> P1C
        P1C --> P1D
        P1D --> P1E
        P1E --> P1F
    end

    subgraph "PHASE 2 (Mixed Parallel/Sequential)"
        P2A["Base64 Encode<br/>Approved Bases"]
        P2B["NB Image-to-Image<br/>Refinement<br/>(Sequential per image)"]

        P2C["Track A: NB<br/>Variations (8-10)"]
        P2D["Track B: Flux2<br/>Batch (8-10)"]
        P2E["Track C: Imagen 4<br/>Heroes (2-3)"]

        P2F["Collect All<br/>Variations"]
        P2G["Batch QA +<br/>Brand Eval"]

        P2A --> P2B
        P2B --> P2C
        P2B --> P2D
        P2B --> P2E
        P2C --> P2F
        P2D --> P2F
        P2E --> P2F
        P2F --> P2G
    end

    subgraph "PHASE 3 (Per Image: Sequential; Aspect Ratios: Parallel)"
        P3A["Negative Space<br/>Analysis<br/>(Claude Vision)"]
        P3B["Select<br/>Typography"]
        P3C["Text Composite<br/>(NB or ComfyUI)"]

        P3D["Adapt 16:9"]
        P3E["Adapt 1:1"]
        P3F["Adapt 9:16"]

        P3G["QA + Brand<br/>Validation"]

        P3A --> P3B
        P3B --> P3C
        P3C --> P3D
        P3C --> P3E
        P3C --> P3F
        P3D --> P3G
        P3E --> P3G
        P3F --> P3G
    end

    subgraph "PHASE 4 (Aspect Ratios: Parallel)"
        P4A["Generate Motion<br/>Scripts"]

        P4B["Veo 3.1<br/>16:9 (poll)"]
        P4C["Veo 3.1<br/>1:1 (poll)"]
        P4D["Veo 3.1<br/>9:16 (poll)"]

        P4E["Video QA +<br/>Brand Eval"]

        P4A --> P4B
        P4A --> P4C
        P4A --> P4D
        P4B --> P4E
        P4C --> P4E
        P4D --> P4E
    end

    I4 --> P1A
    I5 --> P1A
    P1F -->|"Hard dependency:<br/>Phase 1 must complete"| P2A
    P2G -->|"Hard dependency:<br/>Phase 2 must complete"| P3A
    P3G -->|"Hard dependency:<br/>Phase 3 must complete"| P4A
```

### Dependency Summary Table

| Operation | Type | Depends On | Can Parallel With |
|-----------|------|------------|-------------------|
| Infrastructure validation | Sequential | Nothing | Nothing (must be first) |
| Typography research | Sequential | Infra validation | Nothing |
| Brand config load | Sequential | Typography research | Nothing |
| Workflow template build | Sequential | Brand config | Prompt library build |
| Prompt library build | Sequential | Brand config | Workflow template build |
| Phase 1: Per-garment generation | Parallel per garment | Init complete | Other garment P1 pipelines |
| Phase 1: Variation loop (per garment) | Sequential | Prior variation | Nothing |
| Phase 1: QA gate | Sequential | All variations generated | Nothing |
| Phase 2: NB refinement | Sequential per image | Phase 1 QA pass | Nothing |
| Phase 2: Variation scaling | Parallel (3 tracks) | Refinement complete | All 3 tracks run simultaneously |
| Phase 2: QA gate | Sequential | All variations collected | Nothing |
| Phase 3: Negative space analysis | Sequential per image | Phase 2 QA pass | Nothing |
| Phase 3: Aspect ratio adaptation | Parallel (3 formats) | Text composite done | All 3 ratios run simultaneously |
| Phase 3: QA gate | Sequential | All formats generated | Nothing |
| Phase 4: Motion script gen | Sequential | Phase 3 QA pass | Nothing |
| Phase 4: Veo animation | Parallel (3 formats) | Motion script ready | All 3 ratios run simultaneously |
| Phase 4: QA gate | Sequential | All videos downloaded | Nothing |

### Critical Path

The longest sequential chain that determines minimum pipeline duration:

```
Infra Validation -> Typography Research -> Brand Config -> Templates/Prompts
-> Phase 1 Generation (4-6 variations, sequential per seed)
-> Phase 1 QA
-> Phase 2 Refinement (sequential per image)
-> Phase 2 Scaling (parallel, bounded by slowest track)
-> Phase 2 QA
-> Phase 3 Negative Space Analysis
-> Phase 3 Text Composite
-> Phase 3 Aspect Ratio Adaptation (parallel)
-> Phase 3 QA
-> Phase 4 Motion Script
-> Phase 4 Veo Animation (parallel, bounded by longest poll)
-> Phase 4 QA
-> Pipeline Complete
```

Estimated critical path time: 20-30 minutes per garment (dominated by Veo 3.1 polling latency and QA retry loops).

---

## Appendix A: Engine Routing Decision Matrix

```mermaid
flowchart TD
    TASK_IN["Incoming Generation Task"]

    TASK_TYPE{{"Task Type?"}}

    BASE_GEN["Base Image<br/>Generation"]
    STYLE_XFER["Style Transfer<br/>(Chrome Mannequin)"]
    BATCH_VAR["Batch Variation<br/>Scaling"]
    HERO_SHOT["Hero Shot<br/>(Maximum Fidelity)"]
    TEXT_COMP["Text<br/>Compositing"]
    ANIMATION["Video<br/>Animation"]

    FLUX_PRIMARY["PRIMARY:<br/>Flux2 Dev (Local GPU)<br/>Zero latency, free"]
    NB_PRIMARY["PRIMARY:<br/>Nano Banana<br/>Native img-to-img"]
    FLUX_BATCH["PRIMARY:<br/>Flux2 Dev (Local GPU)<br/>Fastest batch gen"]
    IMG4_PRIMARY["PRIMARY:<br/>Imagen 4 Ultra<br/>Highest fidelity"]
    NB_TEXT["PRIMARY:<br/>Nano Banana<br/>Native text overlay"]
    VEO_PRIMARY["PRIMARY:<br/>Veo 3.1<br/>Best quality + audio"]

    NB_FB1["FALLBACK:<br/>Nano Banana"]
    NBP_FB1["FALLBACK:<br/>Nano Banana Pro"]
    IMG4F_FB1["FALLBACK:<br/>Imagen 4 Fast"]
    NBP_FB2["FALLBACK:<br/>Nano Banana Pro"]
    CV_FB1["FALLBACK:<br/>Claude Vision eval +<br/>ComfyUI text nodes"]
    VEO_FB1["FALLBACK:<br/>Veo 3.0 Fast"]

    TASK_IN --> TASK_TYPE
    TASK_TYPE -->|"Base gen"| BASE_GEN
    TASK_TYPE -->|"Style transfer"| STYLE_XFER
    TASK_TYPE -->|"Batch variation"| BATCH_VAR
    TASK_TYPE -->|"Hero shot"| HERO_SHOT
    TASK_TYPE -->|"Text composite"| TEXT_COMP
    TASK_TYPE -->|"Animation"| ANIMATION

    BASE_GEN --> FLUX_PRIMARY
    FLUX_PRIMARY -.->|"On failure"| NB_FB1

    STYLE_XFER --> NB_PRIMARY
    NB_PRIMARY -.->|"On failure"| NBP_FB1

    BATCH_VAR --> FLUX_BATCH
    FLUX_BATCH -.->|"On failure"| IMG4F_FB1

    HERO_SHOT --> IMG4_PRIMARY
    IMG4_PRIMARY -.->|"On failure"| NBP_FB2

    TEXT_COMP --> NB_TEXT
    NB_TEXT -.->|"On failure"| CV_FB1

    ANIMATION --> VEO_PRIMARY
    VEO_PRIMARY -.->|"On failure"| VEO_FB1
```

---

## Appendix B: State Machine for Pipeline Lifecycle

```mermaid
stateDiagram-v2
    [*] --> INITIALIZING

    INITIALIZING --> INFRA_CHECK: Start pipeline
    INFRA_CHECK --> INFRA_FAILED: Service unavailable
    INFRA_CHECK --> CONFIGURED: All services OK

    INFRA_FAILED --> INFRA_CHECK: Retry
    INFRA_FAILED --> ABORTED: Max retries exceeded

    CONFIGURED --> PHASE_1_RUNNING: Begin generation

    PHASE_1_RUNNING --> PHASE_1_QA: Variations generated
    PHASE_1_QA --> PHASE_1_RUNNING: QA fail, retry < 3
    PHASE_1_QA --> PHASE_2_RUNNING: QA pass (sufficient bases)
    PHASE_1_QA --> PHASE_1_ESCALATED: QA fail, retry >= 3

    PHASE_1_ESCALATED --> PHASE_2_RUNNING: Proceed with available
    PHASE_1_ESCALATED --> ABORTED: No viable bases

    PHASE_2_RUNNING --> PHASE_2_QA: Variations collected
    PHASE_2_QA --> PHASE_2_RUNNING: QA fail, retry < 3
    PHASE_2_QA --> PHASE_3_RUNNING: >= 16 pass
    PHASE_2_QA --> PHASE_2_DEGRADED: < 16 pass, retry >= 3

    PHASE_2_DEGRADED --> PHASE_3_RUNNING: Proceed with available

    PHASE_3_RUNNING --> PHASE_3_QA: Ads composited
    PHASE_3_QA --> PHASE_3_RUNNING: QA fail, retry < 3
    PHASE_3_QA --> PHASE_4_RUNNING: QA pass
    PHASE_3_QA --> PHASE_3_REJECTED: QA fail, retry >= 3

    PHASE_3_REJECTED --> PHASE_4_RUNNING: Skip rejected, animate rest

    PHASE_4_RUNNING --> PHASE_4_QA: Videos generated
    PHASE_4_QA --> PHASE_4_RUNNING: QA fail, retry < 3
    PHASE_4_QA --> COMPLETED: QA pass
    PHASE_4_QA --> PHASE_4_PARTIAL: QA fail, retry >= 3

    PHASE_4_PARTIAL --> COMPLETED: Deliver static + partial video

    COMPLETED --> [*]
    ABORTED --> [*]

    note right of COMPLETED
        outputs/static/ = approved statics
        outputs/animated/ = approved videos
        outputs/rejected/ = failed assets
        state/pipeline.json = final report
    end note

    note right of ABORTED
        state/pipeline.json = error details
        Human review required
    end note
```

---

## Appendix C: API Call Flow Summary

| Agent | Service | Endpoint | Method | Payload Direction | Response |
|-------|---------|----------|--------|-------------------|----------|
| Pipeline Operator | ComfyUI | `comfyui:8188/prompt` | POST | Workflow JSON -> ComfyUI | prompt_id |
| Pipeline Operator | ComfyUI | `comfyui:8188/history/{id}` | GET | -- | Job status |
| Pipeline Operator | ComfyUI | `comfyui:8188/view` | GET | Query params -> ComfyUI | PNG image bytes |
| Pipeline Operator | Nano Banana | `googleapis.com/.../generateContent` | POST | Base64 image + prompt -> Google | Base64 PNG in JSON |
| Pipeline Operator | Nano Banana Pro | `googleapis.com/.../generateContent` | POST | Base64 image + prompt -> Google | Base64 PNG in JSON |
| Pipeline Operator | Imagen 4 Ultra | `googleapis.com/.../predict` | POST | Prompt + params -> Google | Base64 image in JSON |
| Pipeline Operator | Veo 3.1 | `googleapis.com/.../predictLongRunning` | POST | Base64 image + prompt -> Google | operation_name |
| Pipeline Operator | Veo 3.1 | `googleapis.com/v1beta/{op}` | GET | -- | Status + video URI |
| Creative Director | Perplexity | `api.perplexity.ai/chat/completions` | POST | Research query -> Perplexity | JSON response |
| Brand Guardian | Claude Vision | (Internal Anthropic API) | POST | Image + eval prompt -> Claude | Structured evaluation |

---

## Appendix D: Retry and Backoff Strategy

All API calls follow exponential backoff with jitter:

```
Attempt 1: immediate
Attempt 2: 2s + random(0-1s)
Attempt 3: 4s + random(0-2s)
```

QA retry loops follow a different cadence:

```
QA Retry 1: Adjust parameters (prompt weight, cfg, seed) -> regenerate
QA Retry 2: Adjust parameters more aggressively + try alternate engine -> regenerate
QA Retry 3: (final) Use most permissive parameters -> regenerate
After Retry 3: Move to outputs/rejected/, flag for human review
```

Maximum total retries per asset across all failure types: **3 per QA gate, 3 per API call** (9 total attempts worst case per asset per phase).
