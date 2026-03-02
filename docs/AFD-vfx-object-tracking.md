# AFD: VFX Object Tracking Pipeline v2 — Architecture & Functional Design

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VFX Pipeline CLI                         │
│   python -m vfx_pipeline --video X --screenshot Y --output Z    │
└──────────────┬──────────────────────────────┬───────────────────┘
               │                              │
    ┌──────────▼──────────┐       ┌───────────▼──────────────┐
    │   Phase 1: ComfyUI  │       │   Phase 2: Blender MCP   │
    │   (3D Generation)   │       │   (Track + Composite)    │
    │                     │       │                          │
    │  ┌───────────────┐  │       │  ┌────────────────────┐  │
    │  │ Step 1: Rembg │  │       │  │ Step 3: Scene Setup│  │
    │  │ Background    │  │       │  │ Import GLB, fix    │  │
    │  │ Removal       │  │       │  │ rotation, parents  │  │
    │  └──────┬────────┘  │       │  └────────┬───────────┘  │
    │  ┌──────▼────────┐  │       │  ┌────────▼───────────┐  │
    │  │ Step 2:       │  │       │  │ Step 4: GeoTracker │  │
    │  │ Hunyuan3D v2  │  │       │  │ Analyze, pin,      │  │
    │  │ Mesh + Texture│  │       │  │ track, refine      │  │
    │  └──────┬────────┘  │       │  └────────┬───────────┘  │
    │         │ GLB       │       │  ┌────────▼───────────┐  │
    │         ▼           │       │  │ Step 5: Compositor │  │
    │  ┌───────────────┐  │       │  │ AlphaOver, render  │  │
    │  │ Validate GLB  │  │       │  │ PNG sequence       │  │
    │  └───────────────┘  │       │  └────────────────────┘  │
    └─────────────────────┘       └──────────────────────────┘
```

## Component Specifications

### C1: ComfyUI Client (`comfyui_client.py`)

**Responsibility**: HTTP/WebSocket communication with ComfyUI server.

| Method | Purpose | Changes from v1 |
|--------|---------|-----------------|
| `upload_image(path)` | Upload image to ComfyUI input dir | No change |
| `run_workflow(workflow, timeout)` | Queue prompt, wait for completion via WS | No change |
| `get_output_path(outputs, node_id, key)` | Extract file path from node output | Add GLB-specific key handling |
| `free_memory()` | POST /free to release GPU VRAM | No change |
| `get_3d_output(outputs, node_id)` | Extract GLB path from Hy3DExportMesh | **New** |

### C2: Blender Client (`blender_client.py`)

**Responsibility**: WebSocket communication with Blender MCP server.

| Method | Purpose | Changes from v1 |
|--------|---------|-----------------|
| `execute_python(script, timeout)` | Run Python in Blender context | No change |
| `execute_python_with_result(script, timeout)` | Run Python, parse structured result | **New** |

### C3: Workflow Builder (`workflows.py`)

**Responsibility**: Build ComfyUI workflow JSON programmatically.

| Function | Purpose | Changes from v1 |
|----------|---------|-----------------|
| `build_hunyuan3d_generation(image, seed)` | Hunyuan3D v2 mesh generation | **New** (replaces SAM3D) |
| `load_reference_workflow(path)` | Load the KeenTools example JSON directly | **New** |
| ~~`build_sam3_segmentation`~~ | Removed | Was using non-existent nodes |
| ~~`build_sam3d_reconstruction`~~ | Removed | Was using non-existent nodes |
| ~~`build_sam3_video_segmentation`~~ | Removed | Was using non-existent nodes |

### C4: Blender Scripts (embedded in `pipeline.py`)

Each script is a self-contained Python string executed via Blender MCP.

#### Script: `BLENDER_RESET_AND_SETUP`
```
1. Delete all objects (bpy.ops.wm.read_homefile use_empty=True)
2. Enable keentools addon
3. Create new GeoTracker
4. Return geotracker index
```

#### Script: `BLENDER_LOAD_FOOTAGE`
```
1. Load video as movie clip
2. Set scene frame range to match clip
3. Set scene FPS from clip metadata
4. Return clip dimensions and frame count
```

#### Script: `BLENDER_IMPORT_AND_PREPARE_GLB`
```
1. Import GLB via import_scene.gltf
2. Find all imported objects
3. For each object:
   a. Convert rotation_mode from 'QUATERNION' to 'XYZ'
   b. If parented to empty: clear parent (keep transform)
4. Delete orphan empties
5. Rename primary mesh to target name
6. Return mesh name and vertex count
```
**This is the critical fix missing from v1.**

#### Script: `BLENDER_SETUP_GEOTRACKER`
```
1. Get mesh object and movie clip
2. Create camera if not exists
3. Access gt_settings.geotrackers[current_geotracker_num]
4. Assign geomobj, camobj, movie_clip
5. Match render resolution to clip
6. Return "ready"
```

#### Script: `BLENDER_ANALYZE_CLIP`
```
1. Run bpy.ops.keentools_gt.analyze_clip()
2. Wait for analysis to complete (poll calculating_mode)
3. Return analysis status
```
**New — v1 skipped this entirely.**

#### Script: `BLENDER_ALIGN_MODEL`
```
1. Enter pin mode (bpy.ops.keentools_gt.pinmode)
2. Set initial transform from parameters (loc/rot/scale)
   OR use magic_keyframe_btn() as fallback
