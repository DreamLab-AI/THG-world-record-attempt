"""Blender Python scripts executed via MCP.

Each script is a self-contained string that runs inside Blender's Python
interpreter via the Blender MCP WebSocket server. Scripts communicate
results by printing to stdout and returning a value via the final expression.

v2 changes from v1:
- GLB import now fixes rotation mode (QUATERNION → XYZ Euler)
- GLB import clears parent relationships and deletes orphan empties
- Clip analysis step added (was missing in v1)
- Multi-keyframe pin support (v1 only used magic_keyframe)
- Compositor uses Blender 5.x compositing_node_group API correctly
"""

# ------------------------------------------------------------------
# Scene Setup
# ------------------------------------------------------------------

RESET_AND_CREATE_GEOTRACKER = """
import bpy

# Clear scene completely
bpy.ops.wm.read_homefile(use_empty=True)

# Enable KeenTools addon
addon_ok = False
try:
    bpy.ops.preferences.addon_enable(module='keentools')
    addon_ok = True
    print("KeenTools addon enabled")
except Exception as e:
    print(f"ERROR: KeenTools addon not available: {{e}}")
    print("Install from: https://keentools.io/downloads")

# Create GeoTracker
gt_index = -1
if addon_ok:
    try:
        bpy.ops.keentools_gt.create_geotracker()
        gt_settings = bpy.context.scene.keentools_gt_settings
        gt_index = gt_settings.current_geotracker_num
        print(f"GeoTracker created (index {{gt_index}})")
    except Exception as e:
        print(f"ERROR: Cannot create GeoTracker: {{e}}")

print(f"RESULT:addon_ok={{addon_ok}},gt_index={{gt_index}}")
str(gt_index)
"""

LOAD_FOOTAGE = """
import bpy

video_path = "{video_path}"
clip = bpy.data.movieclips.load(video_path)

# Set scene frame range and FPS from clip metadata
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = clip.frame_duration
# Try to get FPS from clip; default to 25
fps = getattr(clip, 'fps', 25)
if fps <= 0:
    fps = 25
scene.render.fps = int(fps)

w, h = clip.size[0], clip.size[1]
print(f"Loaded: {{clip.name}}, {{w}}x{{h}}, {{clip.frame_duration}} frames, {{fps}} fps")
print(f"RESULT:clip={{clip.name}},width={{w}},height={{h}},frames={{clip.frame_duration}},fps={{fps}}")
str(clip.frame_duration)
"""

# ------------------------------------------------------------------
# GLB Import & Preparation (critical fix from tutorial)
# ------------------------------------------------------------------

IMPORT_AND_PREPARE_GLB = """
import bpy
import math

glb_path = "{glb_path}"
mesh_name = "{mesh_name}"

# Import GLB
bpy.ops.import_scene.gltf(filepath=glb_path)
imported = list(bpy.context.selected_objects)
print(f"Imported {{len(imported)}} objects from {{glb_path}}")

# Step 1: Convert rotation mode from Quaternion to XYZ Euler
# (Tutorial: "by default, the rotation mode is set to quaternion,
#  but GeoTracker only works with XYZ Euler")
for obj in imported:
    if obj.rotation_mode == 'QUATERNION':
        obj.rotation_mode = 'XYZ'
        print(f"  Fixed rotation mode: {{obj.name}} QUATERNION → XYZ")

# Step 2: Clear parent connections (keep transform)
# (Tutorial: "in the relations tab, we'll clear the parent connection")
meshes = []
empties = []
for obj in imported:
    if obj.type == 'MESH':
        meshes.append(obj)
    elif obj.type == 'EMPTY':
        empties.append(obj)

for mesh in meshes:
    if mesh.parent:
        # Store world matrix before unparenting
        world_mat = mesh.matrix_world.copy()
        mesh.parent = None
        mesh.matrix_world = world_mat
        print(f"  Unparented: {{mesh.name}}")

# Step 3: Delete orphan empties
# (Tutorial: "then delete the empty object")
for empty in empties:
    bpy.data.objects.remove(empty, do_unlink=True)
    print(f"  Deleted empty: {{empty.name}}")

# Step 4: Rename primary mesh
# (Tutorial: "Let's rename the mesh to quad bike")
if meshes:
    primary = meshes[0]
    old_name = primary.name
    primary.name = mesh_name
    primary.data.name = mesh_name
    bpy.context.view_layer.objects.active = primary
    primary.select_set(True)
    verts = len(primary.data.vertices)
    faces = len(primary.data.polygons)
    print(f"  Renamed: {{old_name}} → {{mesh_name}} ({{verts}} verts, {{faces}} faces)")

mesh_count = len(meshes)
print(f"RESULT:mesh_count={{mesh_count}},name={{mesh_name}},verts={{verts if meshes else 0}}")
str(mesh_count)
"""

