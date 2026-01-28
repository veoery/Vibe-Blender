"""Blender rendering template for multi-view output.

This code is injected into generated scripts to handle rendering.
Variables OUTPUT_DIR and RENDER_RESOLUTION must be defined before this code.
"""

RENDER_TEMPLATE = '''
# ============================================
# RENDERING SETUP (Auto-injected by Blender Skill)
# ============================================

import bpy
import math
import os
import mathutils

def setup_camera(name, location, rotation, ortho=True, ortho_scale=5):
    """Create and configure a camera."""
    cam_data = bpy.data.cameras.new(name=name)
    cam_data.type = 'ORTHO' if ortho else 'PERSP'
    if ortho:
        cam_data.ortho_scale = ortho_scale

    cam_obj = bpy.data.objects.new(name, cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = location
    cam_obj.rotation_euler = rotation
    return cam_obj

def setup_lighting():
    """Set up basic three-point lighting."""
    # Key light
    key_data = bpy.data.lights.new(name="KeyLight", type='SUN')
    key_data.energy = 3.0
    key_obj = bpy.data.objects.new("KeyLight", key_data)
    bpy.context.scene.collection.objects.link(key_obj)
    key_obj.rotation_euler = (math.radians(45), math.radians(30), 0)

    # Fill light
    fill_data = bpy.data.lights.new(name="FillLight", type='SUN')
    fill_data.energy = 1.5
    fill_obj = bpy.data.objects.new("FillLight", fill_data)
    bpy.context.scene.collection.objects.link(fill_obj)
    fill_obj.rotation_euler = (math.radians(45), math.radians(-60), 0)

    # Rim light
    rim_data = bpy.data.lights.new(name="RimLight", type='SUN')
    rim_data.energy = 2.0
    rim_obj = bpy.data.objects.new("RimLight", rim_data)
    bpy.context.scene.collection.objects.link(rim_obj)
    rim_obj.rotation_euler = (math.radians(-30), math.radians(180), 0)

def render_view(camera, filepath, resolution):
    """Render a single view."""
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.filepath = filepath
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)

def render_turntable(camera, output_dir, frames=12, resolution=(512, 512)):
    """Render a turntable animation."""
    scene = bpy.context.scene
    scene.camera = camera
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.image_settings.file_format = 'PNG'

    # Create empty at origin to rotate around
    bpy.ops.object.empty_add(location=(0, 0, 0))
    pivot = bpy.context.active_object
    pivot.name = "TurntablePivot"

    # Parent camera to pivot
    camera.parent = pivot

    frame_paths = []
    for i in range(frames):
        angle = (2 * math.pi * i) / frames
        pivot.rotation_euler = (0, 0, angle)
        bpy.context.view_layer.update()

        filepath = os.path.join(output_dir, f"turntable_{i:03d}.png")
        scene.render.filepath = filepath
        bpy.ops.render.render(write_still=True)
        frame_paths.append(filepath)

    return frame_paths

def run_render_pipeline(output_dir, resolution=(512, 512)):
    """Run the complete rendering pipeline."""
    os.makedirs(output_dir, exist_ok=True)

    # Set up render engine
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 64
    bpy.context.scene.cycles.use_denoising = True

    # Fallback to EEVEE if Cycles unavailable
    try:
        bpy.context.scene.cycles.device = 'GPU'
    except:
        bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'

    # Set up lighting
    setup_lighting()

    # Calculate scene bounds for camera positioning
    min_coord = [float('inf')] * 3
    max_coord = [float('-inf')] * 3

    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ mathutils.Vector(corner)
                for i in range(3):
                    min_coord[i] = min(min_coord[i], world_corner[i])
                    max_coord[i] = max(max_coord[i], world_corner[i])

    if min_coord[0] == float('inf'):
        # No mesh objects, use defaults
        min_coord = [-1, -1, -1]
        max_coord = [1, 1, 1]

    center = [(min_coord[i] + max_coord[i]) / 2 for i in range(3)]
    size = max(max_coord[i] - min_coord[i] for i in range(3))
    dist = size * 2
    ortho_scale = size * 1.5

    # Create cameras for 4 views
    cameras = {
        'front': setup_camera('CamFront', (center[0], -dist, center[2]), (math.radians(90), 0, 0), True, ortho_scale),
        'top': setup_camera('CamTop', (center[0], center[1], dist), (0, 0, 0), True, ortho_scale),
        'side': setup_camera('CamSide', (dist, center[1], center[2]), (math.radians(90), 0, math.radians(90)), True, ortho_scale),
        'iso': setup_camera('CamIso', (dist*0.7, -dist*0.7, dist*0.7), (math.radians(54.7), 0, math.radians(45)), False),
    }

    # Render each view
    view_paths = []
    for name, cam in cameras.items():
        filepath = os.path.join(output_dir, f"view_{name}.png")
        render_view(cam, filepath, resolution)
        view_paths.append(filepath)

    # Render turntable (12 frames = 30° per frame)
    turntable_dir = os.path.join(output_dir, "turntable_frames")
    os.makedirs(turntable_dir, exist_ok=True)
    frame_paths = render_turntable(cameras['iso'], turntable_dir, frames=12, resolution=resolution)

    print(f"[RENDER COMPLETE] Views: {len(view_paths)}, Frames: {len(frame_paths)}")

# Run the pipeline if OUTPUT_DIR is defined
if 'OUTPUT_DIR' in dir():
    run_render_pipeline(OUTPUT_DIR, RENDER_RESOLUTION if 'RENDER_RESOLUTION' in dir() else (512, 512))
'''