3. Return alignment status
```

#### Script: `BLENDER_TRACK_WITH_PINS`
```
1. For each key frame in pin_frames:
   a. Set scene.frame_current = frame
   b. Enter pin mode
   c. Apply transform adjustment (if provided)
   d. Create pin at this position
2. Run bpy.ops.keentools_gt.refine_all_btn()
3. Poll tracking status until complete or timeout
4. Return tracking result
```
**New — v1 only used single magic keyframe.**

#### Script: `BLENDER_BAKE_AND_EXPORT`
```
1. Exit pin mode
2. Bake animation to world space (product=1 = GEOTRACKER)
3. Save .blend file
4. Return bake status
```

#### Script: `BLENDER_SETUP_COMPOSITOR_5X`
```
1. Enable compositor nodes (scene.use_nodes = True)
2. Get/create compositing_node_group (Blender 5.x API)
3. Create output socket on interface
4. Create nodes: MovieClip, RLayers, AlphaOver, GroupOutput, Viewer
5. Link: MovieClip→AlphaOver.Background, RLayers→AlphaOver.Foreground
6. Link: AlphaOver→GroupOutput, AlphaOver→Viewer
7. Set render engine, resolution, output path
8. Return "compositor_ready"
```

#### Script: `BLENDER_RENDER_FRAMES`
```
1. bpy.ops.render.render(animation=True)
2. Return output path and frame count
```

### C5: Pipeline Orchestrator (`pipeline.py`)

**Responsibility**: Coordinate all steps with validation between each.

```python
class VFXPipeline:
    def __init__(comfyui_url, blender_url)

    # Phase 1: ComfyUI
    def step1_generate_3d(screenshot_path, seed) -> GLBResult

    # Phase 2: Blender
    def step2_setup_scene(glb_path, video_path) -> SceneResult
    def step3_track(pin_frames, timeout) -> TrackResult
    def step4_composite(render_engine) -> CompositeResult

    # Full pipeline
    def run(video, screenshot, output, **kwargs) -> PipelineResult
```

**Validation gates between steps:**

| After Step | Validation | Fail Action |
|------------|-----------|-------------|
| 1 (3D gen) | GLB file exists, >1KB, valid GLTF header | Abort with error |
| 2 (scene) | Mesh loaded, GeoTracker configured, clip frames > 0 | Abort with error |
| 3 (track) | Animation keyframes exist on mesh object | Warn, attempt re-track |
| 4 (composite) | Output PNG files exist, count matches frame range | Warn |

## Data Flow

```
screenshot.png ──► ComfyUI Hunyuan3D ──► model.glb ─┐
                                                      ├──► Blender GeoTracker ──► tracked.blend
video.mp4 ────────────────────────────────────────────┘         │
                                                                ▼
                                                        Compositor
                                                                │
                                                                ▼
                                                    composited_####.png
```

## GPU Memory Strategy

| Phase | GPU Usage | Action |
|-------|-----------|--------|
| Hunyuan3D mesh gen | ~12-20 GB | Load DIT + VAE models |
| Hunyuan3D texture | ~8-15 GB | Load paint + delight models |
| Between phases | 0 GB | `POST /free` + 3s wait |
| Blender GeoTracker | ~2-4 GB | Optical flow analysis |
| Blender EEVEE render | ~2-6 GB | Compositor render |

## CLI Interface

```bash
python -m vfx_pipeline \
    --video footage.mp4 \
    --screenshot object.png \
    --output /tmp/vfx_out \
    --name "quad_bike" \
    --seed 42 \
    --pin-frames 1,50,100,150 \
    --render-engine EEVEE \
    --timeout 600

# Skip to tracking with existing GLB:
python -m vfx_pipeline \
    --video footage.mp4 \
    --glb model.glb \
    --output /tmp/vfx_out

# Use KeenTools example files:
python -m vfx_pipeline \
    --video assets/keentools-example/ComfyUI+GeoTracker_example/5835604-hd_1920_1080_25fps.mp4 \
    --glb assets/keentools-example/ComfyUI+GeoTracker_example/Car.glb \
    --output /tmp/vfx_test
```

## Error Handling

| Error | Detection | Recovery |
|-------|-----------|----------|
| ComfyUI timeout | WebSocket no progress for 120s | Abort step, report last known state |
| GLB generation failure | Empty/missing output file | Retry once with different seed |
| Blender MCP disconnect | WebSocket close event | Reconnect with 3 retries |
| GeoTracker addon missing | `addon_enable` exception | Abort with install instructions |
| Tracking timeout | Poll loop exceeds max iterations | Stop tracking, bake what exists |
| Compositor render fail | `render.render()` exception | Fallback to viewport render |
| VRAM OOM | CUDA OOM in error string | Free memory, retry with lower resolution |

## File Organization

```
src/vfx_pipeline/
├── __init__.py
├── __main__.py
├── pipeline.py          # Orchestrator (VFXPipeline class)
├── comfyui_client.py    # ComfyUI HTTP/WS client
├── blender_client.py    # Blender MCP WebSocket client
├── blender_scripts.py   # All Blender Python scripts (extracted from pipeline.py)
├── workflows.py         # ComfyUI workflow builders
└── validators.py        # Output validation between steps
```
