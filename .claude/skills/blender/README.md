# Blender ReAct Skill for Claude Code

Generate 3D models in Blender through natural language. Claude writes Blender Python scripts, executes them, critiques the visual output, and refines until the result matches your requirements.

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

3. **Install dependencies**: `pip install pillow imageio`

4. **Verify**: `blender --version`

### Usage

Just ask Claude to create 3D models:

```
"Create a red cube"
"Make a modern coffee table with glass top"
"Generate a metallic gold sphere"
```

Claude will show you a 4-view render and save files to `outputs/TIMESTAMP/model.blend`

## Features

- **Natural language to 3D**: Describe what you want, Claude creates it
- **Self-correction loop**: Automatically iterates based on visual feedback (up to 5 times)
- **Multi-view renders**: See your model from 4 angles (front, top, side, isometric)
- **Turntable GIF**: 360° rotation animation
- **No LLM API required**: Uses Claude Code's built-in reasoning
- **Portable**: Standalone skill with minimal dependencies

## How It Works

```
You: "Create a modern coffee table"
     ↓
Claude writes Blender Python script
     ↓
Executes → Generates 4-view renders (30-60s)
     ↓
Claude critiques: Evaluates quality (0-10 score)
     ↓
If good (≥8/10): Shows result ✓
If needs work: Refines and repeats (max 5 iterations)
```

## Installation

### 1. Install Blender

