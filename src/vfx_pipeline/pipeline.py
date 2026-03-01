"""End-to-end 3D VFX Object Tracking Pipeline.

Usage:
    python -m vfx_pipeline.pipeline \\
        --video /path/to/video.mp4 \\
        --prompt "the red car" \\
        --output /tmp/vfx_output

Pipeline:
    1. SAM3 text-prompted segmentation (ComfyUI)
    2. SAM3D 3D reconstruction (ComfyUI)
    3. GeoTracker match-move (Blender MCP)
    4. VFX compositing + render (Blender MCP)
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Optional

from .comfyui_client import ComfyUIClient
from .blender_client import BlenderClient
from .workflows import (
    build_sam3_segmentation,
    build_sam3_video_segmentation,
    build_sam3d_reconstruction,
)
import glob as globmod


# ---------------------------------------------------------------------------
# Blender Python scripts (executed via MCP execute_python)
# ---------------------------------------------------------------------------

BLENDER_RESET_SCENE = """
import bpy
# Clear default scene
bpy.ops.wm.read_homefile(use_empty=True)
# Ensure keentools addon is enabled
try:
    bpy.ops.preferences.addon_enable(module='keentools')
    print("KeenTools addon enabled")
except Exception as e:
    print(f"KeenTools enable: {e}")
print("Scene reset complete")
"""

BLENDER_IMPORT_GLB = """
import bpy
filepath = "{glb_path}"
bpy.ops.import_scene.gltf(filepath=filepath)
# Get imported objects
imported = [o for o in bpy.context.selected_objects]
print(f"Imported {{len(imported)}} objects from {{filepath}}")
for obj in imported:
    print(f"  - {{obj.name}} ({{obj.type}})")
# Select the mesh object
meshes = [o for o in imported if o.type == 'MESH']
if meshes:
    bpy.context.view_layer.objects.active = meshes[0]
    print(f"Active mesh: {{meshes[0].name}}")
str(len(imported))
"""

BLENDER_LOAD_VIDEO_CLIP = """
import bpy
video_path = "{video_path}"
# Load as movie clip for tracking
clip = bpy.data.movieclips.load(video_path)
print(f"Loaded clip: {{clip.name}}, {{clip.size[0]}}x{{clip.size[1]}}, {{clip.frame_duration}} frames")
# Also set scene frame range to match
bpy.context.scene.frame_start = 1
bpy.context.scene.frame_end = clip.frame_duration
bpy.context.scene.render.fps = 24
print(f"Scene: frames 1-{{clip.frame_duration}}, 24fps")
str(clip.frame_duration)
"""

BLENDER_SETUP_GEOTRACKER = """
import bpy

# Get the mesh object (first mesh in scene)
mesh_obj = None
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mesh_obj = obj
        break

if not mesh_obj:
    raise ValueError("No mesh object found in scene")

# Get the movie clip
clip = None
for c in bpy.data.movieclips:
    clip = c
    break

if not clip:
    raise ValueError("No movie clip loaded")

print(f"Setting up GeoTracker: mesh={mesh_obj.name}, clip={clip.name}")

# Create GeoTracker
try:
    bpy.ops.keentools_gt.create_geotracker()
    print("GeoTracker created")
except Exception as e:
    print(f"Create GeoTracker: {e}")

# Access GeoTracker settings (API uses geotrackers collection + current_geotracker_num)
gt_settings = bpy.context.scene.keentools_gt_settings
gt_idx = gt_settings.current_geotracker_num
gt = gt_settings.geotrackers[gt_idx]

# Set up camera first (GeoTracker needs it)
cam = bpy.data.objects.get('Camera')
if not cam:
    bpy.ops.object.camera_add(location=(0, -5, 2))
    cam = bpy.context.active_object
    cam.name = 'Camera'
bpy.context.scene.camera = cam

# Assign geometry, clip, and camera to GeoTracker
gt.geomobj = mesh_obj
gt.camobj = cam
gt.movie_clip = clip

# Match render resolution to clip
bpy.context.scene.render.resolution_x = clip.size[0]
bpy.context.scene.render.resolution_y = clip.size[1]

