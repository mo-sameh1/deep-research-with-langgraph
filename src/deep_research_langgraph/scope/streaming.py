"""Presentation streaming helpers for validated scope outputs."""

from __future__ import annotations

import re
from collections.abc import Iterator


def iter_text_chunks(text: str, *, target_size: int = 24) -> Iterator[str]:
    """Yield readable chunks without splitting every character."""

    if target_size < 1:
        msg = "target_size must be at least 1"
        raise ValueError(msg)

    buffer = ""
    for token in re.findall(r"\S+\s*", text):
        buffer += token
        if len(buffer) >= target_size or "\n" in buffer:
            yield buffer
            buffer = ""
    if buffer:
        yield buffer
