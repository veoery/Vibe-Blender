"""Example: Lighting and object adjustment edit script (Level 2 task).

This script demonstrates how to adjust lighting properties
and object positions in BlenderBench Level 2 tasks.

Usage:
    BLENDER_PATH=/path/to/blender python execute_blender_edit.py \
        examples/lighting_adjustment.py \
        /path/to/scene.blend \
        /path/to/output
"""

import bpy
import math

# Load existing scene
bpy.ops.wm.open_mainfile(filepath=BLEND_FILE_PATH)

# === EDIT: Adjust lighting and object positions ===

# Adjust lamp on cupboard
lamp_cupboard = bpy.data.objects["lamp_on_the_cupboard"]
lamp_cupboard.data.energy = 1.5
lamp_cupboard.data.color = (1, 1, 1)  # RGB, values 0-1

# Adjust lamp on shelf
lamp_shelf = bpy.data.objects["lamp_on_shelf"]
lamp_shelf.data.energy = 1.2

# Adjust ceiling light
ceiling_light = bpy.data.objects["light_on_ceilling"]
ceiling_light.data.energy = 200

# Move basketball to target position
basketball = bpy.data.objects["basketball"]
basketball.location = (13.4023, 2.7485, 0.6584)

# === END EDIT ===

# Save modified scene
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
