"""Example: Compositional edit script (Level 3 task).

This script demonstrates how to combine camera, object,
lighting, and shape key adjustments in BlenderBench Level 3 tasks.

Usage:
    BLENDER_PATH=/path/to/blender python execute_blender_edit.py \
        examples/compositional_edit.py \
        /path/to/scene.blend \
        /path/to/output
"""

import bpy
import math

# Load existing scene
bpy.ops.wm.open_mainfile(filepath=BLEND_FILE_PATH)

# === EDIT: Multiple adjustments ===

# 1. Adjust camera to see the objects
camera = bpy.data.objects["Camera1"]
camera.location = (2.5, -8.0, 3.5)
camera.rotation_euler = (math.radians(70), 0, math.radians(15))

# 2. Move cabinet (needed for mirror reflection)
cabinet = bpy.data.objects["Cabinet"]
cabinet.location = (0.55602, 12.284, 0.1277)

# 3. Move plant to visible position
plant = bpy.data.objects["Plant"]
plant.location = (3.1586, 15.049, 0.92)

# 4. Adjust character shape keys (if present)
try:
    key = bpy.data.shape_keys["Key"]
    key.key_blocks["BellySag"].value = 5
    key.key_blocks["BellyShrink"].value = 3
except KeyError:
    print("[INFO] Shape keys not found, skipping")

# 5. Adjust lighting if needed
try:
    main_light = bpy.data.objects["MainLight"]
    main_light.data.energy = 150
except KeyError:
    print("[INFO] MainLight not found, skipping")

# === END EDIT ===

# Save modified scene
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