print(f"GeoTracker configured: {mesh_obj.name} tracking in {clip.name}")
print(f"Resolution: {clip.size[0]}x{clip.size[1]}")
str("ready")
"""

BLENDER_GT_START_TRACKING = """
import bpy, time

# Enable precalcless mode
gt_settings = bpy.context.scene.keentools_gt_settings
gt = gt_settings.geotrackers[gt_settings.current_geotracker_num]
gt.precalcless = True

# Find 3D viewport
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    with bpy.context.temp_override(window=window, area=area, region=region):
                        bpy.ops.view3d.view_camera()
                        time.sleep(0.5)
                        bpy.ops.keentools_gt.pinmode('INVOKE_DEFAULT')
                        time.sleep(1)
                        bpy.ops.keentools_gt.magic_keyframe_btn()
                        time.sleep(1)
                        bpy.ops.keentools_gt.track_to_end_btn()
                    break
            break

print("Tracking started")
str("started")
"""

BLENDER_GT_CHECK_STATUS = """
import bpy
gt_settings = bpy.context.scene.keentools_gt_settings
mode = gt_settings.calculating_mode
pct = gt_settings.user_percent
if mode and mode != 'NONE':
    print(f"TRACKING: {mode} {pct:.0f}%")
else:
    print("IDLE")
str(mode)
"""

BLENDER_GT_BAKE_AND_EXIT = """
import bpy

# Find 3D viewport for context
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            for region in area.regions:
                if region.type == 'WINDOW':
                    with bpy.context.temp_override(window=window, area=area, region=region):
                        # Exit pinmode
                        try:
                            bpy.ops.keentools_gt.exit_pinmode_btn()
                            print("Exited pinmode")
                        except:
                            pass

                        # Bake animation to world space
                        try:
                            bpy.ops.keentools_gt.bake_animation_to_world(product=1)
                            print("Animation baked to world space")
                        except Exception as e:
                            print(f"Bake: {e}")
                            # Fallback: manually keyframe the mesh
                            try:
                                mesh = None
                                for obj in bpy.data.objects:
                                    if obj.type == 'MESH':
                                        mesh = obj
                                        break
                                if mesh:
                                    mesh.keyframe_insert(data_path='location', frame=1)
                                    mesh.keyframe_insert(data_path='rotation_euler', frame=1)
                                    print("Manual keyframe fallback applied")
                            except Exception as e2:
                                print(f"Manual keyframe: {e2}")
                    break
            break

str("baked")
"""

BLENDER_RUN_GEOTRACKER = """
import bpy
import time

print("Starting GeoTracker solve...")

# Enable precalcless mode (skip video analysis for scripted tracking)
gt_settings = bpy.context.scene.keentools_gt_settings
gt_idx = gt_settings.current_geotracker_num
gt = gt_settings.geotrackers[gt_idx]
gt.precalcless = True
print("Enabled precalcless mode")

# Find the 3D viewport for context override
view3d_area = None
view3d_region = None
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            view3d_area = area
            for region in area.regions:
                if region.type == 'WINDOW':
                    view3d_region = region
                    break
            break

if not view3d_area:
    raise RuntimeError("No 3D viewport found")

