"""Structured application logs: one JSON object per line.

Machine-readable logs are what let the service be observed (and its attribution
trail reconstructed) without parsing prose. The formatter is deliberately small:
standard record fields, whatever ``extra`` fields the caller attached, and an
``audit`` payload merged to the top level when present.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import TextIO

#: Attributes every LogRecord carries; anything else came from ``extra``.
_STANDARD_FIELDS = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__
) | {"message", "asctime", "audit"}


class JsonFormatter(logging.Formatter):
    """Render a record as a single JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        audit = getattr(record, "audit", None)
        if isinstance(audit, dict):
            # An attribution record owns its own event/timestamp/actor fields.
            payload.update(audit)
        for key, value in record.__dict__.items():
            if key not in _STANDARD_FIELDS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(stream: TextIO | None = None, level: int = logging.INFO) -> None:
    """Install the JSON handler on the ``driftguard`` logger.

    Re-running replaces DriftGuard's own handler rather than stacking another,
    so re-configuring (tests, a reload) never doubles every line.
    """
    logger = logging.getLogger("driftguard")
    logger.handlers[:] = [
        handler for handler in logger.handlers
        if not getattr(handler, "_driftguard_json", False)
    ]
    handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
    handler.setFormatter(JsonFormatter())
    handler._driftguard_json = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(level)
