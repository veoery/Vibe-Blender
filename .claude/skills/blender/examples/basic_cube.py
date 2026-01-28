"""Basic cube example - demonstrates minimal Blender script structure."""

import bpy

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create cube
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
cube = bpy.context.active_object
cube.name = "BasicCube"

# Add material
mat = bpy.data.materials.new(name="CubeMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.2, 0.5, 0.8, 1.0)  # Blue
bsdf.inputs["Roughness"].default_value = 0.3

cube.data.materials.append(mat)

# Save (OUTPUT_BLEND_PATH is injected by execute_blender.py)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
