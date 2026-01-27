"""Abstract base class for LLM backends."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class BaseLLM(ABC):
    """Abstract base class defining the LLM interface.

    All LLM backends must implement this interface to be compatible
    with the Vibe-Blender pipeline.
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text completion from a prompt.

        Args:
            prompt: The user prompt to complete
            system: Optional system prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        pass

    @abstractmethod
    def analyze_image(
        self,
        image_path: Path | str,
        prompt: str,
        system: Optional[str] = None,
    ) -> str:
        """Analyze an image and respond to a prompt about it.

        Args:
            image_path: Path to the image file
            prompt: Question or instruction about the image
            system: Optional system prompt for context

        Returns:
            Analysis response
        """
        pass

    @abstractmethod
    def analyze_images(
        self,
        image_paths: list[Path | str],
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Analyze multiple images and respond to a prompt.

        Args:
            image_paths: List of paths to image files
            prompt: Question or instruction about the images
            system: Optional system prompt for context

        Returns:
            Analysis response
        """
        pass
