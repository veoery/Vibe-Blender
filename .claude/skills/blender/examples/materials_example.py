"""Materials example - demonstrates common material types."""

import bpy

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Helper function to create material
def create_material(name, base_color, metallic=0.0, roughness=0.5, emission=None):
    """Create a Principled BSDF material."""
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")

    bsdf.inputs["Base Color"].default_value = (*base_color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness

    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1.0)
        bsdf.inputs["Emission Strength"].default_value = 2.0

    return mat

# Create spheres with different materials
materials = [
    ("Red_Plastic", (0.8, 0.1, 0.1), 0.0, 0.4, None),
    ("Gold_Metal", (1.0, 0.8, 0.3), 0.9, 0.2, None),
    ("Blue_Glass", (0.1, 0.3, 0.8), 0.0, 0.1, None),
    ("Green_Emission", (0.2, 0.8, 0.2), 0.0, 0.5, (0.2, 1.0, 0.2)),
]

x_offset = -4.5
for name, color, metallic, roughness, emission in materials:
    # Create sphere
    bpy.ops.mesh.primitive_uv_sphere_add(location=(x_offset, 0, 0), radius=1)
    sphere = bpy.context.active_object
    sphere.name = name

    # Apply material
    mat = create_material(name + "_Mat", color, metallic, roughness, emission)
    sphere.data.materials.append(mat)

    # Add subdivision for smooth appearance
    mod = sphere.modifiers.new(name="Subsurf", type='SUBSURF')
    mod.levels = 2
    mod.render_levels = 2

    x_offset += 3

# Save
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
