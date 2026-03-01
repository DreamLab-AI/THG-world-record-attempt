# 3D VFX Object Tracking Pipeline — Skill Spec

## Overview

Agentic pipeline that takes a video, segments an object using SAM 3, reconstructs it as a 3D mesh via SAM 3D, tracks it across the video using GeoTracker/Blender, and outputs VFX-ready composited footage.

**Skill name**: `3d-vfx-tracking`

## Pipeline Architecture

```
Video Input
  │
  ├─ Step 1: SAM 3 — Text-prompted video segmentation
  │   Tool: ComfyUI (SAM3 nodes or fallback SAM2 + GroundingDINO)
  │   Input: Video + text prompt ("the red jacket")
  │   Output: Per-frame masks + best frame isolation
  │
  ├─ Step 2: SAM 3D — Single-image 3D reconstruction
  │   Tool: ComfyUI (SAM3D pipeline: 8 nodes)
  │   Input: Best frame + mask
  │   Output: Textured GLB mesh + Gaussian PLY
  │
  ├─ Step 3: GeoTracker — 3D match-move tracking
  │   Tool: Blender MCP (bpy.ops.keentools_gt.*)
  │   Input: GLB mesh + original video
  │   Output: Per-frame 3D pose solve (Alembic .abc)
  │
  └─ Step 4: VFX Compositing
      Tool: Blender compositor + render
      Input: Tracked 3D asset + video backdrop
      Output: Final composited video
```

## Environment Requirements

| Component | Version | Access | Status |
|-----------|---------|--------|--------|
| ComfyUI | Latest | `http://comfyui:8188` | Running, **736 nodes** |
| Blender | 5.0.1 | DISPLAY=:1, MCP on `ws://127.0.0.1:8765` | Running, 52 MCP tools |
| SAM 3 model | Nov 2025 | `sam3.pt` (3.45GB) cached in ComfyUI | Ready |
| SAM 3D models | Nov 2025 | `sam3.pt` + `slat_decoder_mesh.pt` + DINOv2 | Ready |
| SAM 2.1 | 2024 | `sam2.1_hiera_tiny-fp16.safetensors` | Ready |
| SAM1 + GroundingDINO | 2024 | `comfyui_segment_anything` package | **Installed** |
| SAM2 + GroundingDINO | 2024 | `ComfyUI-SAM2` package | **Installed** |
| VideoHelperSuite | Latest | 40 nodes (VHS_LoadVideo, etc.) | **Installed** |
| GPUs | 2x RTX 6000 Ada | 50.9GB VRAM each | Available |
| GeoTracker | v2025.3.0 | KeenTools addon, 87 operators | **Installed** |
| pykeentools | v2025.3.0 | Core library (135MB native .so) | **Installed** |

### Installed ComfyUI Custom Node Packages
```
/root/ComfyUI/custom_nodes/
├── ComfyUI-GGUF              # GGUF model loading
├── ComfyUI-Manager            # Node manager
├── ComfyUI-MultiGPU          # Multi-GPU distribution
├── ComfyUI-SAM2              # SAM2 segmentation + GroundingDINO
├── ComfyUI-TRELLIS2          # Trellis2 image-to-3D
├── ComfyUI-UltraShape1       # Mesh refinement
├── ComfyUI-VideoHelperSuite  # 40 video processing nodes
├── comfyui-sam3dobjects       # SAM3D reconstruction (12 nodes)
└── comfyui_segment_anything   # SAM1 + GroundingDINO segmentation
```

## Step 1: Video Segmentation (SAM 3)

### Model Details
- **Model**: `facebook/sam3` (848M params, detector + tracker)
- **Key feature**: Open-vocabulary text prompts — no clicks needed
- **Training data**: SA-Co (214K unique phrases, 126K images/videos)
- **HuggingFace**: `facebook/sam3`, `docs/transformers/model_doc/sam3`

### ComfyUI Nodes — Currently Installed

**Primary (GroundingDINO + SAM2)** — text-prompted segmentation:
- `GroundingDinoModelLoader (segment anything2)` — load text detection model
- `GroundingDinoSAM2Segment (segment anything2)` — text prompt → masks
- `SAM2ModelLoader (segment anything2)` — load SAM2 model

