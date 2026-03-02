# DDD: VFX Object Tracking Pipeline v2 — Domain-Driven Design

## Strategic Design

### Domain: VFX Object Tracking
The system bridges two bounded contexts — **3D Asset Generation** (ComfyUI) and **3D Motion Tracking + Compositing** (Blender) — to produce VFX shots where a generated 3D model follows a real object in video footage.

### Bounded Contexts

```
┌──────────────────────────┐     ┌──────────────────────────────────┐
│  3D Generation Context   │     │  Tracking & Compositing Context  │
│  (ComfyUI)               │     │  (Blender + GeoTracker)          │
│                          │     │                                  │
│  Entities:               │     │  Entities:                       │
│  - Screenshot            │ GLB │  - BlenderScene                  │
│  - BackgroundMask        │────►│  - TrackedMesh                   │
│  - UntexturedMesh        │     │  - VideoClip                     │
│  - TexturedMesh          │     │  - GeoTrackerInstance             │
│  - GenerationWorkflow    │     │  - TrackingPin                   │
│                          │     │  - VertexMask                    │
│  Value Objects:          │     │  - CompositorGraph               │
│  - Seed                  │     │  - RenderedFrameSequence         │
│  - TextureMode           │     │                                  │
│  - Resolution            │     │  Value Objects:                  │
│                          │     │  - Transform (loc/rot/scale)     │
│  Services:               │     │  - FrameRange                    │
│  - ComfyUIClient         │     │  - RenderSettings                │
│                          │     │  - PinPosition                   │
│                          │     │                                  │
│                          │     │  Services:                       │
│                          │     │  - BlenderClient                 │
└──────────────────────────┘     └──────────────────────────────────┘
```

### Context Map

The **3D Generation Context** is upstream; it produces a GLB artifact consumed by the **Tracking Context** downstream. The integration is via a **Shared Kernel** — the GLB file format — with a **Conformist** relationship (Blender conforms to whatever GLB structure ComfyUI produces, and must fix rotation/parenting issues itself).

## Tactical Design

### Aggregate: PipelineRun

The root aggregate that coordinates the entire pipeline execution.

```python
@dataclass
class PipelineRun:
    """Root aggregate for a single pipeline execution."""
    id: str                          # UUID
    video_path: str                  # Input video
    screenshot_path: Optional[str]   # Input screenshot (None if GLB provided)
    glb_path: Optional[str]          # Pre-made GLB or generated GLB
    output_dir: str                  # Output directory
    object_name: str                 # Name for tracked mesh

    # Step results
    generation_result: Optional[GenerationResult]
    scene_result: Optional[SceneResult]
    tracking_result: Optional[TrackResult]
    composite_result: Optional[CompositeResult]

    # State
    current_step: PipelineStep       # Enum: PENDING, GENERATING, SCENE_SETUP, TRACKING, COMPOSITING, DONE, FAILED
    error: Optional[str]

    def advance(self) -> PipelineStep:
        """State machine transition."""
```

### Entity: TrackedMesh

Represents the 3D model as it moves through the pipeline.

```python
@dataclass
class TrackedMesh:
    """The 3D model being tracked."""
    name: str                        # "quad_bike", "car", etc.
    glb_path: str                    # Path to GLB file
    blender_object_name: str         # Name in Blender scene after import

    # GLB import fixups (from tutorial)
    rotation_mode: str = "XYZ"       # Must convert from QUATERNION
    parent_cleared: bool = False     # Must unparent from GLB empty

    # Tracking state
    vertex_mask_groups: list[str] = field(default_factory=list)  # e.g., ["wheels"]
    pin_frames: list[int] = field(default_factory=list)
    is_tracked: bool = False
    keyframe_count: int = 0
```

### Entity: GeoTrackerInstance

Represents the GeoTracker solver state in Blender.

```python
@dataclass
class GeoTrackerInstance:
    """A GeoTracker instance in the Blender scene."""
    index: int                       # gt_settings.current_geotracker_num
    geometry_object: str             # Mesh object name
    camera_object: str               # Camera name
    movie_clip: str                  # Clip name

    # Analysis state
    clip_analyzed: bool = False
    precalcless: bool = True         # Skip precalc for scripted tracking

    # Tracking state
    tracking_mode: str = "NONE"      # NONE, TRACKING, REFINING
    progress_percent: float = 0.0

    # Surface mask
    mask_vertex_group: Optional[str] = None
```

### Value Object: Transform

```python
@dataclass(frozen=True)
class Transform:
    """Immutable 3D transform for model alignment."""
    location: tuple[float, float, float] = (0, 0, 0)
    rotation_euler: tuple[float, float, float] = (0, 0, 0)
    scale: tuple[float, float, float] = (1, 1, 1)
```

### Value Object: GenerationResult

```python
@dataclass(frozen=True)
class GenerationResult:
    """Output of the 3D generation step."""
    untextured_glb_path: str
    textured_glb_path: str
    seed: int
    duration_seconds: float
    vertex_count: int
```

### Value Object: TrackResult

```python
@dataclass(frozen=True)
class TrackResult:
    """Output of the GeoTracker tracking step."""
    status: str                      # "tracked", "partial", "failed"
    keyframe_count: int
    frames_tracked: int
    total_frames: int
    blend_file_path: str
    duration_seconds: float
```

### Value Object: CompositeResult