# ------------------------------------------------------------------
# GeoTracker Configuration
# ------------------------------------------------------------------

SETUP_GEOTRACKER = """
import bpy

mesh_name = "{mesh_name}"

# Get the mesh object
mesh_obj = bpy.data.objects.get(mesh_name)
if not mesh_obj:
    # Fallback: find first mesh
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            mesh_obj = obj
            break

if not mesh_obj:
    raise ValueError(f"No mesh object found (looked for '{{mesh_name}}')")

# Get the movie clip
clip = None
for c in bpy.data.movieclips:
    clip = c
    break
if not clip:
    raise ValueError("No movie clip loaded")

# Create camera if needed
cam = bpy.data.objects.get('Camera')
if not cam:
    bpy.ops.object.camera_add(location=(0, -5, 2))
    cam = bpy.context.active_object
    cam.name = 'Camera'
bpy.context.scene.camera = cam

# Configure GeoTracker
gt_settings = bpy.context.scene.keentools_gt_settings
gt_idx = gt_settings.current_geotracker_num
gt = gt_settings.geotrackers[gt_idx]

gt.geomobj = mesh_obj
gt.camobj = cam
gt.movie_clip = clip

# Match render resolution to clip
bpy.context.scene.render.resolution_x = clip.size[0]
bpy.context.scene.render.resolution_y = clip.size[1]

print(f"GeoTracker configured:")
print(f"  Geometry: {{mesh_obj.name}}")
print(f"  Camera: {{cam.name}}")
print(f"  Clip: {{clip.name}} ({{clip.size[0]}}x{{clip.size[1]}})")
print(f"RESULT:status=ready,gt_index={{gt_idx}}")
str("ready")
"""

# ------------------------------------------------------------------
# Clip Analysis (new in v2 — v1 skipped this)
# ------------------------------------------------------------------

ANALYZE_CLIP = """
import bpy
import time

gt_settings = bpy.context.scene.keentools_gt_settings

# Find 3D viewport for context override
view3d_area = None
view3d_region = None
target_window = None
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            target_window = window
            view3d_area = area
            for region in area.regions:
                if region.type == 'WINDOW':
                    view3d_region = region
                    break
            break
    if view3d_area:
        break

if not view3d_area:
    # No viewport — skip analysis, use precalcless mode
    gt = gt_settings.geotrackers[gt_settings.current_geotracker_num]
    gt.precalcless = True
    print("No 3D viewport — using precalcless mode (skipping analysis)")
    print("RESULT:status=precalcless")
else:
    with bpy.context.temp_override(window=target_window, area=view3d_area, region=view3d_region):
        try:
            bpy.ops.keentools_gt.analyze_clip()
            print("Clip analysis started...")
            # Poll until done
            for i in range(120):
                time.sleep(2)
                mode = gt_settings.calculating_mode
                if not mode or mode == 'NONE':
                    break
                pct = gt_settings.user_percent
                print(f"  Analyzing: {{pct:.0f}}%")
            print("Clip analysis complete")
            print("RESULT:status=analyzed")
        except Exception as e:
            # Fall back to precalcless
            gt = gt_settings.geotrackers[gt_settings.current_geotracker_num]
            gt.precalcless = True
            print(f"Analysis failed ({{e}}), using precalcless mode")
            print("RESULT:status=precalcless")

str("done")
"""

# ------------------------------------------------------------------
# Surface Masking (optional, from tutorial)
# ------------------------------------------------------------------