**Fallback (GroundingDINO + SAM1)**:
- `GroundingDinoModelLoader (segment anything)` — load detection model
- `GroundingDinoSAMSegment (segment anything)` — text prompt → masks
- `SAMModelLoader (segment anything)` — load SAM1 model

**Video Frame Extraction** (VideoHelperSuite, 40 nodes):
- `VHS_LoadVideo` / `VHS_LoadVideoFFmpeg` — load video to frames
- `VHS_SelectEveryNthImage` — temporal subsampling
- `VHS_SplitImages` / `VHS_MergeImages` — frame manipulation
- `VHS_VideoCombine` — frames back to video
- `VHS_VideoInfo` — metadata extraction

### SAM3 Text-Prompted Nodes (Not Yet Installed — Future Upgrade)
These packages provide native SAM3 text-prompted segmentation (no GroundingDINO needed):
1. **ComfyUI-TBG-SAM3** (Ltamann) — Production-ready, 3 nodes
2. **ComfyUI-SAM3** (PozzettiAndrea) — Interactive points editor
3. **ComfyUI-Easy-Sam3** (yolain) — Image + video text-prompted
4. **ComfyUI-segment-anything-3** (wzyfromhust) — Open-vocabulary

### Workflow: `sam3-video-segmentation.json`

```
LoadVideo → ExtractFrames → SAM3Segmentation(text_prompt) → MaskSequence → SaveBestFrame + SaveMasks
```

### Key Parameters
| Parameter | Value | Notes |
|-----------|-------|-------|
| text_prompt | User-provided | e.g. "the chrome mannequin" |
| confidence_threshold | 0.5 | Adjust for precision vs recall |
| video_fps | Match source | Typically 24/30 |
| mask_output | Per-frame PNG | Alpha channel masks |

## Step 2: 3D Reconstruction (SAM 3D)

### Model Details
- **Model**: `facebook/sam-3d-objects` (paper: arXiv:2511.16624)
- **Capability**: Single image → full textured 3D mesh with plausible backside
- **Approach**: Progressive multi-stage (depth → sparse → SLAT → mesh/gaussian → texture)
- **Also available**: `facebook/sam-3d-body-dinov3` for human body mesh recovery

### ComfyUI SAM3D Pipeline (12 nodes, all installed)

```
LoadSAM3DModel                    → loads 6 sub-models (~30s)
  ├─ SAM3D_DepthEstimate          → MoGe depth estimation (~5s)
  ├─ SAM3DSparseGen               → Stage 1: sparse voxel structure (~5s)
  ├─ SAM3DSLATGen                 → Stage 2: SLAT diffusion (~60-90s)
  ├─ SAM3DMeshDecode              → Decode to vertex-colored mesh (~15s)
  ├─ SAM3DGaussianDecode          → Decode to Gaussian splats (~15s)
  └─ SAM3DTextureBake             → UV texture baking (~60s)
      └─ Output: textured.glb + gaussian.ply
```

### Critical Parameters
| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| dtype | bfloat16 | Best quality/speed tradeoff |
| stage1_inference_steps | 30 | Quality (min 20) |
| stage1_cfg_strength | 7.5 | Classifier-free guidance |
| stage2_inference_steps | 30 | Quality (min 20) |
| stage2_cfg_strength | 5.5 | Lower than stage 1 |
| texture_size | 4096 | 4K UV map |
| texture_mode | "opt" | Gradient descent (~60s) vs "fast" (~5s) |
| simplify | 0.97 | Preserve mesh detail |
| save_glb | true | For Blender import |

### VRAM Management
- SAM3D full pipeline: ~25GB VRAM
- Cannot run concurrently with FLUX2 (~37GB)
- Free GPU memory between phases: `POST /free {"unload_models": true, "free_memory": true}`

### Output Structure
```
sam3d_inference_X/
├── gaussian.ply      # 3D Gaussian splats (~70MB)
├── mesh.glb          # Textured mesh with 4K UV (~35MB)
├── pointcloud.ply    # Point cloud
├── metadata.json     # Generation metadata
├── pointmap.pt       # Depth data
├── slat.pt           # SLAT latent
└── sparse_structure.pt
```

