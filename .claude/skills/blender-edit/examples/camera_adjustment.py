"""Example: Camera adjustment edit script (Level 1 task).

This script demonstrates how to adjust camera position and rotation
to match a goal viewpoint in BlenderBench Level 1 tasks.

Usage:
    BLENDER_PATH=/path/to/blender python execute_blender_edit.py \
        examples/camera_adjustment.py \
        /path/to/scene.blend \
        /path/to/output
"""

import bpy
import math

# Load existing scene (BLEND_FILE_PATH is injected by executor)
bpy.ops.wm.open_mainfile(filepath=BLEND_FILE_PATH)

# === EDIT: Adjust Camera1 position and rotation ===

# Get the camera object
camera = bpy.data.objects["Camera1"]

# Set new location (from goal_code)
camera.location = (5.9589, -5.6058, 4.0383)

# Set new rotation (in radians!)
camera.rotation_euler = (1.2839, 0.0000, 0.8149)

# Optional: Adjust focal length if needed
# camera.data.lens = 50  # mm

# === END EDIT ===

# Save modified scene (OUTPUT_BLEND_PATH is injected by executor)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
