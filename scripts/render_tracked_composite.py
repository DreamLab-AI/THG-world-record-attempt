"""Render the GeoTracker-tracked Car.glb composited over video footage.

This script:
1. Opens the KeenTools reference CameraTrack.blend (contains completed tracking)
2. Fixes the video clip path to point to our actual file
3. Verifies the tracked animation data on both Camera and Car mesh
4. Sets up the Blender 5.x compositor (video background + 3D render overlay)
5. Configures EEVEE with proper lighting and materials
6. Renders to PNG frame sequence
7. Validates output frames

Usage (headless):
    blender --background CameraTrack.blend --python render_tracked_composite.py

The rendered frames can then be encoded to MP4 via ffmpeg.
"""

import bpy
import os
import sys
import json
import math

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
EXAMPLE_DIR = os.path.join(PROJECT_DIR, "assets", "keentools-example", "ComfyUI+GeoTracker_example")

VIDEO_PATH = os.path.join(EXAMPLE_DIR, "5835604-hd_1920_1080_25fps.mp4")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "exports", "vfx-composite")
FRAME_PREFIX = os.path.join(OUTPUT_DIR, "frame_")

# ---------------------------------------------------------------------------
# Step 1: Fix video clip path
# ---------------------------------------------------------------------------

print("=" * 60)
print("  VFX Composite Render: GeoTracker Car over Video")
print("=" * 60)

scene = bpy.context.scene

# The reference blend has a relative clip path that won't resolve.
# Re-link it to our actual video file.
clip = None
for c in bpy.data.movieclips:
    clip = c
    break

if clip:
    old_path = clip.filepath
    clip.filepath = VIDEO_PATH
    print(f"[1/7] Fixed clip path: {old_path} -> {VIDEO_PATH}")
    # Force clip to re-read by toggling frame (Blender 5.x has no clip.reload())
    try:
        clip.reload()
    except AttributeError:
        pass  # 5.x doesn't have reload; setting filepath is sufficient
    print(f"       Clip: {clip.name}, {clip.frame_duration} frames")
else:
    print("[1/7] No clip found, loading from scratch...")
    clip = bpy.data.movieclips.load(VIDEO_PATH)
    print(f"       Loaded: {clip.name}, {clip.size[0]}x{clip.size[1]}, {clip.frame_duration} frames")

# Set scene frame range to match clip
scene.frame_start = 1
scene.frame_end = clip.frame_duration
scene.render.fps = 25  # Match video's actual FPS

# ---------------------------------------------------------------------------
# Step 2: Verify tracked animation data
# ---------------------------------------------------------------------------

print(f"\n[2/7] Verifying tracked animation...")

car_obj = bpy.data.objects.get("Car")
cam_obj = bpy.data.objects.get("Camera")

if not car_obj:
    print("  ERROR: No 'Car' mesh object found!")
    sys.exit(1)

if not cam_obj:
    print("  ERROR: No 'Camera' object found!")
    sys.exit(1)

# Check Car has animation
car_has_anim = car_obj.animation_data and car_obj.animation_data.action
cam_has_anim = cam_obj.animation_data and cam_obj.animation_data.action

print(f"  Car '{car_obj.name}': {car_obj.data.vertices.__len__()} verts, "
      f"rot_mode={car_obj.rotation_mode}, "
      f"animated={'YES (' + car_obj.animation_data.action.name + ')' if car_has_anim else 'NO'}")
print(f"  Camera '{cam_obj.name}': "
      f"animated={'YES (' + cam_obj.animation_data.action.name + ')' if cam_has_anim else 'NO'}")

if not car_has_anim:
    print("  WARNING: Car has no tracked animation! Composite will show static mesh.")
if not cam_has_anim:
    print("  WARNING: Camera has no animation! Tracking may not be applied.")

# Verify rotation mode is XYZ (tutorial requirement)
if car_obj.rotation_mode != 'XYZ':
    print(f"  Fixing rotation mode: {car_obj.rotation_mode} -> XYZ")
    car_obj.rotation_mode = 'XYZ'

# ---------------------------------------------------------------------------
# Step 3: Set up material on car for visibility
# ---------------------------------------------------------------------------

print(f"\n[3/7] Setting up car material...")

# Check if car already has a valid material
existing_mat = None
if car_obj.data.materials:
    for m in car_obj.data.materials:
        if m is not None:
            existing_mat = m
            break

if existing_mat:
    mat = existing_mat
    print(f"  Existing material: {mat.name}")
else:
    # Create a visible material so the car shows up in the render
    mat = bpy.data.materials.new(name="CarTracked")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        # Semi-transparent blue-grey to show it's a CG overlay
        bsdf.inputs["Base Color"].default_value = (0.15, 0.25, 0.4, 1.0)
        bsdf.inputs["Metallic"].default_value = 0.8
        bsdf.inputs["Roughness"].default_value = 0.2
        # Make slightly transparent so video shows through
        bsdf.inputs["Alpha"].default_value = 0.85
    try:
        mat.blend_method = 'BLEND'
    except:
        pass  # Blender 5.x may not have blend_method
    # Clear any None material slots and assign our material
    car_obj.data.materials.clear()
    car_obj.data.materials.append(mat)
    print(f"  Created material: {mat.name} (metallic blue-grey, 85% opacity)")

# ---------------------------------------------------------------------------
# Step 4: Set up lighting
# ---------------------------------------------------------------------------

print(f"\n[4/7] Setting up lighting...")