# All GeoTracker ops need to run inside context override
with bpy.context.temp_override(
    window=bpy.context.window_manager.windows[0],
    area=view3d_area,
    region=view3d_region,
):
    # Switch to camera view
    bpy.ops.view3d.view_camera()
    time.sleep(0.5)

    # Enter pinmode (required for tracking)
    try:
        bpy.ops.keentools_gt.pinmode('INVOKE_DEFAULT')
        print("Entered Pinmode")
        time.sleep(2)
    except Exception as e:
        print(f"Pinmode enter: {e}")

    # Magic keyframe for initial alignment
    try:
        bpy.ops.keentools_gt.magic_keyframe_btn()
        print("Magic keyframe placed")
        time.sleep(1)
    except Exception as e:
        print(f"Magic keyframe: {e}")

    # Track forward through video
    try:
        bpy.ops.keentools_gt.track_to_end_btn()
        print("Track to end started...")
        # Wait for async tracking to complete
        for i in range(120):
            time.sleep(5)
            if not gt_settings.calculating_mode or gt_settings.calculating_mode == 'NONE':
                break
            pct = gt_settings.user_percent
            print(f"  Tracking: {pct:.0f}%")
        print("Tracking complete")
    except Exception as e:
        print(f"Track to end: {e}")

    # Refine tracking
    try:
        bpy.ops.keentools_gt.refine_all_btn()
        print("Refine started...")
        for i in range(60):
            time.sleep(5)
            if not gt_settings.calculating_mode or gt_settings.calculating_mode == 'NONE':
                break
            pct = gt_settings.user_percent
            print(f"  Refining: {pct:.0f}%")
        print("Refinement complete")
    except Exception as e:
        print(f"Refine: {e}")

    # Exit pinmode
    try:
        bpy.ops.keentools_gt.exit_pinmode_btn()
        print("Exited Pinmode")
    except Exception as e:
        print(f"Exit pinmode: {e}")

# Bake animation to world space (product=1 = GEOTRACKER)
try:
    bpy.ops.keentools_gt.bake_animation_to_world(product=1)
    print("Animation baked to world space")
except Exception as e:
    print(f"Bake animation: {e}")

print("GeoTracker solve complete")
str("tracked")
"""

BLENDER_EXPORT_TRACKING = """
import bpy

output_path = "{output_path}"

# Export as Alembic (.abc) for tracked animation
abc_path = output_path + "/tracked_animation.abc"
bpy.ops.wm.alembic_export(
    filepath=abc_path,
    start=bpy.context.scene.frame_start,
    end=bpy.context.scene.frame_end,
    selected=False,
)
print(f"Exported Alembic: {{abc_path}}")
str(abc_path)
"""

BLENDER_ENSURE_LIGHTING = """
import bpy
scene = bpy.context.scene
# Add sun light if none exists
has_light = any(o.type == 'LIGHT' for o in bpy.data.objects)
if not has_light:
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    bpy.context.active_object.data.energy = 3.0
    print("Added sun light")
else:
    print("Light already exists")
str("ok")
"""

BLENDER_SETUP_COMPOSITOR = """
import bpy, os

video_path = "{video_path}"
output_path = "{output_path}"

scene = bpy.context.scene
scene.use_nodes = True

# Blender 5.x: scene.node_tree replaced by scene.compositing_node_group
cng = scene.compositing_node_group
if cng is None:
    cng = bpy.data.node_groups.new("Compositing", "CompositorNodeTree")
    scene.compositing_node_group = cng

# Clear existing nodes and interface sockets
for node in list(cng.nodes):
    cng.nodes.remove(node)
for item in list(cng.interface.items_tree):
    cng.interface.remove(item)

# Create output socket (replaces CompositorNodeComposite in 5.x)
cng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")

# Create nodes
clip_node = cng.nodes.new("CompositorNodeMovieClip")
render_layer = cng.nodes.new("CompositorNodeRLayers")
alpha_over = cng.nodes.new("CompositorNodeAlphaOver")
group_output = cng.nodes.new("NodeGroupOutput")
viewer = cng.nodes.new("CompositorNodeViewer")

clip_node.location = (-400, 200)
render_layer.location = (-400, -200)
alpha_over.location = (0, 0)
group_output.location = (400, 100)
viewer.location = (400, -100)

# Set movie clip
clip = None
for c in bpy.data.movieclips:
    clip = c
    break
if not clip:
    clip = bpy.data.movieclips.load(video_path)
if clip:
    clip_node.clip = clip

# Blender 5.x AlphaOver inputs: [0]=Background, [1]=Foreground, [2]=Factor
cng.links.new(clip_node.outputs["Image"], alpha_over.inputs["Background"])
cng.links.new(render_layer.outputs["Image"], alpha_over.inputs["Foreground"])
cng.links.new(alpha_over.outputs["Image"], group_output.inputs["Image"])
cng.links.new(alpha_over.outputs["Image"], viewer.inputs["Image"])

