"""Resolve SynVow credentials for integrated YMAI nodes."""

from __future__ import annotations

from . import synvow_auth


def resolve_api_key() -> str:
    """Resolve the SynVow API key saved by the plugin login flow."""
    return synvow_auth.read_api_key()


def require_api_key() -> str:
    return resolve_api_key()
