"""Screen management framework for the v2 UI."""

from .manager import ScreenManagerV2, ScreenView
from .events import UIEvent
from .widgets import ButtonWidget, ListWidget, SliderWidget, ArtworkWidget

__all__ = [
    "ScreenManagerV2",
    "ScreenView",
    "UIEvent",
    "ButtonWidget",
    "ListWidget",
    "SliderWidget",
    "ArtworkWidget",
]

