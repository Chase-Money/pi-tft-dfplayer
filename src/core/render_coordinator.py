"""Render coordinator for the v2 UI framework.

Handles screen rendering coordination and framebuffer presentation.
"""

from typing import Optional, Tuple


class RenderCoordinator:
    """Coordinates rendering operations between screen manager and renderer."""

    def __init__(self, screen_manager, renderer):
        """
        Initialize the render coordinator.

        Args:
            screen_manager: ScreenManagerV2 instance
            renderer: FramebufferRendererV2 instance
        """
        self.screen_manager = screen_manager
        self.renderer = renderer

    def render_frame(self, refreshed: bool) -> bool:
        """
        Render a frame if needed.

        Args:
            refreshed: Whether the screen content has changed

        Returns:
            bool: True if a frame was rendered
        """
        if not refreshed:
            return False

        # Force full screen refresh after screen navigation to prevent artifacts
        if self.screen_manager.needs_full_refresh():
            dirty_rects = None
            self.screen_manager.clear_refresh_flag()
        else:
            # Get dirty rect hints from screen if available (for partial updates)
            # Defaults to None for full screen update if screen doesn't provide hints
            dirty_rects = getattr(self.screen_manager.current, "last_dirty", None)

        self.renderer.render()
        self.renderer.present(dirty_rects=dirty_rects)
        self.renderer.present(dirty_rects=dirty_rects)
        return True