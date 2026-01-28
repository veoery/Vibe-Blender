# Blender Python API Quick Reference

Compact reference for the most common Blender Python API operations.

## Scene Management

### Clear Scene
```python
import bpy

# Delete all objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
```

### Save File
```python
# Save current file
bpy.ops.wm.save_as_mainfile(filepath="/path/to/file.blend")
```

## Primitives

### Cube
```python
bpy.ops.mesh.primitive_cube_add(
    size=2.0,
    location=(0, 0, 0),
    rotation=(0, 0, 0),
    scale=(1, 1, 1)
)
cube = bpy.context.active_object
```

### Sphere
```python
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=1.0,
    location=(0, 0, 0),
    segments=32,  # longitude
    ring_count=16  # latitude
)
sphere = bpy.context.active_object
```

### Cylinder
```python
bpy.ops.mesh.primitive_cylinder_add(
    radius=1.0,
    depth=2.0,
    location=(0, 0, 0),
    vertices=32  # number of sides
)
cylinder = bpy.context.active_object
```

### Cone
```python
bpy.ops.mesh.primitive_cone_add(
    radius1=1.0,
    radius2=0.0,
    depth=2.0,
    location=(0, 0, 0),
    vertices=32
)
cone = bpy.context.active_object
```

### Torus
```python
bpy.ops.mesh.primitive_torus_add(
    major_radius=1.0,
    minor_radius=0.25,
    location=(0, 0, 0),
    major_segments=48,
    minor_segments=12
)
torus = bpy.context.active_object
```

### Plane
```python
bpy.ops.mesh.primitive_plane_add(
    size=2.0,
    location=(0, 0, 0)
)
plane = bpy.context.active_object
```

### Monkey (Suzanne)
```python
bpy.ops.mesh.primitive_monkey_add(
    size=2.0,
    location=(0, 0, 0)
)
monkey = bpy.context.active_object
```

## Object Properties

### Transform
```python
obj = bpy.context.active_object

# Location
obj.location = (x, y, z)

# Rotation (Euler angles in radians)
import math
obj.rotation_euler = (math.radians(45), 0, 0)

# Scale
obj.scale = (1.5, 1.0, 2.0)
```

### Naming
```python
obj.name = "MyObject"
```

### Selection
```python
# Select object
obj.select_set(True)

# Deselect all
bpy.ops.object.select_all(action='DESELECT')

# Make active
bpy.context.view_layer.objects.active = obj
```

## Materials

### Create Material
```python
# Create new material
mat = bpy.data.materials.new(name="MyMaterial")
mat.use_nodes = True

# Get Principled BSDF node
bsdf = mat.node_tree.nodes.get("Principled BSDF")
```

### Common Material Properties
```python
# Base Color (RGBA, values 0-1)
bsdf.inputs["Base Color"].default_value = (0.8, 0.2, 0.1, 1.0)

# Metallic (0 = dielectric, 1 = metal)
bsdf.inputs["Metallic"].default_value = 0.0

# Roughness (0 = glossy, 1 = rough)
bsdf.inputs["Roughness"].default_value = 0.5

# Transmission (for glass)
bsdf.inputs["Transmission"].default_value = 1.0
bsdf.inputs["IOR"].default_value = 1.45

# Emission
bsdf.inputs["Emission Color"].default_value = (1.0, 0.5, 0.0, 1.0)
bsdf.inputs["Emission Strength"].default_value = 2.0

# Subsurface Scattering
bsdf.inputs["Subsurface Weight"].default_value = 0.5
bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
```

### Apply Material to Object
```python
# Clear existing materials
obj.data.materials.clear()

# Add material
obj.data.materials.append(mat)
```

### Common Colors (RGB)
```python
colors = {
    "red": (0.8, 0.1, 0.1),
    "green": (0.1, 0.8, 0.1),
    "blue": (0.1, 0.3, 0.8),
    "yellow": (1.0, 0.9, 0.1),
    "orange": (1.0, 0.5, 0.1),
    "purple": (0.6, 0.2, 0.8),
    "white": (1.0, 1.0, 1.0),
    "black": (0.05, 0.05, 0.05),
    "gray": (0.5, 0.5, 0.5),
}
```

## Modifiers

### Subdivision Surface
```python
mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
mod.levels = 2  # viewport subdivisions
mod.render_levels = 3  # render subdivisions
mod.subdivision_type = 'CATMULL_CLARK'  # or 'SIMPLE'
```

