# Vibe-Blender

**AI-powered text-to-3D generator with self-correction**

Transform text descriptions into Blender 3D models. The system automatically refines models through iterative visual feedback until they match your prompt.

## Quick Start

```bash
# Install
pip install -e ".[dev]"

# Initialize config
vibe-blender init

# Edit config.yaml: set Blender path and OpenAI API key

# Verify setup
vibe-blender doctor

# Generate your first model
vibe-blender generate "A modern coffee table"
```

## How It Works

1. **Clarification** - Asks 2-3 questions if prompt is vague (interactive mode only)
2. **Planning** - Analyzes prompt → scene description
3. **Generation** - Creates Blender Python script
4. **Execution** - Runs script in Blender (headless)
5. **Rendering** - Generates 4-view grid + turntable GIF
6. **Critique** - AI evaluates renders (Pass: saves model, Fail: refines)
7. **Iteration** - Auto-refines up to 5 times until passing

## Usage

```bash
# Interactive (default) - asks clarifying questions for vague prompts
vibe-blender generate "A table"

# Detailed prompt - skips clarification automatically
vibe-blender generate "A low-poly coffee table with wooden top and metal legs"

# With reference image - matches style/materials from image
vibe-blender generate "A chair" -r reference.png

# Non-interactive - for scripts/automation
vibe-blender generate "A lamp" --no-interactive

# Custom options
vibe-blender generate "A vase" --output ./models --max-retries 3 --verbose
```

## Output Structure

```
outputs/20240126_153045/
├── pipeline.log              # Full execution log
├── iteration_01/
│   ├── script.py            # Blender script
│   ├── model.blend          # Blender file
│   └── renders/
│       ├── grid_4view.png   # 4 views (Front/Top/Side/Iso)
│       └── turntable.gif    # 360° animation
└── final/
    └── model.blend          # Final approved model
```

## Tips for Best Results

**Be Specific**
- Good: "Low-poly modern coffee table with walnut top and chrome legs"
- Vague: "A table" (triggers clarification questions)

**Include Details**
- Style: realistic, low-poly, cartoon, abstract
- Materials: wood, metal, glass, plastic
- Scale: "dining table for 6" vs "small side table"

**Use Reference Images**
- Provide style/material reference with `-r image.png`
- AI will match colors, proportions, and aesthetic from image

**Answer Questions**
- System asks only 2-3 critical questions when needed
- Answers significantly improve first-iteration quality

## Configuration

Edit `config.yaml`:

```yaml
blender:
  executable: "/Applications/Blender.app/Contents/MacOS/Blender"
  timeout: 120

llm:
  backend: "openai"  # or "ollama"
  openai:
    model: "gpt-4o"
    api_key: "${OPENAI_API_KEY}"

pipeline:
  max_retries: 5
  output_dir: "./outputs"
```

## Troubleshooting

**Config not found** → `vibe-blender init`
**Blender not found** → Run `vibe-blender doctor`, update path in config.yaml
**API key missing** → Set `export OPENAI_API_KEY="sk-..."` or add to config.yaml
**Renders too bright** → Add lighting hint: "...with soft studio lighting"
