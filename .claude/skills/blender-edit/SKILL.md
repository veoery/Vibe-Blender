---
name: blender-edit
description: Edit existing Blender scenes through iterative script writing and visual feedback (BlenderBench evaluation)
version: 1.0.0
---

# Blender Edit Skill (BlenderBench Evaluation)

Edit existing Blender scenes through a ReAct (Reason + Act) loop. Given a starting scene, task description, and goal image, you write Blender Python scripts to modify the scene until it matches the target.

**When to use**: BlenderBench evaluation tasks, scene editing tasks where you have a starting .blend file and need to match a goal render.

**Core workflow**: Load Scene → Analyze Difference → Write Edit Script → Execute → Compare to Goal → Iterate or Complete

## Key Differences from blender skill

| Aspect | blender (generation) | blender-edit (editing) |
|--------|---------------------|------------------------|
| Starting point | Empty scene | Existing .blend file |
| Goal | Match text description | Match goal_render image |
| Cameras | Auto-generated 4-view | Use existing Camera1/Camera2 |
| Output | view_*.png, grid | render1.png, render2.png |
| Lighting | Add 3-point lighting | Keep scene lighting |

## Blender Python API for Editing

### Loading Existing Scene
```python
import bpy

# ALWAYS load the existing .blend file first (BLEND_FILE_PATH is auto-injected)
bpy.ops.wm.open_mainfile(filepath=BLEND_FILE_PATH)

# DO NOT clear the scene - we're editing, not creating
```

### Camera Adjustments (Level 1 tasks)
```python
# Get existing camera
camera = bpy.data.objects["Camera1"]

# Adjust position
camera.location = (x, y, z)

# Adjust rotation (in radians!)
camera.rotation_euler = (rx, ry, rz)

# Adjust focal length
camera.data.lens = 50  # mm
```

### Object Manipulation (Level 2 tasks)
```python
# Get object by name
obj = bpy.data.objects["ObjectName"]

# Move object
obj.location = (x, y, z)

# Rotate object
obj.rotation_euler = (rx, ry, rz)

# Scale object
obj.scale = (sx, sy, sz)
```

### Lighting Adjustments (Level 2 tasks)
```python
# Get light object
light = bpy.data.objects["LightName"]

# Adjust energy/brightness
light.data.energy = 500  # watts

# Adjust color (RGB, values 0-1)
light.data.color = (1.0, 0.9, 0.8)
```

### Shape Keys (Level 3 tasks)
```python
# Adjust character morphing
bpy.data.shape_keys["Key"].key_blocks["ShapeKeyName"].value = 5.0
```

### Save (REQUIRED)
```python
# ALWAYS save at end (OUTPUT_BLEND_PATH is auto-injected)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
```

## ReAct Workflow for Editing

### Starting an Edit Session

Create a session directory using the task name:
```bash
# Create session directory using task path (e.g., level1/camera1)
task_id="level1/camera1"  # From task info
session_dir="outputs/blenderbench/${task_id}"
mkdir -p "$session_dir"

# Log the task info as JSON
cat > "$session_dir/task_info.json" << EOF
{
  "instance_id": "${task_id}",
  "task_description": "[description]",
  "blend_file_path": "[path to .blend]",
  "goal_render_paths": ["[path to goal_render1.png]"],
  "num_renders": 1
}
EOF
```

### Phase 1: Analyze the Task

1. **View both images**: Use Read tool to view `start_render` and `goal_render`
2. **Identify differences**: What needs to change? (camera, objects, lighting, etc.)
3. **Read start_code**: Understand current state of the scene
4. **Plan edits**: List specific changes needed

**Analysis Template**:
```
Start state: [describe what you see in start_render]
Goal state: [describe what you see in goal_render]
Differences:
- [difference 1: e.g., "camera needs to move right"]
- [difference 2: e.g., "object X needs to move to position Y"]
Required edits:
- [edit 1: e.g., "camera.location = (5.9, -5.6, 4.0)"]
```

### Phase 2: Write Edit Script

Create a Blender Python script that modifies the scene:

