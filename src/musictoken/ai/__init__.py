"""AI suggestions for MusicToken.

Pluggable LLM provider behind a small `complete_json` interface, plus a
:class:`Suggester` service that the UI calls into for:

- ``suggest_chips``   — propose new chips for a vibe prompt
- ``pick_wild``       — pick a chip from the existing library with reasoning
- ``autofill``        — given a Spotify URI / URL, infer label + genre
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from .base import AIProvider, AIError
from .fallback import FallbackProvider
from .mock import MockProvider
from .suggester import Suggester

log = logging.getLogger(__name__)


def _build_raw(backend: str, cfg: Dict[str, Any]) -> AIProvider:
    backend = (backend or "mock").lower()

    if backend == "mock":
        return MockProvider()

    if backend == "openai":
        from .openai_provider import OpenAIProvider

        return OpenAIProvider(cfg.get("openai", {}) or {})

    if backend == "anthropic":
        from .anthropic_provider import AnthropicProvider

        return AnthropicProvider(cfg.get("anthropic", {}) or {})

    if backend == "ollama":
        from .ollama_provider import OllamaProvider

        return OllamaProvider(cfg.get("ollama", {}) or {})

    log.warning("Unknown AI backend %r — using mock.", backend)
    return MockProvider()


def build_provider(cfg: Dict[str, Any]) -> AIProvider:
    """Build the configured AI provider.

    If ``ai.fallback_to_mock`` is true (default) and the primary backend
    is not already ``mock``, the returned provider transparently falls
    back to the mock provider when the primary raises :class:`AIError`.
    """
    backend = (cfg.get("backend") or "mock").lower()
    primary = _build_raw(backend, cfg)
    fallback = bool(cfg.get("fallback_to_mock", True))
    if backend != "mock" and fallback:
        return FallbackProvider(primary, MockProvider())
    return primary


__all__ = [
    "AIProvider",
    "AIError",
    "MockProvider",
    "Suggester",
    "build_provider",
]
