"""Ollama backend for local LLM operations."""

import base64
import logging
from pathlib import Path
from typing import Optional

import httpx

from .base import BaseLLM

logger = logging.getLogger(__name__)


class OllamaBackend(BaseLLM):
    """Ollama backend for local model inference.

    Supports both text generation with LLaMA-style models
    and vision analysis with LLaVA.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        vision_model: str = "llava",
        timeout: float = 120.0,
    ):
        """Initialize Ollama backend.

        Args:
            base_url: Ollama server URL
            model: Model name for text generation
            vision_model: Model name for vision tasks
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.vision_model = vision_model
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

        logger.info(f"Initialized Ollama backend at {base_url}")
        logger.info(f"Text model: {model}, Vision model: {vision_model}")

    def _check_server(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except httpx.RequestError:
            return False

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text using Ollama.

        Args:
            prompt: The user prompt
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens (num_predict in Ollama)

        Returns:
            Generated text response
        """
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        logger.debug(f"Generating with {self.model}, temp={temperature}")
        logger.debug(f"LLM Input - System: {(system[:300] + '...') if system and len(system) > 300 else system}")
        logger.debug(f"LLM Input - Prompt: {(prompt[:500] + '...') if len(prompt) > 500 else prompt}")

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()["response"]
            logger.debug(f"LLM Output ({len(result)} chars): {(result[:500] + '...') if len(result) > 500 else result}")
            return result

        except httpx.RequestError as e:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running: {e}"
            )

    def analyze_image(
        self,
        image_path: Path | str,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Analyze a single image using LLaVA.

        Args:
            image_path: Path to the image
            prompt: Analysis prompt
            system: Optional system prompt
            max_tokens: Maximum tokens (unused, for API compatibility)

        Returns:
            Analysis response
        """
        return self.analyze_images([image_path], prompt, system, max_tokens)

    def analyze_images(
        self,
        image_paths: list[Path | str],
        prompt: str,
        system: Optional[str] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Analyze multiple images using LLaVA.

        Args:
            image_paths: List of image paths
            prompt: Analysis prompt
            system: Optional system prompt
            max_tokens: Maximum tokens (unused, for API compatibility)

        Returns:
            Analysis response
        """
        # Encode all images
        images = []
        for image_path in image_paths:
            image_path = Path(image_path)
            if not image_path.exists():
                raise FileNotFoundError(f"Image not found: {image_path}")

            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            images.append(image_data)

        payload = {
            "model": self.vision_model,
            "prompt": prompt,
            "images": images,
            "stream": False,
        }

        if system:
            payload["system"] = system

        logger.debug(f"Analyzing {len(images)} images with {self.vision_model}")
        logger.debug(f"Vision Input - Prompt: {(prompt[:500] + '...') if len(prompt) > 500 else prompt}")

        try:
            response = self.client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()

            result = response.json()["response"]
            logger.debug(f"Vision Output ({len(result)} chars): {(result[:800] + '...') if len(result) > 800 else result}")
            return result

        except httpx.RequestError as e:
            raise ConnectionError(
                f"Failed to connect to Ollama at {self.base_url}. "
                f"Ensure Ollama is running with LLaVA model: {e}"
            )

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, "client"):
            self.client.close()
