"""Blender script executor."""

import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import Config
from ..models.schemas import GeneratedScript, RenderOutput
from .renderer import RenderManager

logger = logging.getLogger(__name__)


class BlenderExecutor:
    """Executes Blender Python scripts in headless mode.

    Handles subprocess management, timeout protection, and
    output capture for debugging.
    """

    def __init__(self, config: Config):
        """Initialize the executor.

        Args:
            config: Application configuration
        """
        self.blender_path = config.blender.executable
        self.timeout = config.blender.timeout
        self.render_resolution = config.pipeline.render_resolution
        self.save_intermediate = config.pipeline.save_intermediate

    def execute(
        self,
        script: GeneratedScript,
        output_dir: Path,
    ) -> RenderOutput:
        """Execute a Blender script and render output.

        Args:
            script: The generated script to execute
            output_dir: Directory for output files

        Returns:
            RenderOutput with paths to generated files

        Raises:
            RuntimeError: If Blender execution fails
            TimeoutError: If execution exceeds timeout
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Update the global script (source of truth across iterations)
        global_script_path = output_dir / "script.py"
        global_script_path.write_text(script.code)
        logger.info(f"Updated global script at {global_script_path}")

        # Create iteration subdirectory and copy global script with injected paths
        iter_dir = output_dir / f"iteration_{script.iteration:02d}"
        iter_dir.mkdir(exist_ok=True)

        script_path = iter_dir / "script.py"
        blend_path = iter_dir / "model.blend"
        render_dir = iter_dir / "renders"
        render_dir.mkdir(exist_ok=True)

        full_script = self._prepare_script(
            script.code,
            blend_path=blend_path,
            render_dir=render_dir,
        )

        script_path.write_text(full_script)
        logger.info(f"Wrote iteration script to {script_path}")

        # Execute Blender
        log_path = iter_dir / "blender.log"
        success, stdout, stderr = self._run_blender(script_path, log_path)

        # Check for Python errors in stderr (even if Blender returned 0)
        blender_error = None
        if stderr and ("Traceback" in stderr or "Error:" in stderr or "Exception:" in stderr):
            # Extract the relevant error portion
            blender_error = self._extract_python_error(stderr)
            logger.warning(f"Blender script had errors: {blender_error[:200]}...")

        # Post-process: create grid and GIF using host Python (with PIL)
        grid_image = render_dir / "grid_4view.png"
        turntable_gif = render_dir / "turntable.gif"

        render_manager = RenderManager(self.render_resolution)

        # Create grid from individual views
        view_images = [
            render_dir / "view_front.png",
            render_dir / "view_top.png",
            render_dir / "view_side.png",
            render_dir / "view_iso.png",
        ]
        existing_views = [p for p in view_images if p.exists()]

        if len(existing_views) >= 4:
            render_manager.create_grid_image(
                existing_views[:4],
                grid_image,
                labels=["Front", "Top", "Side", "Isometric"],
            )
        elif len(existing_views) > 0:
            # Use whatever views we have
            logger.warning(f"Only {len(existing_views)} views found, creating partial grid")
            # For partial grid, just use the first available as a placeholder
            render_manager.create_grid_image(
                (existing_views * 4)[:4],  # repeat to fill 4 slots
                grid_image,
            )

        # Create turntable GIF
        turntable_frames_dir = render_dir / "turntable_frames"
        if turntable_frames_dir.exists():
            render_manager.create_turntable_gif(
                turntable_frames_dir,
                turntable_gif,
            )

        return RenderOutput(
            script_path=script_path,
            blend_file=blend_path if blend_path.exists() else None,
            grid_image=grid_image if grid_image.exists() else None,
            turntable_gif=turntable_gif if turntable_gif.exists() else None,
            render_dir=render_dir,
            blender_error=blender_error,
        )

    def _extract_python_error(self, stderr: str) -> str:
        """Extract Python error from Blender stderr.

        Args:
            stderr: Full stderr output

        Returns:
            Extracted error message
        """
        lines = stderr.strip().split('\n')

        # Find the traceback start
        traceback_start = -1
        for i, line in enumerate(lines):
            if line.startswith("Traceback"):
                traceback_start = i
                break

        if traceback_start >= 0:
            # Return from traceback to end
            return '\n'.join(lines[traceback_start:])

        # If no traceback, look for error lines
        error_lines = [l for l in lines if "Error" in l or "Exception" in l]
        if error_lines:
            return '\n'.join(error_lines)

        # Return last 10 lines as fallback
        return '\n'.join(lines[-10:])

    def _prepare_script(
        self,
        code: str,
        blend_path: Path,
        render_dir: Path,
    ) -> str:
        """Prepare the full script with output paths and rendering code.

        Args:
            code: Original generated code
            blend_path: Path to save .blend file
            render_dir: Directory for renders

        Returns:
            Complete script with injected variables and rendering code
        """
        from ..templates.render_views import RENDER_TEMPLATE

        # Inject output variables at the start
        header = f'''# Auto-generated by Vibe-Blender
# Timestamp: {datetime.now().isoformat()}

import bpy
import math
import os

# Output paths (injected by executor)
OUTPUT_BLEND_PATH = r"{blend_path}"
OUTPUT_DIR = r"{render_dir}"
RENDER_RESOLUTION = {tuple(self.render_resolution)}

'''

        # Remove duplicate imports from the generated code
        code_lines = code.split('\n')
        filtered_lines = []
        for line in code_lines:
            # Skip import lines we've already added
            if line.strip().startswith('import bpy'):
                continue
            if line.strip().startswith('import math'):
                continue
            if line.strip().startswith('import os'):
                continue
            filtered_lines.append(line)

        code = '\n'.join(filtered_lines)

        # Combine: header + user code + rendering
        return header + code + '\n\n' + RENDER_TEMPLATE

    def _run_blender(
        self,
        script_path: Path,
        log_path: Path,
    ) -> tuple[bool, str, str]:
        """Run Blender with the script.

        Args:
            script_path: Path to the Python script
            log_path: Path to save logs

        Returns:
            Tuple of (success, stdout, stderr)

        Raises:
            RuntimeError: If Blender fails
            TimeoutError: If execution times out
        """
        cmd = [
            self.blender_path,
            "--background",
            "--python",
            str(script_path),
        ]

        logger.info(f"Running: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            )

            stdout = result.stdout
            stderr = result.stderr

            # Save logs
            with open(log_path, "w") as f:
                f.write("=== STDOUT ===\n")
                f.write(stdout)
                f.write("\n=== STDERR ===\n")
                f.write(stderr)

            if result.returncode != 0:
                logger.error(f"Blender exited with code {result.returncode}")
                logger.error(f"Stderr: {stderr[:1000]}")
                raise RuntimeError(
                    f"Blender execution failed (code {result.returncode}): {stderr[:500]}"
                )

            logger.info("Blender execution completed successfully")
            return True, stdout, stderr

        except subprocess.TimeoutExpired:
            logger.error(f"Blender execution timed out after {self.timeout}s")
            raise TimeoutError(f"Blender execution timed out after {self.timeout} seconds")

    def validate_blender(self) -> bool:
        """Check if Blender is available and working.

        Returns:
            True if Blender is functional
        """
        try:
            result = subprocess.run(
                [self.blender_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                logger.info(f"Found: {version_line}")
                return True
            return False
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            logger.error(f"Blender validation failed: {e}")
            return False
