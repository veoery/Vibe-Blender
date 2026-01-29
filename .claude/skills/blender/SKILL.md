---
name: blender
description: Generate 3D Blender models through iterative script writing and visual feedback
version: 1.0.0
---

# Blender ReAct Skill

Create 3D models in Blender through an iterative ReAct (Reason + Act) loop. You write Blender Python scripts, execute them to generate renders, critique the visual results, and refine until the model matches the user's requirements.

**When to use**: User requests 3D model generation, Blender modeling, or 3D visualization tasks.

**Core workflow**: Understand → Write Script → Execute → Critique Renders → Iterate or Present

## Blender Python API Essentials

### Scene Setup
```python
import bpy
import math

# ALWAYS clear scene first
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# ALWAYS save at end (OUTPUT_BLEND_PATH is auto-injected)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
```

### Primitives
```python
# Cube
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))

# Sphere
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0))

# Cylinder
bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=2.0, location=(0, 0, 0))

# Cone
bpy.ops.mesh.primitive_cone_add(radius1=1.0, depth=2.0, location=(0, 0, 0))

# Torus
bpy.ops.mesh.primitive_torus_add(major_radius=1.0, minor_radius=0.25)

# Get active object
obj = bpy.context.active_object
obj.name = "MyObject"
```

### Transforms
```python
obj.location = (x, y, z)
obj.rotation_euler = (math.radians(45), 0, 0)  # radians!
obj.scale = (1.5, 1.0, 2.0)
```

### Materials
```python
# Create material
mat = bpy.data.materials.new(name="MyMat")
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get("Principled BSDF")

# Set properties (RGB values 0-1)
bsdf.inputs["Base Color"].default_value = (0.8, 0.2, 0.1, 1.0)  # RGBA
bsdf.inputs["Metallic"].default_value = 0.9  # 0=plastic, 1=metal
bsdf.inputs["Roughness"].default_value = 0.2  # 0=glossy, 1=rough

# Apply to object
obj.data.materials.append(mat)
```

**Common colors**: Red (0.8,0.1,0.1), Blue (0.1,0.3,0.8), Green (0.1,0.8,0.1), Yellow (1.0,0.9,0.1), White (1.0,1.0,1.0), Black (0.05,0.05,0.05)

### Modifiers
```python
# Subdivision (smooth surface)
mod = obj.modifiers.new(name="Subsurf", type='SUBSURF')
mod.levels = 2

# Bevel (round edges)
mod = obj.modifiers.new(name="Bevel", type='BEVEL')
mod.width = 0.1
mod.segments = 4

# Array (repeat object)
mod = obj.modifiers.new(name="Array", type='ARRAY')
mod.count = 5
mod.relative_offset_displace = (1.2, 0, 0)

# Boolean (cut/combine)
mod = base.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'  # or UNION, INTERSECT
mod.object = cutter
cutter.hide_render = True
```

**For organic shapes**: Use UV sphere + subdivision (levels 2)
**For mechanical parts**: Use cube/cylinder + bevel modifier

### Scale Guidelines
Blender units = meters:
- Small (cup, book): 0.1-0.5
- Medium (chair, table): 0.5-2.0
- Large (car, door): 2.0-5.0

## ReAct Workflow

**Important**: Create ONE timestamped output directory at the start (e.g., `outputs/20260128_001500/`). All iterations for this request go into subdirectories: `iteration_01/`, `iteration_02/`, etc.

### Phase 1: Understand Request
1. **Parse requirements**: Object type, style, materials, scale, details
2. **Ask clarifications if needed**:
   - Vague descriptions: "modern style" → what specifically?
   - Missing dimensions: "table" → what size?
   - Ambiguous features: "decorative" → what kind?
3. **Mental plan**:
   - Which primitives to start with?
   - What modifiers needed?
   - Material appearance (color, metallic, rough)?

**Example**:
- User: "Create a coffee table"
- Think: Start with cube for top (scale flat), 4 cylinders for legs, wood material (brown, low metallic, medium roughness)

### Phase 2: Write Script
**Iteration 1**: Use Write tool to create `outputs/TIMESTAMP/script.py`

**Iteration 2+**: Use Edit tool to modify the existing global script

Create a Blender Python script following this structure:

```python
import bpy
import math

# 1. Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# 2. Create objects with primitives
# Use appropriate primitive for each part
# Set locations to position correctly

# 3. Apply materials
# Create materials with proper colors and properties
# Assign to objects

# 4. Add modifiers
# Subdivision for smooth shapes
# Bevel for rounded edges
# Array for repeated elements

# 5. ALWAYS save
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
```

**Critical rules**:
- Start by clearing scene
- Use descriptive names for objects
- Comment complex logic
- End with save operation
- Don't import bpy/math/os (auto-injected)