```python
import bpy
import math

# Load existing scene (BLEND_FILE_PATH injected by executor)
bpy.ops.wm.open_mainfile(filepath=BLEND_FILE_PATH)

# === YOUR EDITS HERE ===
# Example: Adjust camera
camera = bpy.data.objects["Camera1"]
camera.location = (5.9589, -5.6058, 4.0383)
camera.rotation_euler = (1.2839, 0.0000, 0.8149)

# === END EDITS ===

# Save modified scene (OUTPUT_BLEND_PATH injected by executor)
bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND_PATH)
```

**Critical rules**:
- ALWAYS start with `bpy.ops.wm.open_mainfile(filepath=BLEND_FILE_PATH)`
- DO NOT clear the scene or delete objects (unless task requires it)
- Use exact object names from the task (case-sensitive!)
- ALWAYS end with save operation
- Use radians for rotation (or `math.radians(degrees)`)

### Phase 3: Execute

**Workflow for ALL iterations**:

1. **Write/Edit the script**:
   - **Iteration 1**: Write to `$session_dir/script.py`
   - **Iteration 2+**: Edit `$session_dir/script.py`

2. **Copy script to iteration folder**:
   ```bash
   mkdir -p "$session_dir/iteration_XX/renders"
   cp "$session_dir/script.py" "$session_dir/iteration_XX/script.py"
   ```

3. **Execute**:
   ```bash
   BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender" \
   python .claude/skills/blender-edit/helpers/execute_blender_edit.py \
       "$session_dir/iteration_XX/script.py" \
       "/path/to/task.blend" \
       "$session_dir/iteration_XX"
   ```

**Output structure**:
```
outputs/blenderbench/{level}/{task}/   # e.g., outputs/blenderbench/level1/camera1/
├── task_info.json           # Task description and paths
├── goal_render1.png         # Target render to match
├── start_render1.png        # Initial scene render
├── script.py                # Global script (gets edited)
├── critique.log             # All critique feedback
├── iteration_01/
│   ├── script.py            # Snapshot at iteration 1
│   ├── model.blend          # Modified .blend file
│   ├── full_script.py       # With paths injected
│   ├── blender.log
│   └── renders/
│       └── render1.png      # From Camera1 (matches goal count)
├── iteration_02/            # If refined
│   └── ...
└── final/
    ├── model.blend          # Final result
    └── render1.png          # Final render (for evaluation)
```

### Phase 4: Compare to Goal (CRITICAL!)

Use the Read tool to view:
1. Your rendered output (`render1.png`)
2. The goal render (`goal_render`)

**Evaluation Criteria** (score each 0-2):

**1. Camera Match (0-2 points)** - Level 1 focus
- Viewing angle correct?
- Distance/zoom correct?
- Framing matches goal?

**2. Object Positions (0-2 points)** - Level 2 focus
- Objects in correct locations?
- Spatial relationships correct?
- Reflections/occlusions as expected?

**3. Lighting Match (0-2 points)** - Level 2 focus
- Brightness levels correct?
- Light colors match?
- Shadows in right places?

**4. Material/Shape Match (0-2 points)** - Level 3 focus
- Shape keys/morphs correct?
- Material properties unchanged (unless required)?

**5. Overall Similarity (0-2 points)**
- Does it look like the goal?
- Any obvious differences remaining?

**Total Score: 0-10**

**IMPORTANT**: Log the critique:
```bash
cat >> "$session_dir/critique.log" << EOF

=== Iteration XX - Score: X/10 ===
Camera: X/2
Objects: X/2
Lighting: X/2
Materials: X/2
Overall: X/2

Remaining differences:
- [difference 1]
- [difference 2]

Action: [iterate/complete]
EOF
```

### Phase 5: Iterate or Complete

**Decision tree**:
```
Score >= 8 OR iteration >= 5?
  YES → Mark as complete, copy to final/
  NO → Identify specific issues → Edit script → Execute → Compare
```

