# PRD: VFX Object Tracking Pipeline v2

## Product Overview

A scripted pipeline that takes a video and a screenshot, generates a 3D model from the screenshot using Hunyuan3D v2 (via ComfyUI), imports the model into Blender, tracks it against the video using GeoTracker, and composites CG elements over the original footage.

**Based on**: KeenTools official tutorial workflow (GeoTracker + SAM 3D / Hunyuan3D).

## Problem Statement

The v1 pipeline (`src/vfx_pipeline/pipeline.py`) failed due to:

1. **Wrong 3D generation tool**: Used non-existent SAM3D ComfyUI nodes; fell back to SAM2+GroundingDINO (segmentation, not 3D generation)
2. **Missing GLB preparation**: No quaternion→Euler rotation fix, no parent clearing, no mesh rename
3. **No manual pin alignment**: Used `magic_keyframe_btn()` blindly instead of initial model positioning
4. **No clip analysis**: Skipped `analyze_clip()` which GeoTracker needs for feature detection
5. **No vertex group masking**: Wheels/non-rigid parts tracked incorrectly
6. **No multi-keyframe pinning**: Single magic keyframe instead of pinning at multiple key positions
7. **Compositor gap**: Tracked animation (Alembic) never re-imported; rendered untransformed mesh
8. **Wrong node types**: SAM3D workflow config acknowledged missing nodes in its own JSON

## Requirements

### Functional Requirements

#### FR-1: 3D Model Generation
- **FR-1.1**: Accept a single screenshot (PNG/JPG) of the target object from a 3/4 angle
- **FR-1.2**: Remove background using rembg (TransparentBGSession+ node)
- **FR-1.3**: Generate untextured 3D mesh using Hunyuan3D-2 DIT model
- **FR-1.4**: Generate textured 3D mesh using Hunyuan3D-2 paint/delight/bake pipeline
- **FR-1.5**: Export both untextured and textured GLB files
- **FR-1.6**: Support the official KeenTools example workflow (`3dmodelgeneration.json`) as the canonical ComfyUI workflow

- **FR-1.7**: Accept pre-made GLB files (skip generation) via `--glb` flag

#### FR-2: Blender Scene Setup
- **FR-2.1**: Reset Blender scene (delete default cube, camera, light)
- **FR-2.2**: Create new GeoTracker instance
- **FR-2.3**: Load video footage as movie clip
- **FR-2.4**: Import GLB model
- **FR-2.5**: Convert rotation mode from Quaternion to XYZ Euler on all imported objects
- **FR-2.6**: Clear parent relationships (unparent from empty objects)
- **FR-2.7**: Delete orphan empty objects from GLB import
- **FR-2.8**: Rename primary mesh to user-specified name (default: "tracked_object")
- **FR-2.9**: Load mesh into GeoTracker geometry slot
- **FR-2.10**: Analyze clip (pre-compute optical flow for tracking)

#### FR-3: Model Alignment
- **FR-3.1**: Enter pin mode for initial alignment
- **FR-3.2**: Position model at initial frame to match object in footage
- **FR-3.3**: Support scripted initial transform (location, rotation, scale) via `--initial-transform`
- **FR-3.4**: Fallback to magic keyframe when no initial transform provided

#### FR-4: Mesh Preparation (Optional)
- **FR-4.1**: Accept vertex group names for surface masking (e.g., mask wheels)
- **FR-4.2**: Apply surface mask in GeoTracker mask tab
- **FR-4.3**: Support proportional editing adjustments via transform deltas

#### FR-5: Tracking
- **FR-5.1**: Pin model at user-specified key frames (or auto-detect 3-5 evenly spaced frames)
- **FR-5.2**: Run `refine_all` to interpolate tracking between keyframes
- **FR-5.3**: Poll tracking status with configurable timeout (default: 600s, max: 1800s)
- **FR-5.4**: Support track-to-end and track-to-start directions
- **FR-5.5**: Export tracked animation as keyframed transforms on the mesh object

#### FR-6: Compositing & Render
- **FR-6.1**: Set up Blender 5.x compositor with correct node group API
- **FR-6.2**: Layer render (3D tracked object) over video background via AlphaOver
- **FR-6.3**: Render to PNG frame sequence or MP4 via FFmpeg
- **FR-6.4**: Match output resolution to input video
- **FR-6.5**: Support EEVEE (fast) and Cycles (quality) render engines

### Non-Functional Requirements

- **NFR-1**: Pipeline must work headless (no GUI interaction required)
- **NFR-2**: Each step must validate its output before proceeding to the next
- **NFR-3**: VRAM management: free GPU memory between ComfyUI and Blender phases
- **NFR-4**: Idempotent: re-running a step with same inputs produces same outputs
- **NFR-5**: Total pipeline time < 10 minutes for a 10-second 1080p clip with simple geometry

### Inputs

| Input | Required | Format | Description |
|-------|----------|--------|-------------|
| Video | Yes | MP4/MOV | Footage containing the object to track |
| Screenshot | Yes* | PNG/JPG | 3/4 angle view of object (*or provide GLB) |
| GLB model | No | GLB | Pre-made 3D model (skips generation) |
| Text prompt | No | String | Object name for logging/naming |
| Initial transform | No | JSON | `{loc: [x,y,z], rot: [x,y,z], scale: [x,y,z]}` |
| Key frames | No | List[int] | Frame numbers for pin positions |
| Vertex mask groups | No | List[str] | Vertex group names to mask from tracking |

### Outputs

| Output | Format | Description |
|--------|--------|-------------|
| Untextured GLB | `.glb` | Raw geometry for tracking |
| Textured GLB | `.glb` | Textured geometry for rendering |
| Tracked Blender file | `.blend` | Scene with tracked animation |
| Composited frames | `.png` sequence | Final VFX frames |
| Pipeline metadata | `.json` | Timing, parameters, step results |

### Reference Files

| File | Source | Purpose |
|------|--------|---------|
| `3dmodelgeneration.json` | KeenTools example | Hunyuan3D ComfyUI workflow |
| `CameraTrack.blend` | KeenTools example | Reference Blender scene with GeoTracker setup |
| `Car.glb` | KeenTools example | Reference 3D model (car) |
| `5835604-hd_1920_1080_25fps.mp4` | KeenTools example | Reference tracking footage |

## Success Criteria

1. Pipeline generates a valid textured GLB from a single screenshot
2. GeoTracker successfully tracks the 3D model across all video frames
3. Composited output shows the 3D mesh correctly overlaid on the video
4. The example project files (Car.glb + video) produce a visually correct result
5. Pipeline runs end-to-end without manual intervention
