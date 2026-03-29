"""Shared Anthropic client — single instance reused across the application."""

import anthropic

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    """Return a shared Anthropic client instance (created once, reused)."""
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client