**When iterating**:
1. Use Edit tool on the global script (token efficient!)
2. Focus on the specific differences identified
3. Make incremental adjustments (don't rewrite everything)
4. Check numeric values carefully (positions, rotations)

**When completing**:
1. State final score: "Final Score: X/10"
2. Copy final model and renders to final/:
   ```bash
   mkdir -p "$session_dir/final"
   cp iteration_XX/model.blend final/
   cp iteration_XX/renders/render1.png final/
   ```
3. Summarize what was changed
4. Provide output paths for evaluation

## Common Edit Patterns

### Camera Position from Values
```python
# Given: camera.location = (x, y, z) in start_code
# Goal: Match goal_render viewpoint
camera = bpy.data.objects["Camera1"]
camera.location = (5.9589, -5.6058, 4.0383)  # From goal_code
camera.rotation_euler = (1.2839, 0.0000, 0.8149)
```

### Object Movement
```python
# Move object to specific position
cabinet = bpy.data.objects["Cabinet"]
cabinet.location = (0.55602, 12.284, 0.1277)

plant = bpy.data.objects["Plant"]
plant.location = (3.1586, 15.049, 0.92)
```

### Light Adjustment
```python
# Adjust multiple lights
lamp1 = bpy.data.objects["lamp_on_the_cupboard"]
lamp1.data.energy = 1.5
lamp1.data.color = (1, 1, 1)

ceiling_light = bpy.data.objects["light_on_ceilling"]
ceiling_light.data.energy = 200
```

### Shape Key Morphing
```python
# Adjust character body shape
key = bpy.data.shape_keys["Key"]
key.key_blocks["BellySag"].value = 5
key.key_blocks["BellyShrink"].value = 3
```

## Troubleshooting

**"Object 'X' not found"**
- Check exact object name (case-sensitive)
- List objects: `print([obj.name for obj in bpy.data.objects])`
- Name may have suffix like ".001"

**"Render doesn't match goal"**
- Double-check numeric values (copy exactly from goal_code if available)
- Verify units (radians vs degrees)
- Check if there are multiple steps needed

**"Camera1 not found"**
- Scene may use different camera name
- Check: `print([obj.name for obj in bpy.data.objects if obj.type == 'CAMERA'])`

**"Script runs but no visual change"**
- Verify you're modifying the right property
- Check if object is on correct layer/collection
- Ensure changes happen AFTER loading the .blend file

## BlenderBench Task Levels

### Level 1: Camera Adjustment (9 tasks)
- Single-step camera position/rotation changes
- Focus on matching viewpoint exactly
- Usually just Camera1 location + rotation_euler

### Level 2: Multi-Step Editing (9 tasks)
- Object movement (often multiple objects)
- Lighting adjustments (energy, color)
- May involve reflections/mirrors
- Requires understanding spatial relationships

### Level 3: Compositional Editing (9 tasks)
- Combines camera + object + lighting
- Shape key adjustments for characters
- Most complex, requires all skills

## Tips for Success

1. **Copy values exactly**: If goal_code is available, copy numeric values precisely
2. **Check object names**: Use exact names from the .blend file
3. **Radians matter**: Camera/object rotations use radians, not degrees
4. **Iterate on differences**: Focus critique on specific mismatches
5. **Compare carefully**: Overlay images mentally, note pixel-level differences
6. **Trust goal_render**: The goal image is ground truth, match it visually
7. **Log everything**: Detailed critique logs help track progress
8. **Max 5 iterations**: Don't over-iterate, present best result

## Evaluation Integration

After completing edits, the output can be evaluated using VIGA's evaluation scripts:

```bash
# Your outputs are structured as:
# outputs/blenderbench/{level}/{task}/final/render1.png
# Example: outputs/blenderbench/level1/camera1/final/render1.png

# Run evaluation:
python VIGA/evaluators/blenderbench/ref_based_eval.py {test_id}
python VIGA/evaluators/blenderbench/ref_free_eval.py {test_id}
python VIGA/evaluators/blenderbench/gather.py {test_id}
```

Metrics:
- **PL Loss**: Photometric (pixel) loss - lower is better
- **N-CLIP**: Negative CLIP similarity - lower is better
- **VLM Score**: GPT-4o evaluation - higher is better (0-5)
