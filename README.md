# Vibe-Blender

**AI-powered text-to-3D generator with self-correction**

Transform text descriptions into Blender 3D models. The system automatically refines models through iterative visual feedback until they match your prompt.

## 🎯 Two Ways to Use This Project

### 1. **Vibe-Blender CLI** (This Tool)
Lightweight, standalone command-line tool with full pipeline control.

- ✅ **For**: Developers, technical users who want full control
- 🔧 **Advantages**:
  - Lightweight Python package - easy to extend and customize
  - Full control over the generation process
  - Simple to update with new features
  - Configurable pipeline (LLM backend, iteration count, etc.)
  - Perfect for automation and scripting
- 📦 **Requires**: Python installation, OpenAI/Ollama API keys

```bash
vibe-blender generate "modern coffee table" -r reference.png
```

### 2. **Blender Skill for Claude Code** (Interactive) 👈 **Easy Start!**
Conversational 3D modeling - leverage Claude Code's built-in capabilities.

- ✅ **For**: Non-technical users, designers, anyone who wants to start quickly
- 🔧 **Advantages**:
  - No coding required - just talk to Claude naturally
  - No API keys needed (uses Claude Code's reasoning)
  - Easier onboarding - install Blender and go
  - Interactive refinement through conversation
  - Claude handles the complexity for you
- 📦 **Requires**: Only Blender installed

```
You: "Create a Japanese tea house with tokonoma alcove"
Claude: [writes script, executes, shows renders, iterates]
You: "Make it more minimalist"
Claude: [refines design and presents updated version]
```

**🚀 Try the Skill** (Located in `.claude/skills/blender/`):
1. Install Blender: `brew install blender` (macOS) or download from blender.org
2. Set environment: `export BLENDER_PATH="/path/to/blender"`
3. Ask Claude: `"Create a red cube"`

See `.claude/skills/blender/README.md` for complete setup guide.

---

**Which should I choose?**

| | CLI | Skill |
|---|---|---|
| **Best for** | Technical users | Non-technical users |
| **Control** | Full pipeline control | Claude manages workflow |
| **Extensibility** | Easy to add features | Uses Claude's built-in abilities |
| **Setup complexity** | Moderate (API keys, config) | Simple (just Blender) |
| **Interaction** | Command-line flags | Natural conversation |
| **Use case** | Automation, customization | Quick prototyping, learning |

Both use the same ReAct self-correction principles and share rendering utilities!

---

## 🎯 ReAct Loop Example: Japanese Tea House

**Prompt:** *"Design a small Japanese tea house... simplicity, asymmetry, natural materiality... include tokonoma and nijiriguchi."*

| Iteration | Visual Progress | Feedback/Refinement |
| :--- | :--- | :--- |
| **1. Blockout** | ![It 1](outputs/20260128_100000/iteration_01/renders/turntable.gif) | Established base structure. **Feedback:** Recess the tokonoma and increase interior space. |
| **2. Details** | ![It 2](outputs/20260128_100000/iteration_02/renders/turntable.gif) | Added shoji grids and tokobashira. **Feedback:** Open facade and add garden elements. |
| **3. Garden** | ![It 3](outputs/20260128_100000/iteration_03/renders/turntable.gif) | Integrated veranda and stone lantern. **Feedback:** Add a tree and fix roof pyramidal shape. |
| **4. Final** | ![It 4](outputs/20260128_100000/iteration_04/renders/turntable.gif) | **SUCCESS:** Refined composition with foliage and accurate wabi-sabi proportions. |

---

## Quick Start (CLI)

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
