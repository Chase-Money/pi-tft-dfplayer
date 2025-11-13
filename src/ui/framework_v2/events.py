"""Simple event primitives for the v2 UI framework."""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple


@dataclass
class UIEvent:
    """Generic UI event container.

    Attributes:
        type: Event type (e.g., "tap", "press", "scroll").
        payload: Optional dictionary with event-specific data.
    """

    type: str
    payload: Optional[Dict[str, Any]] = None

    def get_point(self) -> Optional[Tuple[int, int]]:
        if not self.payload:
            return None
        return self.payload.get("pos")

