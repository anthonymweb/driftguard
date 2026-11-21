"""The attribution trail: who did what, when, and on what basis.

Records are emitted as structured log lines on the ``driftguard.audit`` logger
rather than stored in the evidence tables. The trail therefore survives outside
the database and outside any single process — a refusal, an authorisation or an
export remains reconstructable from the logs alone — without ever duplicating
scan evidence or touching the token map.
"""
from __future__ import annotations

import logging
import time
from typing import Any

AUDIT_LOGGER = logging.getLogger("driftguard.audit")


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def audit(event: str, *, actor: str | None = None, **fields: Any) -> dict:
    """Record an attribution event and return the record that was written.

    ``actor`` is who performed the action (the authorising party, the API
    caller); remaining keyword fields are the event's own facts. ``None`` values
    are dropped so absent information is never rendered as null.
    """
    record: dict[str, Any] = {"event": event, "timestamp": _utcnow()}
    if actor is not None:
        record["actor"] = actor
    record.update({key: value for key, value in fields.items() if value is not None})
    AUDIT_LOGGER.info(event, extra={"audit": record})
    return record
