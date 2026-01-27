"""LLM backends for Vibe-Blender."""

from .base import BaseLLM
from .openai_backend import OpenAIBackend
from .ollama_backend import OllamaBackend


def create_llm(backend: str, **kwargs) -> BaseLLM:
    """Factory function to create LLM backend.

    Args:
        backend: Either "openai" or "ollama"
        **kwargs: Backend-specific configuration

    Returns:
        Configured LLM backend instance
    """
    backends = {
        "openai": OpenAIBackend,
        "ollama": OllamaBackend,
    }

    if backend not in backends:
        raise ValueError(f"Unknown backend: {backend}. Available: {list(backends.keys())}")

    return backends[backend](**kwargs)


__all__ = ["BaseLLM", "OpenAIBackend", "OllamaBackend", "create_llm"]
