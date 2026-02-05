"""Blender rendering template for BlenderBench evaluation.

Uses existing Camera1/Camera2 from the scene instead of creating new cameras.
Outputs render1.png (and optionally render2.png) for evaluation compatibility.

Variables BLEND_FILE_PATH, OUTPUT_BLEND_PATH, OUTPUT_DIR, and NUM_RENDERS must be defined before this code.
"""

EVAL_RENDER_TEMPLATE = '''
# ============================================
# EVALUATION RENDERING (BlenderBench Compatible)
# ============================================

import bpy
import os

def setup_render_settings(resolution=(512, 512), samples=512):
    """Configure render settings for evaluation."""
    scene = bpy.context.scene

    # Use Cycles for quality
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.cycles.use_denoising = True

    # Try GPU, fallback to CPU
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = 'CUDA'  # or 'OPTIX', 'METAL'
        prefs.get_devices()
        for device in prefs.devices:
            if device.type == 'GPU':
                device.use = True
        scene.cycles.device = 'GPU'
    except Exception:
        scene.cycles.device = 'CPU'

    # Resolution
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.resolution_percentage = 100

    # Output format
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGB'


def render_from_camera(camera_name, output_path):
    """Render from a specific camera."""
    scene = bpy.context.scene

    if camera_name not in bpy.data.objects:
        print(f"[WARNING] Camera '{camera_name}' not found, skipping")
        return False

    camera = bpy.data.objects[camera_name]
    if camera.type != 'CAMERA':
        print(f"[WARNING] Object '{camera_name}' is not a camera, skipping")
        return False

    scene.camera = camera
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"[RENDER] {camera_name} -> {output_path}")
    return True


def run_eval_render_pipeline(output_dir, num_renders=1, resolution=(512, 512), samples=512):
    """Run evaluation rendering pipeline using existing scene cameras.

    Args:
        output_dir: Directory to save renders
        num_renders: Number of renders to generate (matches goal image count)
        resolution: Render resolution tuple
        samples: Number of Cycles samples
    """
    os.makedirs(output_dir, exist_ok=True)

    # Setup render settings
    setup_render_settings(resolution, samples)

    renders = []
    camera_names = ["Camera1", "Camera2"]  # BlenderBench uses Camera1/Camera2

    # Only render up to num_renders cameras
    for i in range(min(num_renders, len(camera_names))):
        camera_name = camera_names[i]
        render_path = os.path.join(output_dir, f"render{i+1}.png")
        if render_from_camera(camera_name, render_path):
            renders.append(render_path)

    # Fallback: if no Camera1/Camera2, try scene's active camera for render1
    if not renders and bpy.context.scene.camera and num_renders >= 1:
        fallback_path = os.path.join(output_dir, "render1.png")
        bpy.context.scene.render.filepath = fallback_path
        bpy.ops.render.render(write_still=True)
        renders.append(fallback_path)
        print(f"[RENDER] Fallback camera -> {fallback_path}")

    print(f"[RENDER COMPLETE] Generated {len(renders)} render(s)")
    return renders


# Run the pipeline if OUTPUT_DIR is defined
if 'OUTPUT_DIR' in dir():
    run_eval_render_pipeline(
        OUTPUT_DIR,
        num_renders=NUM_RENDERS if 'NUM_RENDERS' in dir() else 1,
        resolution=RENDER_RESOLUTION if 'RENDER_RESOLUTION' in dir() else (512, 512),
        samples=RENDER_SAMPLES if 'RENDER_SAMPLES' in dir() else 512
    )
'''