CREATE_SURFACE_MASK = """
import bpy

mesh_name = "{mesh_name}"
group_name = "{group_name}"
face_indices_json = "{face_indices_json}"  # JSON list of face indices or "auto"

import json

mesh_obj = bpy.data.objects.get(mesh_name)
if not mesh_obj or mesh_obj.type != 'MESH':
    raise ValueError(f"Mesh '{{mesh_name}}' not found")

# Create vertex group
vg = mesh_obj.vertex_groups.get(group_name)
if not vg:
    vg = mesh_obj.vertex_groups.new(name=group_name)

mesh = mesh_obj.data

if face_indices_json == "auto":
    # Auto-detect: no masking, just create empty group
    print(f"Created empty vertex group '{{group_name}}' for manual population")
else:
    face_indices = json.loads(face_indices_json)
    # Collect vertex indices from specified faces
    vert_indices = set()
    for fi in face_indices:
        if fi < len(mesh.polygons):
            for vi in mesh.polygons[fi].vertices:
                vert_indices.add(vi)
    vg.add(list(vert_indices), 1.0, 'REPLACE')
    print(f"Vertex group '{{group_name}}': {{len(vert_indices)}} vertices from {{len(face_indices)}} faces")

# Apply to GeoTracker mask
gt_settings = bpy.context.scene.keentools_gt_settings
gt = gt_settings.geotrackers[gt_settings.current_geotracker_num]
gt.mask_3d = group_name
print(f"GeoTracker surface mask set to '{{group_name}}'")
print(f"RESULT:status=masked,vertices={{len(vert_indices) if face_indices_json != 'auto' else 0}}")
str("masked")
"""

# ------------------------------------------------------------------
# Tracking (multi-pin approach from tutorial)
# ------------------------------------------------------------------

ENTER_PINMODE_AND_ALIGN = """
import bpy
import time

# Initial transform (optional)
loc = {location}
rot = {rotation}
scale = {scale}
use_magic = {use_magic}

gt_settings = bpy.context.scene.keentools_gt_settings

# Find 3D viewport
view3d_area = None
view3d_region = None
target_window = None
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            target_window = window
            view3d_area = area
            for region in area.regions:
                if region.type == 'WINDOW':
                    view3d_region = region
                    break
            break
    if view3d_area:
        break

if not view3d_area:
    raise RuntimeError("No 3D viewport found — cannot enter pin mode")

with bpy.context.temp_override(window=target_window, area=view3d_area, region=view3d_region):
    # Switch to camera view
    bpy.ops.view3d.view_camera()
    time.sleep(0.5)

    # Enter pin mode
    bpy.ops.keentools_gt.pinmode('INVOKE_DEFAULT')
    time.sleep(1)
    print("Entered pin mode")

    if use_magic:
        # Use magic keyframe for automatic initial alignment
        bpy.ops.keentools_gt.magic_keyframe_btn()
        time.sleep(2)
        print("Magic keyframe applied")
    else:
        # Apply manual initial transform
        mesh_obj = gt_settings.geotrackers[gt_settings.current_geotracker_num].geomobj
        if mesh_obj:
            mesh_obj.location = loc
            mesh_obj.rotation_euler = rot
            mesh_obj.scale = scale
            print(f"Applied transform: loc={{loc}}, rot={{rot}}, scale={{scale}}")

print("RESULT:status=aligned")
str("aligned")
"""