### Alternative 3D Methods (also in ComfyUI)
| Method | Nodes | Best For |
|--------|-------|----------|
| **Trellis2** | 11 nodes | Fast image-to-3D, GLB export, PBR |
| **Rodin3D** | 5 nodes | Detailed generation, sketches |
| **UltraShape** | 4 nodes | Mesh refinement, simplification |
| **Hunyuan3D** | Multi-view | Tencent's open-source PBR pipeline |

## Step 3: GeoTracker (3D Match-Move)

### Overview
GeoTracker by KeenTools — geometry-based 3D object tracking. Takes a 3D mesh + video footage and solves the object's pose per frame.

- **Version**: v2025.3.0 (Dec 2025)
- **Supports**: Blender 5.0, After Effects 25.6, Nuke 16.1+
- **Export**: Alembic `.abc` for animated geometry
- **License**: Commercial (free tier available)
- **Download**: https://keentools.io/download/geotracker-for-blender

### Installed Version
- **KeenTools 2025.3.0** — FaceBuilder + FaceTracker + GeoTracker
- **pykeentools 2025.3.0** — Native core library (`pykeentools.cpython-311-x86_64-linux-gnu.so`)
- **Path**: `/home/devuser/.config/blender/5.0/scripts/addons/keentools/`
- **License**: Commercial (free trial available, prompted on first use)

### GeoTracker Operators (87 total)
Key operators in `bpy.ops.keentools_gt.*`:
- **Lifecycle**: `create_geotracker`, `delete_geotracker`, `select_geotracker`
- **Pin placement**: `pinmode`, `movepin`, `remove_pins_btn`, `toggle_pins_btn`
- **Tracking**: `track_next_btn`, `track_prev_btn`, `track_to_end_btn`, `track_to_start_btn`
- **Refinement**: `refine_btn`, `refine_all_btn`
- **Keyframes**: `magic_keyframe_btn`, `add_keyframe_btn`, `remove_keyframe_btn`
- **Video**: `create_precalc`, `analyze_call`, `split_video_to_frames`
- **Animation**: `bake_animation_to_world`, `bake_from_selected_frames`
- **Transfer**: `transfer_tracking`
- **Texture**: `texture_bake_options`, `texture_file_export`, `reproject_tex_sequence`
- **Modes**: `switch_to_camera_mode`, `switch_to_geometry_mode`

### Also Available: FaceBuilder (55 ops) + FaceTracker (50 ops)
- `bpy.ops.keentools_fb.*` — 3D head from photos, blendshapes, FBX/CC export
- `bpy.ops.keentools_ft.*` — Video face tracking, FACS animation transfer

### Python Scripting (Blender Operators)
```python
import bpy

# GeoTracker workflow via Blender Python:

# 1. Import mesh from SAM3D output
bpy.ops.import_scene.gltf(filepath="/path/to/mesh.glb")

# 2. Import video as movie clip
bpy.ops.clip.open(filepath="/path/to/video.mp4")

# 3. Create GeoTracker instance
bpy.ops.keentools_gt.create_geotracker()

# 4. Assign mesh and clip (via GeoTracker panel properties)
# Access via bpy.context.scene.keentools_gt_settings

# 5. Enter pin mode and place pins
bpy.ops.keentools_gt.pinmode()

# 6. Track forward through video
bpy.ops.keentools_gt.track_to_end_btn()

# 7. Refine tracking
bpy.ops.keentools_gt.refine_all_btn()

# 8. Bake animation to world space
bpy.ops.keentools_gt.bake_animation_to_world()

# 9. Export as Alembic
bpy.ops.wm.alembic_export(filepath="/path/to/tracked.abc")
```

### Blender MCP Integration
Via the `execute_python` MCP tool, we can script the entire GeoTracker workflow headlessly:
```json
{
  "tool": "execute_python",
  "params": {
    "code": "import bpy; bpy.ops.import_scene.gltf(filepath='/path/to/mesh.glb')"
  }
}
```

