"""Screen manager for the v2 UI framework."""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from .events import UIEvent


class ScreenView:
    """Base class for all v2 screens."""

    name = "screen"

    def __init__(self, manager: "ScreenManagerV2", services: Optional[dict] = None) -> None:
        self.manager = manager
        self.services = services or {}

    # lifecycle hooks -------------------------------------------------
    def on_enter(self, **kwargs) -> None:  # pragma: no cover - optional override
        del kwargs

    def on_exit(self) -> None:  # pragma: no cover - optional override
        ...

    # rendering / events ---------------------------------------------
    def render(self, context: dict) -> None:  # pragma: no cover - override
        del context

    def handle_event(self, event: UIEvent) -> bool:  # pragma: no cover - override
        del event
        return False


class ScreenManagerV2:
    """Stack-based screen manager with simple navigation helpers."""

    def __init__(self, services: Optional[dict] = None) -> None:
        self._registry: Dict[str, Type[ScreenView]] = {}
        self._stack: List[ScreenView] = []
        self.services = services or {}

    # Registration ---------------------------------------------------
    def register(self, name: str, screen_cls: Type[ScreenView]) -> None:
        self._registry[name] = screen_cls

    # Navigation -----------------------------------------------------
    def push(self, name: str, **kwargs) -> ScreenView:
        screen = self._instantiate(name)
        self._stack.append(screen)
        screen.on_enter(**kwargs)
        return screen

    def pop(self) -> Optional[ScreenView]:
        if not self._stack:
            return None
        screen = self._stack.pop()
        screen.on_exit()
        return screen

    def replace(self, name: str, **kwargs) -> ScreenView:
        self.pop()
        return self.push(name, **kwargs)

    # Accessors ------------------------------------------------------
    @property
    def current(self) -> Optional[ScreenView]:
        return self._stack[-1] if self._stack else None

    def stack(self) -> List[str]:  # for debugging/testing
        return [screen.name for screen in self._stack]

    # Dispatch -------------------------------------------------------
    def handle_event(self, event: UIEvent) -> bool:
        screen = self.current
        if screen:
            return screen.handle_event(event)
        return False

    def render(self, context: dict) -> None:
        screen = self.current
        if screen:
            screen.render(context)

    # Internal -------------------------------------------------------
    def _instantiate(self, name: str) -> ScreenView:
        screen_cls = self._registry.get(name)
        if not screen_cls:
            raise KeyError(f"Screen '{name}' not registered")
        screen = screen_cls(self, self.services)
        screen.name = name
        return screen