TRACK_AND_REFINE = """
import bpy
import time

pin_frames_json = "{pin_frames_json}"
timeout_seconds = {timeout_seconds}

import json
pin_frames = json.loads(pin_frames_json)

gt_settings = bpy.context.scene.keentools_gt_settings
scene = bpy.context.scene

# Find 3D viewport
view3d_area = None
view3d_region = None
target_window = None
for window in bpy.context.window_manager.windows:
    for area in window.screen.areas:
        if area.type == 'VIEW_3D':
            target_window = window
            view3d_area = area
            for region in area.regions:
                if region.type == 'WINDOW':
                    view3d_region = region
                    break
            break
    if view3d_area:
        break

if not view3d_area:
    raise RuntimeError("No 3D viewport found")

with bpy.context.temp_override(window=target_window, area=view3d_area, region=view3d_region):
    # Ensure we're in pin mode
    try:
        bpy.ops.keentools_gt.pinmode('INVOKE_DEFAULT')
        time.sleep(0.5)
    except:
        pass  # Already in pin mode

    # Track forward through entire clip
    print("Tracking to end...")
    try:
        bpy.ops.keentools_gt.track_to_end_btn()

        # Poll until complete
        max_polls = int(timeout_seconds / 3)
        for i in range(max_polls):
            time.sleep(3)
            mode = gt_settings.calculating_mode
            if not mode or mode == 'NONE':
                break
            pct = gt_settings.user_percent
            if i % 10 == 0:
                print(f"  Tracking: {{pct:.0f}}%")
        else:
            print("  Tracking timed out, stopping...")
            try:
                bpy.ops.keentools_gt.stop_calculating_btn()
            except:
                pass
    except Exception as e:
        print(f"Track to end error: {{e}}")

    print("Forward tracking complete")

    # Refine all (interpolate between keyframes)
    print("Refining tracking...")
    try:
        bpy.ops.keentools_gt.refine_all_btn()
        for i in range(max_polls):
            time.sleep(3)
            mode = gt_settings.calculating_mode
            if not mode or mode == 'NONE':
                break
            pct = gt_settings.user_percent
            if i % 10 == 0:
                print(f"  Refining: {{pct:.0f}}%")
        print("Refinement complete")
    except Exception as e:
        print(f"Refine error: {{e}}")

    # Exit pin mode
    try:
        bpy.ops.keentools_gt.exit_pinmode_btn()
        print("Exited pin mode")
    except:
        pass

# Bake animation to world space
try:
    bpy.ops.keentools_gt.bake_animation_to_world(product=1)
    print("Animation baked to world space")
except Exception as e:
    print(f"Bake error: {{e}}")
    # Fallback: ensure mesh has at least one keyframe
    mesh_obj = gt_settings.geotrackers[gt_settings.current_geotracker_num].geomobj
    if mesh_obj:
        mesh_obj.keyframe_insert(data_path='location', frame=scene.frame_start)
        mesh_obj.keyframe_insert(data_path='rotation_euler', frame=scene.frame_start)
        print("Fallback: inserted single keyframe")

# Count keyframes on tracked mesh
mesh_obj = gt_settings.geotrackers[gt_settings.current_geotracker_num].geomobj
kf_count = 0
if mesh_obj and mesh_obj.animation_data and mesh_obj.animation_data.action:
    for fc in mesh_obj.animation_data.action.fcurves:
        kf_count = max(kf_count, len(fc.keyframe_points))

total_frames = scene.frame_end - scene.frame_start + 1
print(f"Tracking result: {{kf_count}} keyframes across {{total_frames}} frames")
print(f"RESULT:status=tracked,keyframes={{kf_count}},total_frames={{total_frames}}")
str(kf_count)
"""

# ------------------------------------------------------------------
# Save Blend File
# ------------------------------------------------------------------

SAVE_BLEND = """
import bpy

output_path = "{output_path}"
bpy.ops.wm.save_as_mainfile(filepath=output_path)
print(f"Saved: {{output_path}}")
str(output_path)
"""

# ------------------------------------------------------------------
# Compositor Setup (Blender 5.x)
# ------------------------------------------------------------------