```python
@dataclass(frozen=True)
class CompositeResult:
    """Output of the compositing step."""
    output_dir: str
    frame_count: int
    resolution: tuple[int, int]
    render_engine: str
    duration_seconds: float
```

### Domain Service: GLBPreparer

Encapsulates the critical GLB import fixup logic from the tutorial.

```python
class GLBPreparer:
    """Fixes imported GLB models for GeoTracker compatibility.

    Tutorial requirements:
    1. Convert rotation mode from Quaternion to XYZ Euler
    2. Clear parent connections (unparent from empty)
    3. Delete orphan empty objects
    4. Rename primary mesh
    """

    @staticmethod
    def build_preparation_script(mesh_name: str) -> str:
        """Generate Blender Python that prepares the GLB."""
```

### Domain Service: PinStrategy

Determines where to place tracking pins.

```python
class PinStrategy:
    """Determines keyframe pin positions for GeoTracker."""

    @staticmethod
    def evenly_spaced(total_frames: int, pin_count: int = 5) -> list[int]:
        """Place pins at evenly spaced intervals."""

    @staticmethod
    def from_user(frames: list[int]) -> list[int]:
        """Use user-specified frame numbers."""
```

### Domain Service: StepValidator

Validates outputs between pipeline steps.

```python
class StepValidator:
    """Validates step outputs before allowing progression."""

    @staticmethod
    def validate_glb(path: str) -> ValidationResult:
        """Check GLB exists, has valid header, reasonable size."""

    @staticmethod
    def validate_scene_setup(blender_result: dict) -> ValidationResult:
        """Check mesh loaded, GeoTracker configured, clip has frames."""

    @staticmethod
    def validate_tracking(blender_result: dict) -> ValidationResult:
        """Check animation keyframes exist on mesh object."""

    @staticmethod
    def validate_composite(output_dir: str, expected_frames: int) -> ValidationResult:
        """Check output PNG files exist and count matches."""
```

## Domain Events

| Event | Triggered When | Data |
|-------|---------------|------|
| `GLBGenerated` | Hunyuan3D completes | glb_path, vertex_count, duration |
| `SceneReady` | Blender scene fully configured | mesh_name, clip_frames, geotracker_index |
| `TrackingStarted` | GeoTracker begins tracking | pin_count, direction |
| `TrackingProgress` | Polling detects progress | percent, mode |
| `TrackingCompleted` | GeoTracker finishes | keyframe_count, frames_tracked |
| `CompositeRendered` | All frames rendered | frame_count, output_dir |
| `PipelineCompleted` | All steps done | total_duration, output_summary |
| `StepFailed` | Validation gate fails | step, error_message |

## Anti-Corruption Layer

The `GLBPreparer` service acts as an anti-corruption layer between the ComfyUI generation context and the Blender tracking context. It translates the raw GLB import (with quaternion rotations, empty parents, generic names) into a clean mesh ready for GeoTracker.

```
ComfyUI GLB Output ──► GLBPreparer (ACL) ──► Clean TrackedMesh in Blender
  - QUATERNION rotation    converts to         - XYZ Euler rotation
  - Parented to Empty      clears to           - No parent
  - Generic name           renames to          - "quad_bike" etc.
```

## Ubiquitous Language

| Term | Definition |
|------|-----------|
| **Pin** | A manually placed correspondence point between the 3D model and the 2D footage at a specific frame |
| **Pin Mode** | GeoTracker's interactive alignment mode where pins are placed |
| **Magic Keyframe** | GeoTracker's automatic initial alignment (attempts to match model to footage without manual pins) |
| **Refine All** | GeoTracker's interpolation solver that calculates smooth animation between pinned keyframes |
| **Bake to World** | Converting GeoTracker's internal tracking data into standard Blender keyframe animation |
| **Precalcless Mode** | Skip GeoTracker's video pre-analysis (useful for scripted/headless workflows) |
| **Surface Mask** | A vertex group that tells GeoTracker to ignore certain parts of the mesh during tracking (e.g., rotating wheels) |
| **Clip Analysis** | GeoTracker's pre-computation of optical flow features from the video clip |
| **AlphaOver** | Blender's compositor node that layers a foreground (3D render) over a background (video) using alpha transparency |
| **Compositing Node Group** | Blender 5.x's replacement for the old scene.node_tree compositor API |
| **Hunyuan3D** | Tencent's open-source image-to-3D model (DIT architecture) used for mesh generation |
| **Delight** | Removing lighting information from an image to produce flat/neutral textures suitable for relighting |
| **GLB** | Binary glTF format for 3D models — the interchange format between ComfyUI generation and Blender tracking |

## Module Map

```
src/vfx_pipeline/
│
├── domain/                    # Domain layer (no external deps)
│   ├── entities.py            # PipelineRun, TrackedMesh, GeoTrackerInstance
│   ├── value_objects.py       # Transform, GenerationResult, TrackResult, etc.
│   ├── events.py              # Domain events
│   └── services.py            # GLBPreparer, PinStrategy, StepValidator
│
├── infrastructure/            # Infrastructure layer
│   ├── comfyui_client.py      # HTTP/WS client for ComfyUI
│   ├── blender_client.py      # WebSocket client for Blender MCP
│   └── blender_scripts.py     # All Blender Python script strings
│
├── application/               # Application layer
│   ├── pipeline.py            # VFXPipeline orchestrator
│   └── workflows.py           # ComfyUI workflow builders
│
├── __init__.py
└── __main__.py                # CLI entry point
```
