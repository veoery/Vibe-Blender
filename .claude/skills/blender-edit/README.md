# Blender Edit Skill for Claude Code

Edit existing Blender scenes to match target images. Designed for BlenderBench evaluation tasks where you modify a starting scene to match a goal render.

## Quick Start

### Setup (One Time)

1. **Install Blender**: Download from [blender.org](https://www.blender.org/download/) or `brew install blender` (macOS)

2. **Set environment variable**:
   ```bash
   # Add to ~/.bashrc or ~/.zshrc
   export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"  # macOS
   # or
   export BLENDER_PATH="/usr/bin/blender"  # Linux
   ```

3. **Install dependencies**: `pip install pillow`

### Usage

Provide Claude with:
- A starting `.blend` file
- A `start_render` image (current state)
- A `goal_render` image (target state)
- A `task_description` (what to change)

```
"Edit this Blender scene to match the goal image.
Task: Adjust the camera position so that the viewing angle is consistent with the target image.
Blend file: /path/to/scene.blend
Start render: /path/to/start_render.png
Goal render: /path/to/goal_render.png"
```

Claude will iteratively modify the scene until it matches the goal.

## How It Works

```
You provide: .blend file + start_render + goal_render + task
     ↓
Claude analyzes differences between start and goal
     ↓
Writes Blender Python edit script
     ↓
Executes → Renders from Camera1/Camera2
     ↓
Compares output to goal_render
     ↓
If close match (≥8/10): Done ✓
If not: Refines and repeats (max 5 iterations)
```

## Key Differences from blender skill

| Feature | blender | blender-edit |
|---------|---------|--------------|
| Purpose | Generate from scratch | Edit existing scene |
| Input | Text prompt | .blend + goal image |
| Cameras | Creates new cameras | Uses existing Camera1/Camera2 |
| Output | 4-view grid | render1.png, render2.png |
| Lighting | Adds 3-point | Preserves scene lighting |

## BlenderBench Task Types

### Level 1: Camera Adjustment
Adjust camera position and rotation to match viewpoint.
```python
camera = bpy.data.objects["Camera1"]
camera.location = (5.9, -5.6, 4.0)
camera.rotation_euler = (1.28, 0.0, 0.81)
```

### Level 2: Multi-Step Editing
Move objects, adjust lighting, handle reflections.
```python
cabinet.location = (0.55, 12.28, 0.12)
lamp.data.energy = 200
lamp.data.color = (1, 0.9, 0.8)
```

### Level 3: Compositional Editing
Combine camera, object, lighting, and shape key changes.
```python
camera.location = (x, y, z)
object.location = (x, y, z)
bpy.data.shape_keys["Key"].key_blocks["Morph"].value = 5
```

## Output Structure

```
outputs/edit_YYYYMMDD_HHMMSS/
├── task_info.txt         # Task description
├── script.py             # Global edit script
├── critique.log          # Iteration feedback
├── iteration_01/
│   ├── script.py         # Snapshot
│   ├── model.blend       # Modified scene
│   └── renders/
│       ├── render1.png   # From Camera1
│       └── render2.png   # From Camera2
├── iteration_02/         # If needed
└── final/
    └── model.blend       # Final result
```

## Evaluation

After editing, evaluate using VIGA's BlenderBench scripts:

```bash
# Assuming outputs are structured correctly
python VIGA/evaluators/blenderbench/ref_based_eval.py {test_id}
```

**Metrics**:
- **PL Loss**: Pixel-level difference (lower = better)
- **N-CLIP**: Semantic difference (lower = better)
- **VLM Score**: GPT-4o rating 0-5 (higher = better)

## Troubleshooting

### "Object not found"
- Check exact object name (case-sensitive)
- Names may have suffixes like ".001"

### "Camera1 not found"
- Scene uses different camera name
- List cameras: `[o.name for o in bpy.data.objects if o.type=='CAMERA']`

### "Render doesn't match goal"
- Double-check numeric values
- Verify radians vs degrees for rotations
- May need multiple edit steps

### "No visual change"
- Ensure edits happen AFTER loading the .blend
- Check correct property being modified

## Limitations

- Requires existing `.blend` file with Camera1
- Scene lighting is preserved (not adjusted unless task requires)
- Maximum 5 iterations per task
- GPU recommended for faster Cycles rendering

---

**Version**: 1.0.0
**License**: MIT
**Purpose**: BlenderBench evaluation and scene editing tasks