### Phase 3: Execute
**Workflow for ALL iterations** (consistent process):

1. **Create timestamped output directory** (once at start):
   ```python
   from datetime import datetime
   timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
   base_output_dir = f"outputs/{timestamp}"
   ```

2. **Write/Edit the global script**:
   - **Iteration 1**: Write to `outputs/TIMESTAMP/script.py`
   - **Iteration 2+**: Edit `outputs/TIMESTAMP/script.py` (saves tokens!)

3. **Copy script to iteration folder**:
   ```bash
   mkdir -p outputs/TIMESTAMP/iteration_XX
   cp outputs/TIMESTAMP/script.py outputs/TIMESTAMP/iteration_XX/script.py
   ```

4. **Execute**:
   ```bash
   BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender" \
   python .claude/skills/blender/helpers/execute_blender.py \
       outputs/TIMESTAMP/iteration_XX/script.py \
       outputs/TIMESTAMP/iteration_XX
   ```

**Example workflow**:
```bash
# Iteration 1
Write outputs/20260127_235900/script.py
mkdir -p outputs/20260127_235900/iteration_01
cp outputs/20260127_235900/script.py outputs/20260127_235900/iteration_01/script.py
python helpers/execute_blender.py outputs/20260127_235900/iteration_01/script.py outputs/20260127_235900/iteration_01

# Iteration 2 (refine)
Edit outputs/20260127_235900/script.py  # ← Edit the global script!
mkdir -p outputs/20260127_235900/iteration_02
cp outputs/20260127_235900/script.py outputs/20260127_235900/iteration_02/script.py
python helpers/execute_blender.py outputs/20260127_235900/iteration_02/script.py outputs/20260127_235900/iteration_02
```

   **Note**: Set BLENDER_PATH to your Blender executable location

   **Output structure**:
   ```
   outputs/20260127_235900/
   ├── script.py              # Global script (gets edited)
   ├── iteration_01/
   │   ├── script.py          # Copy of script at iteration 1
   │   ├── model.blend
   │   ├── full_script.py
   │   ├── blender.log
   │   └── renders/
   │       ├── grid_4view.png
   │       └── turntable.gif
   ├── iteration_02/          # If refined
   │   ├── script.py          # Copy of script at iteration 2
   │   └── ...
   └── iteration_03/          # If refined again
       └── ...
   ```

3. **Parse JSON output** for render paths:
   - `renders.front`, `renders.top`, `renders.side`, `renders.iso`
   - `grid` (4-view combined image)
   - `blend_file` (saved .blend file)

**If error occurs**: Read error message, identify issue (syntax, missing save, invalid operation), fix and re-execute.

### Phase 4: Critique (CRITICAL!)
Use the Read tool to view ALL 4 renders. Evaluate against user request using this rubric:

#### Evaluation Criteria

**1. Accuracy (0-2 points)**
- Does it match the description?
- Are all requested features present?
- Is the object type correct?

**2. Geometry & Proportions (0-2 points)**
- Are dimensions realistic?
- Do parts fit together logically?
- Is scale appropriate?

**3. Materials & Appearance (0-2 points)**
- Colors correct?
- Surface finish appropriate (metallic, rough, glossy)?
- Visual style matches request?

**4. Completeness (0-2 points)**
- All components included?
- Details present?
- Nothing obviously missing?

**5. Quality (0-2 points)**
- Clean geometry (no artifacts)?
- Proper shading?
- Professional appearance?

**Total Score: 0-10**

#### Self-Assessment Guide

**8-10 points**: Excellent quality
- Action: Present to user with 4-view grid
- Say: "Here's your [object]. The model includes [key features]."

**5-7 points**: Good but improvable
- If iteration < 3: Identify 1-2 specific issues, iterate
- If iteration ≥ 3: Present to user (good enough)

**0-4 points**: Significant issues
- If iteration < 5: Identify problems, write improved script
- If iteration ≥ 5: Present current version, explain limitations

#### Common Issues & Fixes

**Problem**: Proportions wrong (table too tall, chair too small)
- **Fix**: Adjust scale values or primitive sizes

**Problem**: Materials look wrong (too shiny, wrong color)
- **Fix**: Adjust roughness (higher = less shiny), check RGB values

**Problem**: Object looks blocky
- **Fix**: Add subdivision modifier (levels 2) to smooth surfaces

**Problem**: Missing details
- **Fix**: Add more primitives or use boolean operations

**Problem**: Parts don't align
- **Fix**: Check location coordinates, adjust positions

### Phase 5: Iterate or Present

**Decision tree**:
```
Score ≥ 8 OR iteration ≥ 5?
  YES → Present to user with grid image
  NO → Identify 1-2 specific improvements → Write refined script → Execute → Critique
```