### Fallback: Blender Built-in Motion Tracking
If GeoTracker isn't available:
- Blender's Camera Tracker (Edit > Preferences > Add-ons > "Motion Tracking")
- Manual camera solve → attach mesh to solved camera
- Less automated but always available

## Step 3b: Multi-View Alignment

Critical for placing the 3D asset back into the scene correctly from any camera angle.

### Approach 1: GeoTracker Camera Mode
GeoTracker operates in two modes:
- **Geometry mode**: Mesh moves, camera is fixed (object tracking)
- **Camera mode** (`switch_to_camera_mode`): Camera moves, mesh is fixed (camera solve)

For VFX compositing, use camera mode to solve the original footage camera, then place the 3D asset in that solved space.

```python
# Switch GeoTracker to camera mode
bpy.ops.keentools_gt.switch_to_camera_mode()
# Track camera motion from video
bpy.ops.keentools_gt.track_to_end_btn()
# Now any object in the scene renders from the correct viewpoint per frame
```

### Approach 2: Blender Built-in Camera Solver (25 operators)
Full camera track from 2D feature markers:
```python
# Load footage as movie clip
clip = bpy.data.movieclips.load("/path/to/video.mp4")
# Auto-detect and track features
bpy.ops.clip.track_markers(backwards=False, sequence=True)
# Solve camera from tracked features
bpy.ops.clip.solve_camera()
# One-click scene setup with solved camera
bpy.ops.clip.setup_tracking_scene()
# Create ground plane from tracked markers
bpy.ops.clip.create_plane_track()
```

### Approach 3: SAM3D Pre-Alignment (ComfyUI side)
Before exporting to Blender, optimize the mesh pose:
- `SAM3D_PoseOptimization` — ICP + render alignment → pose matrix + IoU score
- `SAM3D_ScenePoseOptimize` — multi-object scene alignment
- Outputs GLB with correct initial pose relative to the source camera

### Combined Multi-View Pipeline
```
SAM3D_PoseOptimization → initial pose alignment (ComfyUI)
    → Export GLB with source-camera-aligned pose
    → Import into Blender
    → GeoTracker camera mode OR Blender solve_camera
    → Per-frame camera solve from footage
    → 3D asset in solved scene = viewpoint-correct composite
```

## Step 4: VFX Compositing

### Blender Compositor
```python
# Set up compositing nodes
bpy.context.scene.use_nodes = True
tree = bpy.context.scene.node_tree

# Movie Clip → Alpha Over → Composite
clip_node = tree.nodes.new('CompositorNodeMovieClip')
render_layer = tree.nodes.new('CompositorNodeRLayers')
alpha_over = tree.nodes.new('CompositorNodeAlphaOver')
composite = tree.nodes['Composite']

# Connect: backdrop + 3D render → alpha over → output
tree.links.new(clip_node.outputs['Image'], alpha_over.inputs[1])
tree.links.new(render_layer.outputs['Image'], alpha_over.inputs[2])
tree.links.new(alpha_over.outputs['Image'], composite.inputs['Image'])
```

### Render via Blender MCP
```json
{"tool": "set_render_settings", "params": {"engine": "EEVEE", "resolution_x": 1920, "resolution_y": 1080, "fps": 30}}
{"tool": "render_animation", "params": {"output_path": "/tmp/composited_", "format": "FFMPEG"}}
```

### Alternative: AI Video Generation
Instead of traditional compositing, use the tracked pose data to guide AI video generation:
- Rendered 3D pose → ControlNet depth/normal maps → Stable Diffusion / FLUX
- Per-frame guided generation with temporal consistency
- ComfyUI video nodes (Runway Gen4, Kling, Veo3) for final output

## Full Orchestration Script

