"""OpenAI API backend for LLM operations."""

import base64
import logging
import os
from pathlib import Path
from typing import Optional

from openai import OpenAI

from .base import BaseLLM

logger = logging.getLogger(__name__)


class OpenAIBackend(BaseLLM):
    """OpenAI API backend implementation.

    Supports both text generation and vision analysis using GPT-4o.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
    ):
        """Initialize OpenAI backend.

        Args:
            model: Model name to use (default: gpt-4o)
            api_key: API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")

        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"Initialized OpenAI backend with model: {model}")

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text completion using OpenAI API.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response
        """
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": prompt})

        logger.debug(f"Generating with {self.model}, temp={temperature}")
        logger.debug(f"LLM Input - System: {system}")
        logger.debug(f"LLM Input - Prompt: {prompt}")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        # if max_tokens:
        #     kwargs["max_completion_tokens"] = max_tokens

        response = self.client.chat.completions.create(**kwargs)
        result = response.choices[0].message.content

        logger.debug(f"LLM Output ({len(result)} chars): {(result[:500] + '...') if len(result) > 500 else result}")
        return result

    def analyze_image(
        self,
        image_path: Path | str,
        prompt: str,
        system: Optional[str] = None,
    ) -> str:
        """Analyze a single image using GPT-4o vision.

        Args:
            image_path: Path to the image
            prompt: Analysis prompt
            system: Optional system prompt

        Returns:
            Analysis response
        """
        return self.analyze_images([image_path], prompt, system)

    def analyze_images(
        self,
        image_paths: list[Path | str],
        prompt: str,
        system: Optional[str] = None,
    ) -> str:
        """Analyze multiple images using GPT-4o vision.

        Args:
            image_paths: List of image paths
            prompt: Analysis prompt
            system: Optional system prompt

        Returns:
            Analysis response
        """
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        # Build content with images and text
        content = []

        for image_path in image_paths:
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            # Determine media type
            suffix = image_path.suffix.lower()
            media_types = {
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".gif": "image/gif",
                ".webp": "image/webp",
            }
            media_type = media_types.get(suffix, "image/png")

            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{media_type};base64,{image_data}",
                    "detail": "high",
                },
            })

        content.append({"type": "text", "text": prompt})

        messages.append({"role": "user", "content": content})

        logger.debug(f"Analyzing {len(image_paths)} images with {self.model}")
        logger.debug(f"Vision Input - Prompt: {(prompt[:500] + '...') if len(prompt) > 500 else prompt}")

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            # max_completion_tokens=2000,
        )

        result = response.choices[0].message.content
        logger.debug(f"Vision Output ({len(result)} chars): {(result[:800] + '...') if len(result) > 800 else result}")

        return result
