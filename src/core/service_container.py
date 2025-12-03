"""Minimal service container for dependency coordination."""

from __future__ import annotations

import threading
from typing import Any, Dict, Iterable, Optional


class ServiceContainer:
    """Thread-safe registry for shared services."""

    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._lock = threading.RLock()

    def register(self, name: str, service: Any, *, overwrite: bool = False) -> None:
        """Register a service by name."""
        with self._lock:
            if not overwrite and name in self._services:
                raise KeyError(f"Service '{name}' already registered")
            self._services[name] = service

    def get(self, name: str, default: Optional[Any] = None) -> Any:
        with self._lock:
            return self._services.get(name, default)

    def require(self, name: str) -> Any:
        with self._lock:
            if name not in self._services:
                raise KeyError(f"Service '{name}' not registered")
            return self._services[name]

    def keys(self) -> Iterable[str]:
        with self._lock:
            return list(self._services.keys())

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._services)