**When iterating**:
1. Use Edit tool on the global script (token efficient!)
2. Keep what works (don't rewrite from scratch)
3. Focus on specific issues identified in critique
4. Make incremental improvements
5. Copy the edited script to the new iteration folder before executing

**When presenting**:
1. Show 4-view grid image (use Read tool first)
2. Summarize what was created
3. Mention key features
4. Provide output directory path (e.g., `outputs/TIMESTAMP/iteration_02/`)
5. Mention how many iterations it took
6. User can find model.blend, renders, and GIF in the iteration folder

## Code Patterns

### Multiple Objects
```python
# Table with legs
# Top
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1))
top = bpy.context.active_object
top.scale = (2, 1, 0.1)

# Legs (4 corners)
for x in [-1.8, 1.8]:
    for y in [-0.8, 0.8]:
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.05, depth=1, location=(x, y, 0.5)
        )
```

### Material Variations
```python
# Metallic gold
bsdf.inputs["Base Color"].default_value = (1.0, 0.8, 0.3, 1.0)
bsdf.inputs["Metallic"].default_value = 0.9
bsdf.inputs["Roughness"].default_value = 0.2

# Matte plastic
bsdf.inputs["Base Color"].default_value = (0.8, 0.1, 0.1, 1.0)
bsdf.inputs["Metallic"].default_value = 0.0
bsdf.inputs["Roughness"].default_value = 0.6

# Glass
bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.95, 1.0)
bsdf.inputs["Transmission"].default_value = 1.0
bsdf.inputs["Roughness"].default_value = 0.0
bsdf.inputs["IOR"].default_value = 1.45
```

### Boolean Operations
```python
# Create base
bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
base = bpy.context.active_object

# Create cutter
bpy.ops.mesh.primitive_cylinder_add(radius=0.5, depth=3, location=(0, 0, 0))
cutter = bpy.context.active_object
cutter.hide_render = True
cutter.rotation_euler = (math.radians(90), 0, 0)

# Apply boolean
mod = base.modifiers.new(name="Boolean", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = cutter
```

## Troubleshooting

**"Blender executable not found"**
- User needs to set BLENDER_PATH environment variable
- Ask: "Please set BLENDER_PATH to your Blender executable path"

**"Script had errors" + Traceback**
- Read the traceback carefully
- Common causes: Typo in property name, missing object, wrong operation
- Fix the error and re-execute

**"Blender execution timed out"**
- Script too complex (too many objects, high subdivision levels)
- Simplify: Reduce modifier levels, fewer objects, or simpler operations

**"No renders generated"**
- Missing save operation
- Script crashed before completion
- Add save: `bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)`

**Renders look wrong but no errors**
- Materials not applied: Check `obj.data.materials.append(mat)`
- Objects at wrong location: Verify coordinates
- Scale issues: Check object scale and primitive sizes

## Examples

See the `examples/` directory:
- `basic_cube.py` - Minimal working script
- `materials_example.py` - Different material types
- `modifiers_example.py` - Common modifiers

## Tips for Success

1. **Start simple**: Basic primitives first, add detail in iterations
2. **One material per object**: Don't reuse materials across objects
3. **Use subdivision for organic shapes**: Makes spheres/cylinders smooth
4. **Check renders from all views**: Front might look good, top might reveal issues
5. **Realistic proportions matter**: A chair with tiny legs looks wrong
6. **Name everything**: `obj.name = "TableTop"` helps debugging
7. **Comment complex operations**: Boolean, arrays, constraints
8. **Test incrementally**: If iteration 1 has good basic shape, keep it
9. **Don't over-engineer**: User wants a cube? Make a cube, not a masterpiece
10. **Trust the renders**: Visual feedback is more reliable than code intuition

## Iteration Strategy

**Iteration 1**: Basic shape with rough proportions
- Focus: Get the overall form right
- Materials: Simple colors, default properties

**Iteration 2**: Refine proportions and add details
- Focus: Fix scale issues, add missing components
- Materials: Adjust metallic/roughness

**Iteration 3**: Polish and finalize
- Focus: Fine-tune appearance, add modifiers
- Materials: Final color/finish adjustments

**Iterations 4-5**: Edge cases only
- Only if critical issues remain
- Might need to explain limitations to user

## Quality Standards

**Minimum viable**:
- Matches basic description
- Recognizable as requested object
- No obvious errors

**Good quality**:
- Accurate proportions
- Appropriate materials
- Clean geometry
- All features present

**Excellent quality**:
- Realistic details
- Professional appearance
- Refined materials
- Polished finish

Remember: This is a skill, not a pipeline. YOU control the loop. Write scripts, execute them, critique the renders, and decide whether to iterate or present. The goal is to match the user's request efficiently, not to create perfect art.
