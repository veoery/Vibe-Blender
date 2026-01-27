"""Configuration loading and validation for Vibe-Blender."""

import logging
import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BlenderConfig(BaseModel):
    """Blender executable configuration."""

    executable: str = Field(..., description="Path to Blender executable")
    timeout: int = Field(default=120, description="Execution timeout in seconds")

    @field_validator("executable")
    @classmethod
    def validate_executable(cls, v: str) -> str:
        """Validate that the Blender executable exists."""
        path = Path(v)
        if not path.exists():
            logging.warning(f"Blender executable not found at: {v}")
        return v


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""

    model: str = Field(default="gpt-4o", description="Model to use for generation")
    api_key: Optional[str] = Field(default=None, description="API key (prefer env var)")


class OllamaConfig(BaseModel):
    """Ollama configuration for local models."""

    base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    model: str = Field(default="llama3", description="Model for text generation")
    vision_model: str = Field(default="llava", description="Model for vision tasks")


class LLMConfig(BaseModel):
    """LLM backend configuration."""

    backend: str = Field(default="openai", description="Backend to use: openai or ollama")
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)

    @field_validator("backend")
    @classmethod
    def validate_backend(cls, v: str) -> str:
        """Validate backend choice."""
        valid = {"openai", "ollama"}
        if v not in valid:
            raise ValueError(f"Backend must be one of: {valid}")
        return v


class PipelineConfig(BaseModel):
    """Pipeline execution configuration."""

    max_retries: int = Field(default=5, ge=1, le=10, description="Maximum retry attempts")
    output_dir: str = Field(default="./outputs", description="Output directory for generated files")
    render_resolution: tuple[int, int] = Field(
        default=(512, 512), description="Render resolution (width, height)"
    )
    save_intermediate: bool = Field(
        default=True, description="Save intermediate scripts and logs"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")

    @field_validator("level")
    @classmethod
    def validate_level(cls, v: str) -> str:
        """Validate log level."""
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in valid:
            raise ValueError(f"Log level must be one of: {valid}")
        return v


class Config(BaseSettings):
    """Main configuration for Vibe-Blender."""

    model_config = SettingsConfigDict(
        env_prefix="VIBE_BLENDER_",
        env_nested_delimiter="__",
    )

    blender: BlenderConfig
    llm: LLMConfig = Field(default_factory=LLMConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, path: Path | str) -> "Config":
        """Load configuration from a YAML file.

        Args:
            path: Path to the YAML configuration file

        Returns:
            Loaded Config instance

        Raises:
            FileNotFoundError: If the config file doesn't exist
            ValueError: If the config is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        # Substitute environment variables in string values
        data = _substitute_env_vars(data)

        return cls(**data)

    @classmethod
    def find_config(cls) -> Optional[Path]:
        """Find configuration file in standard locations.

        Searches in order:
        1. ./config.yaml
        2. ./config.yml
        3. ~/.config/vibe-blender/config.yaml
        4. ~/.vibe-blender.yaml

        Returns:
            Path to config file if found, None otherwise
        """
        search_paths = [
            Path("./config.yaml"),
            Path("./config.yml"),
            Path.home() / ".config" / "vibe-blender" / "config.yaml",
            Path.home() / ".vibe-blender.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return None

    @classmethod
    def load(cls, config_path: Optional[Path | str] = None) -> "Config":
        """Load configuration from file or defaults.

        Args:
            config_path: Optional explicit path to config file

        Returns:
            Loaded Config instance

        Raises:
            FileNotFoundError: If explicit path provided but not found
        """
        if config_path:
            return cls.from_yaml(config_path)

        found = cls.find_config()
        if found:
            return cls.from_yaml(found)

        # Return config with defaults (will fail validation without blender path)
        raise FileNotFoundError(
            "No configuration file found. Create config.yaml or use --config option."
        )


def _substitute_env_vars(data: dict) -> dict:
    """Recursively substitute ${VAR} patterns with environment variables."""
    if isinstance(data, dict):
        return {k: _substitute_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_substitute_env_vars(item) for item in data]
    elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
        var_name = data[2:-1]
        return os.environ.get(var_name, data)
    return data


def setup_logging(config: Config, log_file: Optional[Path] = None) -> None:
    """Configure logging based on config settings.

    Args:
        config: Application configuration
        log_file: Optional path to log file
    """
    log_level = getattr(logging, config.logging.level)
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    # File handler (if log_file provided)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(log_format, date_format))
        root_logger.addHandler(file_handler)

    # Suppress debug logs from third-party libraries
    # Keep only INFO and above for noisy libraries
    third_party_loggers = [
        "PIL",
        "PIL.PngImagePlugin",
        "PIL.Image",
        "imageio",
        "imageio_ffmpeg",
        "httpx",
        "urllib3",
        "openai",
    ]
    for logger_name in third_party_loggers:
        logging.getLogger(logger_name).setLevel(logging.INFO)