# Ensure world exists for EEVEE lighting
if not scene.world:
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

# Render settings (Blender 5.x: BLENDER_EEVEE, PNG frames)
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = clip.size[0] if clip else 1920
scene.render.resolution_y = clip.size[1] if clip else 1080
scene.render.fps = 24
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = output_path + "/composited_"
scene.render.film_transparent = True

os.makedirs(output_path, exist_ok=True)

print(f"Compositor setup complete")
print(f"Output: {{scene.render.filepath}}")
str("compositor_ready")
"""

BLENDER_RENDER = """
import bpy
print("Starting render...")
bpy.ops.render.render(animation=True)
print("Render complete: " + bpy.context.scene.render.filepath)
str("rendered")
"""


class VFXPipeline:
    """Orchestrates the full SAM3 → SAM3D → GeoTracker → Compositing pipeline."""

    def __init__(
        self,
        comfyui_url: str = "http://comfyui:8188",
        blender_url: str = "ws://127.0.0.1:8765",
    ):
        self.comfy = ComfyUIClient(comfyui_url)
        self.blender_url = blender_url
        self.output_dir = None

    def _ensure_output_dir(self, output_path: str) -> Path:
        p = Path(output_path)
        p.mkdir(parents=True, exist_ok=True)
        self.output_dir = p
        return p

    # ------------------------------------------------------------------
    # Step 1: SAM3 segmentation
    # ------------------------------------------------------------------

    def step1_segment(
        self,
        image_path: str,
        text_prompt: str,
        confidence: float = 0.4,
    ) -> dict:
        """Segment an object from a single image using SAM3 text prompt."""
        print(f"\n[1/4] SAM3 Segmentation: '{text_prompt}'")

        filename = Path(image_path).name
        # Upload if it's not already in ComfyUI input
        if not image_path.startswith("/root/ComfyUI"):
            print(f"  Uploading {filename}...")
            filename = self.comfy.upload_image(image_path)

        workflow = build_sam3_segmentation(filename, text_prompt, confidence)
        outputs = self.comfy.run_workflow(workflow, timeout=300)

        # Extract visualization path
        viz_path = self.comfy.get_output_path(outputs, "40", "images")
        print(f"  Segmentation viz: {viz_path}")

        return {"outputs": outputs, "viz": viz_path, "input_image": filename}

    def step1_segment_video(
        self,
        video_path: str,
        text_prompt: str,
        confidence: float = 0.4,
        max_frames: int = 30,
        every_nth: int = 5,
    ) -> dict:
        """Segment an object across video frames."""
        print(f"\n[1/4] SAM3 Video Segmentation: '{text_prompt}'")

        filename = Path(video_path).name
        workflow = build_sam3_video_segmentation(
            filename, text_prompt, confidence, max_frames, every_nth
        )
        outputs = self.comfy.run_workflow(workflow, timeout=600)

        viz_path = self.comfy.get_output_path(outputs, "40", "images")
        print(f"  Video segmentation viz: {viz_path}")

        return {"outputs": outputs, "viz": viz_path}

    # ------------------------------------------------------------------
    # Step 2: SAM3D 3D reconstruction
    # ------------------------------------------------------------------

    def step2_reconstruct(
        self,
        image_filename: str,
        seed: int = 42,
        texture_mode: str = "fast",
        texture_size: int = 1024,
    ) -> dict:
        """Reconstruct 3D mesh from segmented image using SAM3D."""
        print(f"\n[2/4] SAM3D 3D Reconstruction")
        print("  Loading SAM3D models (~30s)...")

        # Free GPU memory from segmentation before loading SAM3D
        print("  Freeing GPU memory...")
        self.comfy.free_memory()
        time.sleep(3)

        workflow = build_sam3d_reconstruction(
            image_filename,
            seed=seed,
            texture_mode=texture_mode,
            texture_size=texture_size,
        )
        outputs = self.comfy.run_workflow(workflow, timeout=600)

        # TextureBake (node 60) outputs glb_filepath as result[0]
        glb_path = self.comfy.get_output_path(outputs, "60")
        if not glb_path:
            # Try Preview3D node (70) which also references the path
            glb_path = self.comfy.get_output_path(outputs, "70")
        print(f"  Textured GLB: {glb_path}")

        return {
            "outputs": outputs,
            "glb_path": glb_path,
        }

    # ------------------------------------------------------------------
    # Step 3: GeoTracker
    # ------------------------------------------------------------------

    def step3_track(self, glb_path: str, video_path: str) -> dict:
        """Import mesh + video into Blender and run GeoTracker."""
        print(f"\n[3/4] GeoTracker 3D Match-Move")

        # Free ComfyUI GPU memory before Blender work
        print("  Freeing ComfyUI GPU memory...")
        self.comfy.free_memory()
        time.sleep(2)

        with BlenderClient(self.blender_url) as blender:
            # Reset scene
            print("  Resetting Blender scene...")
            blender.execute_python(BLENDER_RESET_SCENE)

            # Import GLB mesh
            print(f"  Importing mesh: {glb_path}")
            blender.execute_python(BLENDER_IMPORT_GLB.format(glb_path=glb_path))

            # Load video clip
            print(f"  Loading video: {video_path}")
            blender.execute_python(BLENDER_LOAD_VIDEO_CLIP.format(video_path=video_path))

            # Setup GeoTracker
            print("  Configuring GeoTracker...")
            blender.execute_python(BLENDER_SETUP_GEOTRACKER)

            # Start tracking (split into separate calls for event loop)
            print("  Starting GeoTracker tracking...")
            blender.execute_python(BLENDER_GT_START_TRACKING, timeout=30)

            # Wait for tracking to complete (check in separate calls)
            print("  Waiting for tracking to complete...")
            for i in range(60):
                time.sleep(10)
                result = blender.execute_python(BLENDER_GT_CHECK_STATUS, timeout=10)
                stdout = result.get("stdout", "")
                if "DONE" in stdout:
                    print("  Tracking complete!")
                    break
                if "IDLE" in stdout:
                    print("  Tracking finished (idle)")
                    break
            else:
                print("  Tracking timed out, stopping...")
                blender.execute_python(
                    "import bpy; bpy.ops.keentools_gt.stop_calculating_btn()",
                    timeout=10,
                )

            # Bake and export
            print("  Baking animation...")
            blender.execute_python(BLENDER_GT_BAKE_AND_EXIT, timeout=60)

            # Export tracked animation
            output_path = str(self.output_dir) if self.output_dir else "/tmp/vfx_output"
            print(f"  Exporting tracked animation...")
            blender.execute_python(
                BLENDER_EXPORT_TRACKING.format(output_path=output_path),
                timeout=120,
            )

        return {"status": "tracked", "output_dir": output_path}

    # ------------------------------------------------------------------
    # Step 4: Compositing + Render
    # ------------------------------------------------------------------

    def step4_composite(self, video_path: str) -> dict:
        """Set up compositor and render final output."""
        print(f"\n[4/4] VFX Compositing + Render")

        output_path = str(self.output_dir) if self.output_dir else "/tmp/vfx_output"

        with BlenderClient(self.blender_url) as blender:
            # Ensure scene has lighting (use_empty=True scenes don't)
            print("  Ensuring scene lighting...")
            blender.execute_python(BLENDER_ENSURE_LIGHTING)

            # Setup compositor
            print("  Setting up compositor nodes...")
            blender.execute_python(
                BLENDER_SETUP_COMPOSITOR.format(
                    video_path=video_path, output_path=output_path
                )
            )

            # Render
            print("  Rendering composited animation...")
            blender.execute_python(BLENDER_RENDER, timeout=3600)

        print(f"\n  Output: {output_path}/composited_*.png")
        return {"status": "rendered", "output_path": output_path}

    # ------------------------------------------------------------------
    # Full pipeline
    # ------------------------------------------------------------------

    def run(
        self,
        video_path: str,
        text_prompt: str,
        output_path: str = "/tmp/vfx_output",
        confidence: float = 0.4,
        seed: int = 42,
        texture_mode: str = "fast",
        skip_to: Optional[int] = None,
        glb_override: Optional[str] = None,
    ) -> dict:
        """Run the full pipeline end-to-end.

        Args:
            video_path: Path to input video
            text_prompt: Object to segment (e.g. "the red car")
            output_path: Directory for outputs
            confidence: SAM3 detection confidence threshold
            seed: Random seed for SAM3D
            texture_mode: "fast" (~5s) or "opt" (~60s)
            skip_to: Skip to step N (2=SAM3D, 3=GeoTracker, 4=composite)
            glb_override: Use existing GLB instead of running steps 1-2
        """
        out = self._ensure_output_dir(output_path)
        results = {}

        print("=" * 60)
        print("  3D VFX Object Tracking Pipeline")
        print(f"  Video: {video_path}")
        print(f"  Prompt: '{text_prompt}'")
        print(f"  Output: {output_path}")
        print("=" * 60)

        # Determine the image for SAM3D (first frame or best frame from segmentation)
        image_for_3d = None
        glb_path = glb_override

        if not skip_to or skip_to <= 1:
            # Step 1: Segment the first frame to find the object
            # For now, use first frame extraction via a simple workflow
            seg_result = self.step1_segment(
                video_path, text_prompt, confidence
            )
            results["step1"] = seg_result
            # The segmentation visualization shows what was detected
            image_for_3d = seg_result["input_image"]

        if not glb_path and (not skip_to or skip_to <= 2):
            # Step 2: 3D reconstruct from the segmented frame
            if not image_for_3d:
                raise ValueError("No image for 3D reconstruction. Run step 1 first.")
            recon_result = self.step2_reconstruct(
                image_for_3d, seed=seed, texture_mode=texture_mode
            )
            results["step2"] = recon_result
            glb_path = recon_result.get("glb_path")

        if not glb_path:
            raise ValueError("No GLB mesh available. Run steps 1-2 or provide --glb-override.")

        if not skip_to or skip_to <= 3:
            # Step 3: GeoTracker
            track_result = self.step3_track(glb_path, video_path)
            results["step3"] = track_result

        if not skip_to or skip_to <= 4:
            # Step 4: Composite + Render
            comp_result = self.step4_composite(video_path)
            results["step4"] = comp_result

        print("\n" + "=" * 60)
        print("  Pipeline complete!")
        print(f"  Output directory: {output_path}")
        print("=" * 60)

        # Save pipeline metadata
        meta_path = out / "pipeline_metadata.json"
        with open(meta_path, "w") as f:
            json.dump(
                {
                    "video": video_path,
                    "text_prompt": text_prompt,
                    "seed": seed,
                    "glb_path": glb_path,
                    "steps_completed": list(results.keys()),
                },
                f,
                indent=2,
            )

        return results


def main():
    parser = argparse.ArgumentParser(description="3D VFX Object Tracking Pipeline")
    parser.add_argument("--video", required=True, help="Path to input video")
    parser.add_argument("--prompt", required=True, help="Text prompt for object segmentation")
    parser.add_argument("--output", default="/tmp/vfx_output", help="Output directory")
    parser.add_argument("--confidence", type=float, default=0.4, help="SAM3 confidence threshold")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for SAM3D")
    parser.add_argument("--texture-mode", choices=["fast", "opt"], default="fast")
    parser.add_argument("--skip-to", type=int, choices=[1, 2, 3, 4], help="Skip to step N")
    parser.add_argument("--glb-override", help="Use existing GLB mesh (skip steps 1-2)")
    parser.add_argument("--comfyui-url", default="http://comfyui:8188")
    parser.add_argument("--blender-url", default="ws://127.0.0.1:8765")

    args = parser.parse_args()

    pipeline = VFXPipeline(args.comfyui_url, args.blender_url)
    pipeline.run(
        video_path=args.video,
        text_prompt=args.prompt,
        output_path=args.output,
        confidence=args.confidence,
        seed=args.seed,
        texture_mode=args.texture_mode,
        skip_to=args.skip_to,
        glb_override=args.glb_override,
    )


if __name__ == "__main__":
    main()
