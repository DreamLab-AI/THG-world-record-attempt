"""Render the tracked 3D car as transparent RGBA frames (no compositor).

Blender's MovieClip compositor node doesn't load video in headless mode.
Instead we render the 3D layer only with film_transparent=True, producing
RGBA PNGs where the car is opaque and the background is transparent.
ffmpeg then composites these over the original video.
"""

import bpy
import os
import sys
import json
import math
import glob

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
EXAMPLE_DIR = os.path.join(PROJECT_DIR, "assets", "keentools-example", "ComfyUI+GeoTracker_example")

VIDEO_PATH = os.path.join(EXAMPLE_DIR, "5835604-hd_1920_1080_25fps.mp4")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "exports", "vfx-composite")
FRAME_PREFIX = os.path.join(OUTPUT_DIR, "render_")

print("=" * 60)
print("  3D Pass Render: Tracked Car (transparent background)")
print("=" * 60)

scene = bpy.context.scene

# --- Fix clip path so scene frame range is correct ---
for c in bpy.data.movieclips:
    c.filepath = VIDEO_PATH
    break

scene.frame_start = 1
scene.frame_end = 314
scene.render.fps = 25

# --- Verify objects ---
car = bpy.data.objects.get("Car")
cam = bpy.data.objects.get("Camera")
if not car:
    print("ERROR: No Car object"); sys.exit(1)
if not cam:
    print("ERROR: No Camera object"); sys.exit(1)

car_anim = car.animation_data and car.animation_data.action
cam_anim = cam.animation_data and cam.animation_data.action
print(f"  Car: {len(car.data.vertices)} verts, animated={bool(car_anim)}")
print(f"  Camera: animated={bool(cam_anim)}")

# Fix rotation mode
if car.rotation_mode != 'XYZ':
    car.rotation_mode = 'XYZ'

# --- Material: solid opaque so car is clearly visible against transparency ---
car.data.materials.clear()
mat = bpy.data.materials.new(name="CarSolid")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    # Bright metallic blue-teal so it stands out over the video
    bsdf.inputs["Base Color"].default_value = (0.05, 0.3, 0.5, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = 0.15
    bsdf.inputs["Alpha"].default_value = 1.0
car.data.materials.append(mat)
print(f"  Material: metallic teal (fully opaque)")

# --- Lighting ---
# Remove existing lights
for obj in list(bpy.data.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# Key light (sun)
bpy.ops.object.light_add(type='SUN', location=(5, -3, 8))
sun = bpy.context.active_object
sun.name = "KeyLight"
sun.data.energy = 4.0
sun.data.angle = math.radians(15)
sun.rotation_euler = (math.radians(45), math.radians(15), math.radians(-30))

# Fill light (area, softer)
bpy.ops.object.light_add(type='AREA', location=(-3, -2, 4))
fill = bpy.context.active_object
fill.name = "FillLight"
fill.data.energy = 200.0
fill.data.size = 5.0
fill.rotation_euler = (math.radians(60), 0, math.radians(120))

print(f"  Lights: KeyLight (sun 4.0) + FillLight (area 200)")

# --- World: black so film_transparent works cleanly ---
if not scene.world:
    scene.world = bpy.data.worlds.new("World")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0, 0, 0, 1)
    bg.inputs["Strength"].default_value = 0.0

# --- Disable compositor (render 3D layer only) ---
scene.use_nodes = False
print(f"  Compositor: DISABLED (direct render)")

# --- Render settings ---
scene.render.engine = "BLENDER_EEVEE"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.resolution_percentage = 100
scene.render.fps = 25
scene.render.film_transparent = True  # Key: transparent background
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.image_settings.compression = 15
scene.render.filepath = FRAME_PREFIX
scene.camera = cam

try:
    scene.eevee.taa_render_samples = 64
except:
    pass

os.makedirs(OUTPUT_DIR, exist_ok=True)
print(f"  Engine: EEVEE, 1920x1080, 25fps, 314 frames")
print(f"  Output: {FRAME_PREFIX}####.png (RGBA, transparent bg)")

# --- Render ---
print(f"\n  Rendering 314 frames...")
bpy.ops.render.render(animation=True)

rendered = sorted(glob.glob(os.path.join(OUTPUT_DIR, "render_*.png")))
print(f"\n{'=' * 60}")
print(f"  Render complete: {len(rendered)} frames")
print(f"  Output: {OUTPUT_DIR}")
print(f"{'=' * 60}")

# Save metadata
meta = {
    "type": "3d_pass_render",
    "frames_rendered": len(rendered),
    "total_frames": 314,
    "resolution": [1920, 1080],
    "fps": 25,
    "render_engine": "BLENDER_EEVEE",
    "film_transparent": True,
    "compositor": False,
    "car_verts": len(car.data.vertices),
    "car_animated": bool(car_anim),
    "camera_animated": bool(cam_anim),
}
with open(os.path.join(OUTPUT_DIR, "render_3d_pass_meta.json"), "w") as f:
    json.dump(meta, f, indent=2)