### Bevel
```python
mod = obj.modifiers.new(name="Bevel", type='BEVEL')
mod.width = 0.1
mod.segments = 4
mod.limit_method = 'ANGLE'  # or 'WEIGHT', 'VGROUP'
```

### Array
```python
mod = obj.modifiers.new(name="Array", type='ARRAY')
mod.count = 5
mod.relative_offset_displace = (1.2, 0, 0)  # spacing
mod.use_constant_offset = False
mod.use_relative_offset = True
```

### Mirror
```python
mod = obj.modifiers.new(name="Mirror", type='MIRROR')
mod.use_axis = (True, False, False)  # X, Y, Z
mod.use_clip = True
mod.merge_threshold = 0.001
```

### Solidify
```python
mod = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
mod.thickness = 0.1
mod.offset = 0  # -1 to 1 (inward to outward)
```

### Boolean
```python
# Create cutter object first
bpy.ops.mesh.primitive_cube_add(location=(1, 0, 0))
cutter = bpy.context.active_object
cutter.hide_render = True  # hide in renders

# Apply boolean to base object
mod = base_obj.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'  # or 'UNION', 'INTERSECT'
mod.object = cutter
```

### Screw
```python
mod = obj.modifiers.new(name="Screw", type='SCREW')
mod.angle = math.radians(360)
mod.steps = 16
mod.screw_offset = 0.5
```

## Collections

### Create Collection
```python
collection = bpy.data.collections.new("MyCollection")
bpy.context.scene.collection.children.link(collection)
```

### Add Object to Collection
```python
collection.objects.link(obj)
```

## Parenting

### Parent Objects
```python
child.parent = parent
child.matrix_parent_inverse = parent.matrix_world.inverted()
```

## Common Patterns

### Create Object with Material
```python
def create_object_with_material(name, primitive_op, color, metallic=0.0, roughness=0.5):
    """Create primitive with material."""
    primitive_op()  # e.g., bpy.ops.mesh.primitive_cube_add
    obj = bpy.context.active_object
    obj.name = name

    mat = bpy.data.materials.new(name=f"{name}_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness

    obj.data.materials.append(mat)
    return obj
```

### Duplicate Object
```python
# Duplicate with linked data
new_obj = obj.copy()
new_obj.data = obj.data.copy()
bpy.context.collection.objects.link(new_obj)
new_obj.location = (x, y, z)
```

### Apply Smooth Shading
```python
# Smooth shading
bpy.ops.object.shade_smooth()

# Or programmatically
for face in obj.data.polygons:
    face.use_smooth = True
```

## Constraints

### Track To
```python
constraint = obj.constraints.new(type='TRACK_TO')
constraint.target = target_obj
constraint.track_axis = 'TRACK_NEGATIVE_Z'
constraint.up_axis = 'UP_Y'
```

### Copy Location
```python
constraint = obj.constraints.new(type='COPY_LOCATION')
constraint.target = target_obj
constraint.use_x = True
constraint.use_y = True
constraint.use_z = False
```

## Scale Reference

Common real-world object sizes (Blender units = meters):

- **Small objects**: 0.1 - 0.5 units (coffee cup, book)
- **Medium objects**: 0.5 - 2.0 units (chair, table)
- **Large objects**: 2.0 - 5.0 units (car, door)
- **Very large**: 5.0+ units (buildings)

## Tips

1. **Always clear the scene first** to avoid clutter
2. **Use descriptive names** for objects and materials
3. **Apply smooth shading to organic shapes** (spheres, cylinders with subdivision)
4. **Use subdivision modifier** for smooth surfaces (levels 2-3)
5. **Save frequently** using `bpy.ops.wm.save_as_mainfile()`
6. **Test material values**: Colors 0-1, Metallic 0-1, Roughness 0-1
7. **Use math.radians()** for angles (Blender uses radians internally)
8. **Check object exists** before applying modifiers
9. **Hide cutter objects** in boolean operations with `hide_render = True`
10. **Use appropriate primitives**: Sphere for round, Cylinder for tall, Cube for box-like

## Error Prevention

```python
# Check if material exists
if mat.node_tree and "Principled BSDF" in mat.node_tree.nodes:
    bsdf = mat.node_tree.nodes["Principled BSDF"]

# Ensure object is selected
bpy.context.view_layer.objects.active = obj
obj.select_set(True)

# Validate OUTPUT_BLEND_PATH exists
if 'OUTPUT_BLEND_PATH' in dir():
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
```