```python
#!/usr/bin/env python3
"""
3D VFX Object Tracking Pipeline
SAM3 → SAM3D → GeoTracker → Compositing
"""
import requests
import json
import time
import websocket

COMFYUI = "http://comfyui:8188"
BLENDER_WS = "ws://127.0.0.1:8765"

def comfyui_run(workflow: dict) -> dict:
    """Submit workflow and wait for completion."""
    r = requests.post(f"{COMFYUI}/prompt", json={"prompt": workflow})
    prompt_id = r.json()["prompt_id"]
    while True:
        h = requests.get(f"{COMFYUI}/history/{prompt_id}").json()
        status = h.get(prompt_id, {}).get("status", {})
        if status.get("completed"):
            return h[prompt_id].get("outputs", {})
        if status.get("status_str") == "error":
            raise Exception(f"Failed: {status}")
        time.sleep(5)

def blender_exec(code: str) -> dict:
    """Execute Python in Blender via MCP WebSocket."""
    ws = websocket.create_connection(BLENDER_WS)
    ws.send(json.dumps({"id": "1", "tool": "execute_python", "params": {"code": code}}))
    result = json.loads(ws.recv())
    ws.close()
    return result

def pipeline(video_path: str, text_prompt: str, output_path: str):
    # Step 1: SAM3 Video Segmentation
    print(f"[1/4] Segmenting '{text_prompt}' in video...")
    seg_workflow = build_sam3_workflow(video_path, text_prompt)
    seg_outputs = comfyui_run(seg_workflow)
    best_frame = seg_outputs["save_best"]["images"][0]["filename"]
    mask = seg_outputs["save_mask"]["images"][0]["filename"]

    # Free GPU
    requests.post(f"{COMFYUI}/free", json={"unload_models": True, "free_memory": True})
    time.sleep(5)

    # Step 2: SAM3D Reconstruction
    print("[2/4] Reconstructing 3D mesh...")
    sam3d_workflow = build_sam3d_workflow(best_frame, mask)
    mesh_outputs = comfyui_run(sam3d_workflow)
    glb_path = mesh_outputs["texture_bake"]["result"][0]

    # Step 3: GeoTracker in Blender
    print("[3/4] Tracking mesh across video...")
    blender_exec(f"""
import bpy
bpy.ops.wm.read_homefile(use_empty=True)
bpy.ops.import_scene.gltf(filepath='{glb_path}')
# ... GeoTracker setup and solve ...
bpy.ops.wm.alembic_export(filepath='/tmp/tracked.abc')
    """)

    # Step 4: Compositing
    print("[4/4] Compositing VFX...")
    blender_exec(f"""
import bpy
# ... compositor setup ...
bpy.ops.render.render(animation=True)
    """)

    print(f"Done! Output: {output_path}")
```

## Model Comparison

| Model | Input | Output | Speed | VRAM | ComfyUI |
|-------|-------|--------|-------|------|---------|
| SAM 3 | Video + text | Per-frame masks | Real-time | ~8GB | 5+ packages |
| SAM 2.1 | Video + points/boxes | Per-frame masks | Real-time | ~4GB | Mature |
| SAM 3D Objects | Single image | Textured GLB | ~2.5min | ~25GB | 12 nodes |
| SAM 3D Body | Single image | Body mesh | ~1min | ~15GB | Not yet |
| TripoSR | Single image | Mesh | <0.5s | ~8GB | Via 3D-Pack |
| Trellis2 | Single image | GLB + PBR | ~30s | ~12GB | 11 nodes |
| MASt3R | Multiple images | Scene mesh | ~1min | ~16GB | 3 nodes |
| GeoTracker | Mesh + video | Tracked pose | ~30s/frame | CPU | Blender addon |

## References

- SAM 3: https://ai.meta.com/sam3/ | https://huggingface.co/facebook/sam3
- SAM 3D: https://arxiv.org/abs/2511.16624 | https://huggingface.co/facebook/sam-3d-objects
- SAM 3D Body: https://huggingface.co/facebook/sam-3d-body-dinov3
- GeoTracker: https://keentools.io/products/geotracker-for-blender
- pykeentools: https://keentools.io/download/core
- TripoSR: https://huggingface.co/stabilityai/TripoSR
- MASt3R: https://github.com/naver/mast3r
- Trellis2: https://huggingface.co/microsoft/TRELLIS.2-4B
- ComfyUI-TBG-SAM3: https://github.com/Ltamann/ComfyUI-TBG-SAM3
- ComfyUI-SAM3: https://github.com/PozzettiAndrea/ComfyUI-SAM3