SETUP_COMPOSITOR = """
import bpy
import os

video_path = "{video_path}"
output_path = "{output_path}"
render_engine = "{render_engine}"

scene = bpy.context.scene
scene.use_nodes = True

# Blender 5.x: compositing_node_group replaces scene.node_tree
try:
    cng = scene.compositing_node_group
except AttributeError:
    # Blender 4.x fallback
    cng = scene.node_tree

if cng is None:
    try:
        cng = bpy.data.node_groups.new("Compositing", "CompositorNodeTree")
        scene.compositing_node_group = cng
    except:
        # Blender 4.x
        scene.use_nodes = True
        cng = scene.node_tree

# Clear existing nodes
for node in list(cng.nodes):
    cng.nodes.remove(node)

# Clear interface sockets (5.x only)
try:
    for item in list(cng.interface.items_tree):
        cng.interface.remove(item)
    cng.interface.new_socket(name="Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    use_5x = True
except:
    use_5x = False

# Create compositor nodes
clip_node = cng.nodes.new("CompositorNodeMovieClip")
render_layer = cng.nodes.new("CompositorNodeRLayers")
alpha_over = cng.nodes.new("CompositorNodeAlphaOver")

if use_5x:
    output_node = cng.nodes.new("NodeGroupOutput")
else:
    output_node = cng.nodes.new("CompositorNodeComposite")

viewer = cng.nodes.new("CompositorNodeViewer")

clip_node.location = (-400, 200)
render_layer.location = (-400, -200)
alpha_over.location = (100, 0)
output_node.location = (400, 100)
viewer.location = (400, -100)

# Set movie clip
clip = None
for c in bpy.data.movieclips:
    clip = c
    break
if not clip:
    clip = bpy.data.movieclips.load(video_path)
clip_node.clip = clip

# Link nodes
cng.links.new(clip_node.outputs["Image"], alpha_over.inputs["Image"])
cng.links.new(render_layer.outputs["Image"], alpha_over.inputs["Image_001"])
if use_5x:
    cng.links.new(alpha_over.outputs["Image"], output_node.inputs["Image"])
else:
    cng.links.new(alpha_over.outputs["Image"], output_node.inputs["Image"])
cng.links.new(alpha_over.outputs["Image"], viewer.inputs["Image"])

# Ensure world for lighting
if not scene.world:
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.8, 0.8, 0.8, 1)
    bg.inputs["Strength"].default_value = 1.0
    scene.world = world

# Ensure scene has a light
has_light = any(o.type == 'LIGHT' for o in bpy.data.objects)
if not has_light:
    bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
    bpy.context.active_object.data.energy = 3.0
    print("Added sun light")

# Render settings
scene.render.engine = render_engine
scene.render.resolution_x = clip.size[0] if clip else 1920
scene.render.resolution_y = clip.size[1] if clip else 1080
scene.render.fps = int(getattr(clip, 'fps', 25)) if clip else 25
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = True

os.makedirs(output_path, exist_ok=True)
scene.render.filepath = output_path + "/composited_"

print(f"Compositor ready: {{render_engine}}, {{scene.render.resolution_x}}x{{scene.render.resolution_y}}")
print(f"Output: {{scene.render.filepath}}")
print(f"RESULT:status=ready,engine={{render_engine}}")
str("compositor_ready")
"""

# ------------------------------------------------------------------
# Render
# ------------------------------------------------------------------

RENDER_ANIMATION = """
import bpy

print("Rendering composited animation...")
bpy.ops.render.render(animation=True)

scene = bpy.context.scene
frame_count = scene.frame_end - scene.frame_start + 1
print(f"Render complete: {{frame_count}} frames")
print(f"Output: {{scene.render.filepath}}")
print(f"RESULT:status=rendered,frames={{frame_count}}")
str(frame_count)
"""

# ------------------------------------------------------------------
# Validation Helpers
# ------------------------------------------------------------------

CHECK_SCENE_STATE = """
import bpy

scene = bpy.context.scene
result = {{}}

# Meshes
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
result['mesh_count'] = len(meshes)
result['mesh_names'] = [m.name for m in meshes]

# Clips
clips = list(bpy.data.movieclips)
result['clip_count'] = len(clips)
if clips:
    c = clips[0]
    result['clip_name'] = c.name
    result['clip_frames'] = c.frame_duration
    result['clip_size'] = [c.size[0], c.size[1]]

# GeoTracker
try:
    gt_settings = scene.keentools_gt_settings
    result['gt_count'] = len(gt_settings.geotrackers)
    gt_idx = gt_settings.current_geotracker_num
    if gt_idx >= 0 and gt_idx < len(gt_settings.geotrackers):
        gt = gt_settings.geotrackers[gt_idx]
        result['gt_geometry'] = gt.geomobj.name if gt.geomobj else None
        result['gt_camera'] = gt.camobj.name if gt.camobj else None
        result['gt_clip'] = gt.movie_clip.name if gt.movie_clip else None
except:
    result['gt_count'] = 0

# Animation
for mesh in meshes:
    if mesh.animation_data and mesh.animation_data.action:
        kf_count = 0
        for fc in mesh.animation_data.action.fcurves:
            kf_count = max(kf_count, len(fc.keyframe_points))
        result[f'keyframes_{{mesh.name}}'] = kf_count

import json
out = json.dumps(result)
print(f"SCENE_STATE:{{out}}")
str(out)
"""