Download from [blender.org](https://www.blender.org/download/) or use your package manager:

```bash
# macOS
brew install blender

# Ubuntu/Debian
sudo apt install blender

# Arch Linux
sudo pacman -S blender
```

### 2. Set Environment Variable

Tell the skill where Blender is installed:

```bash
# Find Blender path
which blender  # Linux/macOS
# or
where blender  # Windows

# Set environment variable (add to ~/.bashrc or ~/.zshrc)
export BLENDER_PATH="/path/to/blender"

# Example paths:
# macOS Homebrew: /opt/homebrew/bin/blender
# macOS App: /Applications/Blender.app/Contents/MacOS/Blender
# Linux: /usr/bin/blender
# Windows: C:\Program Files\Blender Foundation\Blender\blender.exe
```

### 3. Install Python Dependencies

The skill requires PIL (Pillow) and imageio for post-processing:

```bash
pip install pillow imageio
```

### 4. Verify Setup

```bash
# Test Blender
blender --version

# Should output something like:
# Blender 4.0.0
```

## Usage

### Basic Usage

Simply ask Claude to create a 3D model:

```
You: "Create a red cube"
You: "Make a modern office chair"
You: "Generate a wooden table with 4 legs"
```

Claude will:
1. Write a Blender script
2. Execute it and generate renders
3. Evaluate the quality
4. Iterate if needed (up to 5 times)
5. Show you the final 4-view render

### Advanced Requests

Be specific for better results:

```
You: "Create a metallic gold sphere with a rough surface, about 0.5 meters in diameter"

You: "Make a coffee mug - ceramic white, handle on the right, realistic proportions"

You: "Generate a bookshelf with 4 shelves, wooden material, modern minimalist style"
```

### Clarifying Questions

If your request is vague, Claude may ask for clarification:

```
You: "Create a table"
Claude: "What style? (modern/rustic/industrial) What size? What material?"
You: "Modern, dining table size, glass top with metal legs"
```

### Viewing Results

Claude will show you a 4-view grid image directly in the conversation:
- **Front view**: Shows the object from the front
- **Top view**: Bird's eye view
- **Side view**: Profile view
- **Isometric view**: 3D perspective view

You'll also get:
- A turntable GIF (360° rotation)
- The `.blend` file path (open in Blender)

### Output Locations

All outputs are saved with timestamps and iteration tracking:
```
outputs/YYYYMMDD_HHMMSS/
├── iteration_01/           # First attempt
│   ├── model.blend
│   ├── full_script.py
│   ├── blender.log
│   └── renders/
│       ├── view_front.png
│       ├── view_top.png
│       ├── view_side.png
│       ├── view_iso.png
│       ├── grid_4view.png
│       ├── turntable.gif
│       └── turntable_frames/
├── iteration_02/           # If refined
│   └── ...
└── iteration_03/           # If refined again
    └── ...
```

Each iteration is preserved so you can compare improvements. Example: `outputs/20260127_235900/iteration_02/`

## Tips for Better Results

**Be specific**:
- ❌ "Create a table" → ✅ "Create a modern dining table, glass top, metal legs, 2m long"

**Mention materials**:
- ❌ "Make a sphere" → ✅ "Make a metallic gold sphere with rough surface"

**Include scale**:
- ❌ "Generate a mug" → ✅ "Generate a coffee mug, 10cm tall, realistic proportions"

**Request refinements**:
- "Make the legs thicker"
- "Change the color to dark blue"
- "Add more detail"

## How Claude Works

### ReAct Loop
Claude uses a **Reason + Act** loop:

1. **Reason**: Understand your request, plan approach
2. **Act**: Write Blender Python script
3. **Execute**: Run script, generate renders
4. **Evaluate**: Critique visual output (score 0-10)
5. **Decide**: Iterate (if score < 8) or present (if score ≥ 8)

### Evaluation Criteria
Claude scores models on:
- **Accuracy**: Does it match the description?
- **Geometry**: Are proportions correct?
- **Materials**: Appropriate colors and finishes?
- **Completeness**: All features present?
- **Quality**: Clean geometry, no artifacts?

### Iteration Limits
- Maximum 5 iterations per model
- Prevents infinite loops
- Usually succeeds in 1-3 iterations

## What Can It Create?

**✅ Good for**:
- Furniture (tables, chairs, shelves)
- Simple objects (cups, bowls, boxes)
- Geometric shapes with materials
- Basic architectural elements
- Product mockups

**⚠️ Challenging**:
- Very organic shapes (humans, animals)
- Highly detailed models
- Complex assemblies (100+ parts)

**❌ Not supported yet**:
- Animation (keyframes)
- Image textures (only procedural materials)
- Importing existing models

## Troubleshooting

### "Blender executable not found"
**Solution**: Set `BLENDER_PATH` environment variable

```bash
export BLENDER_PATH="/usr/bin/blender"
# or
export BLENDER_PATH="/Applications/Blender.app/Contents/MacOS/Blender"
```

### "No module named 'PIL'" or "No module named 'imageio'"
**Solution**: Install dependencies

```bash
pip install pillow imageio
```

### "Blender execution timed out after 90s"
**Cause**: Script too complex (too many subdivisions, objects, or heavy operations)

**Solution**: Simplify the request or ask Claude to reduce complexity

### Renders look wrong but no errors
**Possible causes**:
- Materials not applied correctly
- Objects positioned incorrectly
- Scale issues

**Solution**: Ask Claude to fix specific issues:
```
You: "The table legs are too thin, make them thicker"
You: "The color should be darker red"
```

### Script errors (traceback in output)
**Solution**: Claude should automatically fix these, but if not:
- Read the error message
- Ask Claude: "Fix the error in the script"

### Low quality renders
**Causes**:
- Missing subdivision modifier (blocky surfaces)
- Wrong material properties (too shiny, wrong color)
- Poor proportions

**Solution**: Claude should catch these in critique phase and iterate

## Limitations

- **Complexity**: Very complex models (100+ objects) may timeout
- **Textures**: No image texture support (only procedural materials)
- **Animation**: Static models only (no keyframe animation)
- **Physics**: No physics simulation
- **Speed**: Each iteration takes 20-60 seconds (rendering time)

## Advanced

### Manual Execution
```bash
# From the skill directory
cd /path/to/.claude/skills/blender
BLENDER_PATH="/path/to/blender" \
python helpers/execute_blender.py \
    /path/to/script.py \
    /path/to/outputs/$(date +%Y%m%d_%H%M%S)
```

### Examples
Run the included examples:
```bash
BLENDER_PATH="/path/to/blender" \
python .claude/skills/blender/helpers/execute_blender.py \
    .claude/skills/blender/examples/basic_cube.py \
    outputs/test
```

See `examples/` directory for:
- `basic_cube.py` - Simple cube with material
- `materials_example.py` - Different material types
- `modifiers_example.py` - Common modifiers (bevel, array, boolean)

## Technical Details

- **Render engine**: Cycles (GPU preferred) or EEVEE fallback
- **Resolution**: 512x512 per view
- **Samples**: 64 (quality/speed balance)
- **Performance**: 40-60 seconds per iteration
- **Iteration limit**: Maximum 5 attempts

## FAQ

**Q: Can I edit the .blend file?**
A: Yes! Open `outputs/TIMESTAMP/model.blend` in Blender for manual refinement.

**Q: Does it use my GPU?**
A: Yes, if available. Falls back to CPU if needed.

**Q: What if I don't like the result?**
A: Ask for changes: "Make it bigger", "Change color to blue", "Add more detail"

**Q: Can it import existing models?**
A: No, this skill generates models from scratch only.

---

**Version**: 1.0.0
**License**: MIT
**Credits**: Built on Blender's Python API

**Ready to create?** Just ask Claude: "Create a [description of 3D object]"
