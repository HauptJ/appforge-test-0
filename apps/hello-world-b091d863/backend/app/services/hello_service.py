"""Business logic for the hello message."""

from __future__ import annotations


def build_hello_message(name: str) -> str:
    name = name.strip() or "world"
    # Keep it short; schema caps at 200 chars.
    return f"Hello, world! 👋 Welcome, {name[:150]}."