# Add a sun light if none exists
has_light = any(o.type == 'LIGHT' for o in bpy.data.objects)
if not has_light:
    bpy.ops.object.light_add(type='SUN', location=(5, -3, 8))
    sun = bpy.context.active_object
    sun.name = "Sun"
    sun.data.energy = 3.0
    sun.data.angle = math.radians(10)
    print(f"  Added Sun light: energy=3.0")
else:
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT':
            print(f"  Existing light: {obj.name} ({obj.data.type}, energy={obj.data.energy})")

# Set up world/environment
if not scene.world:
    world = bpy.data.worlds.new("World")
    scene.world = world
world = scene.world
world.use_nodes = True
bg = world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.6, 0.65, 0.7, 1.0)
    bg.inputs["Strength"].default_value = 0.8
    print(f"  World background: cool grey, strength=0.8")

# ---------------------------------------------------------------------------
# Step 5: Set up compositor (Blender 5.x)
# ---------------------------------------------------------------------------

print(f"\n[5/7] Setting up compositor (Blender 5.x)...")

scene.use_nodes = True

# Blender 5.x uses compositing_node_group
cng = None
try:
    cng = scene.compositing_node_group
    if cng is None:
        cng = bpy.data.node_groups.new("Compositing", "CompositorNodeTree")
        scene.compositing_node_group = cng
    print(f"  Using compositing_node_group (Blender 5.x)")
except AttributeError:
    # Blender 4.x fallback
    cng = scene.node_tree
    print(f"  Using scene.node_tree (Blender 4.x fallback)")

# Clear existing nodes
for node in list(cng.nodes):
    cng.nodes.remove(node)

# Clear interface sockets (5.x)
try:
    for item in list(cng.interface.items_tree):
        cng.interface.remove(item)
    cng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    use_5x = True
    print(f"  Created output socket (5.x API)")
except:
    use_5x = False

# Create nodes
clip_node = cng.nodes.new("CompositorNodeMovieClip")
clip_node.location = (-400, 200)
clip_node.clip = clip

render_layer = cng.nodes.new("CompositorNodeRLayers")
render_layer.location = (-400, -200)

alpha_over = cng.nodes.new("CompositorNodeAlphaOver")
alpha_over.location = (100, 0)

if use_5x:
    output_node = cng.nodes.new("NodeGroupOutput")
else:
    output_node = cng.nodes.new("CompositorNodeComposite")
output_node.location = (400, 100)

viewer = cng.nodes.new("CompositorNodeViewer")
viewer.location = (400, -100)

# Link: video -> AlphaOver background, render -> AlphaOver foreground
# Blender 5.x AlphaOver inputs are indexed: 0=Fac, 1=Image, 2=Image_001
cng.links.new(clip_node.outputs["Image"], alpha_over.inputs[1])   # Background
cng.links.new(render_layer.outputs["Image"], alpha_over.inputs[2]) # Foreground (3D)

if use_5x:
    cng.links.new(alpha_over.outputs["Image"], output_node.inputs["Image"])
else:
    cng.links.new(alpha_over.outputs["Image"], output_node.inputs["Image"])
cng.links.new(alpha_over.outputs["Image"], viewer.inputs["Image"])

print(f"  Compositor: MovieClip -> AlphaOver <- RenderLayer -> Output")

# ---------------------------------------------------------------------------
# Step 6: Configure render settings
# ---------------------------------------------------------------------------

print(f"\n[6/7] Configuring render...")

scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = 25
scene.render.film_transparent = True  # Transparent background for 3D layer
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.filepath = FRAME_PREFIX

# EEVEE settings
try:
    eevee = scene.eevee
    eevee.taa_render_samples = 32
    print(f"  EEVEE: 32 samples")
except:
    pass

# Ensure camera is active
scene.camera = cam_obj
print(f"  Engine: EEVEE, 1920x1080, 25fps, {clip.frame_duration} frames")
print(f"  Output: {FRAME_PREFIX}####.png")

# Make output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Step 7: Render
# ---------------------------------------------------------------------------

print(f"\n[7/7] Rendering {clip.frame_duration} frames...")
print("  This will take a while in background mode...")

bpy.ops.render.render(animation=True)

# Count rendered frames
import glob
rendered = sorted(glob.glob(os.path.join(OUTPUT_DIR, "frame_*.png")))
print(f"\n{'=' * 60}")
print(f"  Render complete: {len(rendered)} frames")
print(f"  Output: {OUTPUT_DIR}")
print(f"{'=' * 60}")

# Save metadata
meta = {
    "source_blend": "CameraTrack.blend",
    "video": VIDEO_PATH,
    "output_dir": OUTPUT_DIR,
    "frames_rendered": len(rendered),
    "total_frames": clip.frame_duration,
    "resolution": [1920, 1080],
    "fps": 25,
    "render_engine": "BLENDER_EEVEE",
    "car_mesh": {
        "name": car_obj.name,
        "verts": len(car_obj.data.vertices),
        "faces": len(car_obj.data.polygons),
        "animated": car_has_anim,
        "action": car_obj.animation_data.action.name if car_has_anim else None,
    },
    "camera": {
        "animated": cam_has_anim,
        "action": cam_obj.animation_data.action.name if cam_has_anim else None,
    },
}
meta_path = os.path.join(OUTPUT_DIR, "render_metadata.json")
with open(meta_path, "w") as f:
    json.dump(meta, f, indent=2)
print(f"  Metadata: {meta_path}")
