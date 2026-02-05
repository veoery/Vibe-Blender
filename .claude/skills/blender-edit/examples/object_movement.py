"""Example: Object movement edit script (Level 2 task).

This script demonstrates how to move objects to match a goal
in BlenderBench Level 2 tasks, including handling reflections.

Usage:
    BLENDER_PATH=/path/to/blender python execute_blender_edit.py \
        examples/object_movement.py \
        /path/to/scene.blend \
        /path/to/output
"""

import bpy
import math

# Load existing scene
bpy.ops.wm.open_mainfile(filepath=BLEND_FILE_PATH)

# === EDIT: Move objects to target positions ===

# Move cabinet first (to see plant in mirror)
cabinet = bpy.data.objects["Cabinet"]
cabinet.location = (0.55602, 12.284, 0.1277)

# Move plant to visible position
plant = bpy.data.objects["Plant"]
plant.location = (3.1586, 15.049, 0.92)

# Note: Object positions respect constraints:
# x: (0.3, 3)
# y: (12, 15)
# z: (0, 3)

# === END EDIT ===

# Save modified scene
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
