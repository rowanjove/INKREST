"""Globally stable entity identifier generator (Milestone F).

Generates prefixed UUIDs/ULIDs to ensure globally conflict-free syncing across devices.
"""

from __future__ import annotations

import time
import uuid


def generate_stable_id(prefix: str = "ent") -> str:
    """Generate a globally unique time-ordered entity ID."""
    timestamp_ms = int(time.time() * 1000)
    random_part = uuid.uuid4().hex[:12]
    return f"{prefix}_{timestamp_ms}_{random_part}"
