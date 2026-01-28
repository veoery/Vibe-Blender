"""Modifiers example - demonstrates common modifiers."""

import bpy

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Example 1: Subdivision Surface
bpy.ops.mesh.primitive_cube_add(location=(-4, 0, 0), size=1.5)
cube_subsurf = bpy.context.active_object
cube_subsurf.name = "Cube_Subdiv"

mod = cube_subsurf.modifiers.new(name="Subsurf", type='SUBSURF')
mod.levels = 2
mod.render_levels = 3

# Material
mat = bpy.data.materials.new(name="Blue")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.5, 0.8, 1.0)
cube_subsurf.data.materials.append(mat)

# Example 2: Bevel Modifier
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0), size=1.5)
cube_bevel = bpy.context.active_object
cube_bevel.name = "Cube_Bevel"

mod = cube_bevel.modifiers.new(name="Bevel", type='BEVEL')
mod.width = 0.1
mod.segments = 4

# Material
mat = bpy.data.materials.new(name="Red")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.8, 0.2, 0.2, 1.0)
mat.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 0.8
cube_bevel.data.materials.append(mat)

# Example 3: Array Modifier
bpy.ops.mesh.primitive_cylinder_add(location=(4, 0, 0), radius=0.3, depth=1.5)
cylinder_array = bpy.context.active_object
cylinder_array.name = "Cylinder_Array"

mod = cylinder_array.modifiers.new(name="Array", type='ARRAY')
mod.count = 3
mod.relative_offset_displace = (0, 0, 1.2)

# Material
mat = bpy.data.materials.new(name="Green")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.2, 0.8, 0.3, 1.0)
cylinder_array.data.materials.append(mat)

# Example 4: Boolean Modifier
bpy.ops.mesh.primitive_cube_add(location=(-4, 3, 0), size=1.5)
base_cube = bpy.context.active_object
base_cube.name = "Base_Boolean"

# Create cutter sphere
bpy.ops.mesh.primitive_uv_sphere_add(location=(-4, 3, 0), radius=0.9)
cutter_sphere = bpy.context.active_object
cutter_sphere.name = "Cutter"
cutter_sphere.hide_render = True

# Apply boolean
mod = base_cube.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = cutter_sphere

# Material
mat = bpy.data.materials.new(name="Orange")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (1.0, 0.5, 0.1, 1.0)
base_cube.data.materials.append(mat)

# Save
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
