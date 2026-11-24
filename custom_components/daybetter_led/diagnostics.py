"""Safe diagnostic formatting for BLE failures."""

from __future__ import annotations

import re

_ADDRESS = re.compile(
    r"(?i)\b(?:[0-9a-f]{2}:){5}[0-9a-f]{2}\b|\b(?:[0-9a-f]{2}-){5}[0-9a-f]{2}\b"
)
_SPACED_PACKET = re.compile(r"(?i)\b(?:[0-9a-f]{2}[ \t,]+){5,}[0-9a-f]{2}\b")
_COMPACT_PACKET = re.compile(r"(?i)\b[0-9a-f]{16,}\b")


def exception_summary(error: BaseException) -> str:
    """Describe an exception without logging BLE addresses or packet bytes."""
    message = str(error).strip()
    message = _ADDRESS.sub("<redacted address>", message)
    message = _SPACED_PACKET.sub("<redacted data>", message)
    message = _COMPACT_PACKET.sub("<redacted data>", message)
    if message:
        return f"{type(error).__name__}: {message}"
    return type(error).__name__
