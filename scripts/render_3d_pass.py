"""Render the tracked 3D car as transparent RGBA frames (no compositor).

Blender's MovieClip compositor node doesn't load video in headless mode.
Instead we render the 3D layer only with film_transparent=True, producing
RGBA PNGs where the car is opaque and the background is transparent.
ffmpeg then composites these over the original video.

Material approach: Camera-projected video texture so the 3D car looks
like the real car from the footage. Procedural weathered-paint fallback
for surfaces not visible from the projection angle.
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
REF_FRAME_PATH = os.path.join(PROJECT_DIR, "exports", "vfx-composite", "ref_texture_frame.png")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "exports", "vfx-composite")
FRAME_PREFIX = os.path.join(OUTPUT_DIR, "render_")

print("=" * 60)
print("  3D Pass Render: Tracked Car (camera-projected texture)")
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

# =========================================================================
# Material: Camera-projected video texture + procedural weathered fallback
# =========================================================================
print(f"\n  Setting up camera-projected texture material...")

car.data.materials.clear()
mat = bpy.data.materials.new(name="CarProjected")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Clear default nodes
for n in list(nodes):
    nodes.remove(n)

# --- Output node ---
output = nodes.new("ShaderNodeOutputMaterial")
output.location = (1200, 0)

# --- Main Principled BSDF ---
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
bsdf.location = (800, 0)
bsdf.inputs["Metallic"].default_value = 0.3
bsdf.inputs["Roughness"].default_value = 0.55
bsdf.inputs["Alpha"].default_value = 1.0
links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

# --- Load reference frame as texture ---
ref_img = None
if os.path.exists(REF_FRAME_PATH):
    ref_img = bpy.data.images.load(REF_FRAME_PATH)
    print(f"  Loaded reference texture: {REF_FRAME_PATH}")
else:
    print(f"  WARNING: No reference frame at {REF_FRAME_PATH}")

if ref_img:
    # Camera-projected texture (from the tracked camera)
    tex_coord = nodes.new("ShaderNodeTexCoord")
    tex_coord.location = (-600, 200)
    tex_coord.object = cam  # Project from camera

    # Use Window coordinates for camera projection
    mapping = nodes.new("ShaderNodeMapping")
    mapping.location = (-400, 200)
    links.new(tex_coord.outputs["Window"], mapping.inputs["Vector"])

    img_tex = nodes.new("ShaderNodeTexImage")
    img_tex.location = (-200, 200)
    img_tex.image = ref_img
    img_tex.interpolation = 'Smart'
    img_tex.extension = 'CLIP'  # Don't tile - clip at edges
    links.new(mapping.outputs["Vector"], img_tex.inputs["Vector"])

    # --- Procedural fallback: weathered paint matching the real car ---
    # Real car is faded blue-grey with rust/brown patches
    noise = nodes.new("ShaderNodeTexNoise")
    noise.location = (-400, -200)
    noise.inputs["Scale"].default_value = 8.0
    noise.inputs["Detail"].default_value = 12.0
    noise.inputs["Roughness"].default_value = 0.7

    # Color ramp: mix between faded blue-grey and rust brown
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.location = (-200, -200)
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = (0.22, 0.25, 0.30, 1.0)  # Faded blue-grey
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = (0.35, 0.20, 0.12, 1.0)  # Rust brown
    links.new(noise.outputs["Fac"], ramp.inputs["Fac"])

    # Mix projected texture with procedural fallback
    # Use the projected texture's alpha to blend (CLIP mode = 0 alpha outside frame)
    mix_color = nodes.new("ShaderNodeMix")
    mix_color.location = (400, 100)
    mix_color.data_type = 'RGBA'
    # Use projected image alpha as factor (1.0 where projected, 0.0 outside)
    links.new(img_tex.outputs["Alpha"], mix_color.inputs["Factor"])
    links.new(ramp.outputs["Color"], mix_color.inputs[6])  # A (fallback)
    links.new(img_tex.outputs["Color"], mix_color.inputs[7])  # B (projected)

    links.new(mix_color.outputs[2], bsdf.inputs["Base Color"])

    # --- Roughness variation for realism ---
    rough_noise = nodes.new("ShaderNodeTexNoise")
    rough_noise.location = (-400, -500)
    rough_noise.inputs["Scale"].default_value = 15.0
    rough_noise.inputs["Detail"].default_value = 8.0

    rough_ramp = nodes.new("ShaderNodeValToRGB")
    rough_ramp.location = (-200, -500)
    rough_ramp.color_ramp.elements[0].position = 0.3
    rough_ramp.color_ramp.elements[0].color = (0.4, 0.4, 0.4, 1.0)  # Smoother paint
    rough_ramp.color_ramp.elements[1].position = 0.7
    rough_ramp.color_ramp.elements[1].color = (0.85, 0.85, 0.85, 1.0)  # Rough rust
    links.new(rough_noise.outputs["Fac"], rough_ramp.inputs["Fac"])
    links.new(rough_ramp.outputs["Color"], bsdf.inputs["Roughness"])

    print(f"  Material: camera-projected texture + procedural weathered fallback")
else:
    # No reference frame - pure procedural
    bsdf.inputs["Base Color"].default_value = (0.25, 0.28, 0.32, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.6
    print(f"  Material: procedural weathered paint (no reference texture)")

car.data.materials.append(mat)

# =========================================================================
# Lighting: match the desert outdoor scene
# =========================================================================
print(f"\n  Setting up desert environment lighting...")

# Remove existing lights
for obj in list(bpy.data.objects):
    if obj.type == 'LIGHT':
        bpy.data.objects.remove(obj, do_unlink=True)

# Key light (sun) - matching the video's harsh desert sunlight
# Video shows sun from upper-right based on shadows
bpy.ops.object.light_add(type='SUN', location=(5, -3, 8))
sun = bpy.context.active_object
sun.name = "KeyLight"
sun.data.energy = 5.0
sun.data.angle = math.radians(5)  # Sharp shadows like real sun
# Warm desert sunlight color
sun.data.color = (1.0, 0.95, 0.85)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(-25))

# Fill light (hemisphere-like, simulating sky bounce)
bpy.ops.object.light_add(type='AREA', location=(0, 0, 6))
fill = bpy.context.active_object
fill.name = "SkyFill"
fill.data.energy = 100.0
fill.data.size = 15.0  # Large soft area = sky-like
fill.data.color = (0.7, 0.78, 0.95)  # Cool blue sky color
fill.rotation_euler = (0, 0, 0)  # Pointing straight down

# Bounce light from ground
bpy.ops.object.light_add(type='AREA', location=(0, 2, -1))
bounce = bpy.context.active_object
bounce.name = "GroundBounce"
bounce.data.energy = 30.0
bounce.data.size = 10.0
bounce.data.color = (0.85, 0.75, 0.55)  # Warm desert ground bounce
bounce.rotation_euler = (math.radians(180), 0, 0)  # Pointing up

print(f"  Lights: Sun (5.0 warm) + SkyFill (100 cool blue) + GroundBounce (30 warm)")

# --- World: neutral for film_transparent ---
if not scene.world:
    scene.world = bpy.data.worlds.new("World")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    bg.inputs["Color"].default_value = (0.4, 0.45, 0.5, 1)
    bg.inputs["Strength"].default_value = 0.3  # Subtle ambient

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
    "material": "camera_projected_texture_with_procedural_fallback",
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
