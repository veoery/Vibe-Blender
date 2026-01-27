# Vibe-Blender

**AI-powered text-to-3D model generator with self-correction**

Generate Blender 3D models from text descriptions. The system automatically refines models through multiple iterations using visual feedback, ensuring high-quality results.

## How It Works

1. **Clarification** (Interactive Mode): If your prompt is unclear, the system will ask 2-3 quick questions to understand what you want.

2. **Planning**: Analyzes your prompt and creates a detailed scene description.

3. **Generation**: Writes a Blender Python script to create the model.

4. **Execution**: Runs the script in Blender (headless mode).

5. **Rendering**: Generates a 4-view grid and turntable GIF animation.

6. **Critique**: AI analyzes the renders and decides if they match your prompt.
   - ✓ Pass: Saves the final .blend file
   - ✗ Fail: Provides feedback and generates an improved version

7. **Iteration**: Automatically refines the model up to 5 times until it passes.

---

## Development Setup

```bash
# Install with uv
uv venv

# Activate with
source .venv/bin/activate

# Install with
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

## Quick Start

```bash
# 1. Initialize config
vibe-blender init

# 2. Edit config.yaml to set:
#    - Blender executable path
#    - OpenAI API key (or configure Ollama)

# 3. Verify your setup
vibe-blender doctor

# 4. Generate your first model
vibe-blender generate "A cyberpunk coffee table"
```

## Usage Examples

### Interactive Mode (Default)
When your prompt is vague, the system will ask clarifying questions:

```bash
vibe-blender generate "A table"

# The system will ask:
# - What type of table? (coffee/dining/desk/etc.)
# - What style? (modern/traditional/industrial/etc.)
# Answer the questions to get better results!
```

### Clear Prompts
Detailed prompts skip clarification automatically:

```bash
vibe-blender generate "A low-poly modern coffee table with wooden top and metal legs"
# No questions needed - generates immediately
```

### Image-Reference Mode
For scripts or batch processing:

```bash
vibe-blender generate "A chair" -r path/to/ref_image
```

### Non-Interactive Mode
For scripts or batch processing:

```bash
vibe-blender generate "A chair" --no-interactive
# Skips questions, uses AI assumptions
```

### Additional Options

```bash
# Verbose logging
vibe-blender generate "A lamp" --verbose

# Custom output directory
vibe-blender generate "A vase" --output ./my-models

# Limit iterations
vibe-blender generate "A sculpture" --max-retries 3
```

## Output Files

Each generation creates a timestamped directory with all results:

```
outputs/20240126_153045/
├── pipeline.log          # Full execution log with clarification Q&A
├── iteration_01/
│   ├── script.py         # Generated Blender script
│   ├── model.blend       # Blender file
│   └── renders/
│       ├── grid_4view.png    # 4-view grid (Front/Top/Side/Iso)
│       └── turntable.gif     # 360° rotation animation
├── iteration_02/
│   └── ...               # Refined versions (if needed)
└── final/
    └── model.blend       # Final approved model
```

## Tips for Best Results

**Write Detailed Prompts**
- Good: "A low-poly modern coffee table with wooden top and chrome legs"
- Vague: "A table" (will trigger clarification questions)

**Specify Style**
- Mention visual style: realistic, low-poly, cartoon, abstract
- Include materials: wood, metal, glass, plastic

**Include Dimensions**
- For furniture: "dining table for 6 people" vs "small side table"
- For objects: "tall vase" vs "miniature sculpture"

**Answer Clarification Questions**
- The system only asks 2-3 critical questions when needed
- Your answers significantly improve first-iteration quality
- You can skip questions to proceed with AI assumptions

## Configuration

Edit `config.yaml` after running `vibe-blender init`:

```yaml
blender:
  executable: "/Applications/Blender.app/Contents/MacOS/Blender"
  timeout: 120

llm:
  backend: "openai"  # or "ollama"
  openai:
    model: "gpt-4o"
    api_key: "${OPENAI_API_KEY}"  # or set directly

pipeline:
  max_retries: 5
  output_dir: "./outputs"
```

## Troubleshooting

**"Config file not found"**
```bash
vibe-blender init
```

**"Blender not found"**
- Run `vibe-blender doctor` to check your setup
- Update the `blender.executable` path in `config.yaml`

**"API key missing"**
- Set environment variable: `export OPENAI_API_KEY="sk-..."`
- Or add it directly to `config.yaml`

**Renders too bright/dark**
- The system now includes improved lighting guidelines
- Try regenerating with a more specific lighting description
- Example: "...with soft studio lighting" or "...in natural daylight"