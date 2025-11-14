"""
FramebufferRendererV2 - Integrated renderer for V2 UI framework.

This renderer provides:
- Double-buffered rendering via PIL Image
- Automatic framebuffer size detection
- Font management
- Integration with ScreenManagerV2
- Touch event routing
"""

from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from ..framework_v2.manager import ScreenManagerV2
    from ...hardware.framebuffer import Framebuffer

logger = logging.getLogger(__name__)


class FramebufferRendererV2:
    """
    Renderer that bridges the V2 UI framework with the hardware framebuffer.

    Manages:
    - Backbuffer (PIL Image for drawing)
    - Font loading and caching
    - Screen manager rendering
    - Framebuffer presentation
    """

    def __init__(
        self,
        framebuffer: "Framebuffer",
        screen_manager: Optional["ScreenManagerV2"] = None,
        default_font_path: str = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ):
        """
        Initialize the renderer.

        Args:
            framebuffer: Hardware framebuffer instance
            screen_manager: Optional screen manager to render
            default_font_path: Path to default TrueType font
        """
        self.fb = framebuffer
        self.screen_manager = screen_manager
        self.width = framebuffer.width
        self.height = framebuffer.height

        # Create backbuffer for double-buffered rendering
        self.backbuffer = Image.new("RGB", (self.width, self.height), color=(0, 0, 0))
        self.draw = ImageDraw.Draw(self.backbuffer)

        # Font cache
        self._fonts = {}
        self._default_font_path = default_font_path

        # Pre-load common font sizes
        self._load_default_fonts()

        logger.info(f"Renderer initialized: {self.width}x{self.height}")

    def _load_default_fonts(self) -> None:
        """
        Pre-load commonly used font sizes, scaled for screen resolution.

        Font sizes are scaled relative to a 480px wide baseline:
        - 128px wide: fonts are ~27% of baseline
        - 320px wide: fonts are ~67% of baseline
        - 480px wide: fonts are 100% of baseline
        """
        # Base sizes designed for 480px width
        base_sizes = {
            "small": 14,
            "medium": 18,
            "large": 24,
            "xlarge": 32
        }

        # Scale factor based on screen width (480px is baseline)
        scale = min(self.width / 480.0, self.height / 320.0)

        # Clamp scale to reasonable range
        scale = max(0.25, min(1.5, scale))

        logger.info(f"Font scale factor: {scale:.2f} for {self.width}x{self.height}")

        for name, base_size in base_sizes.items():
            # Scale the font size, minimum 8px for readability
            scaled_size = max(8, int(base_size * scale))

            try:
                self._fonts[name] = ImageFont.truetype(self._default_font_path, scaled_size)
                logger.debug(f"Loaded font '{name}': {scaled_size}px")
            except Exception as e:
                logger.warning(f"Failed to load font '{name}' ({scaled_size}px): {e}")
                # Fallback to default bitmap font
                self._fonts[name] = ImageFont.load_default()

    def get_font(self, name: str = "medium") -> ImageFont.ImageFont:
        """
        Get a font by name.

        Args:
            name: Font name (small, medium, large, xlarge)

        Returns:
            ImageFont instance
        """
        return self._fonts.get(name, self._fonts.get("medium"))

    def clear(self, color=(0, 0, 0)) -> None:
        """
        Clear the backbuffer to a solid color.

        Args:
            color: RGB tuple (default: black)
        """
        self.draw.rectangle((0, 0, self.width, self.height), fill=color)

    def render(self) -> None:
        """
        Render the current screen from the screen manager.

        This is the main rendering entry point. It:
        1. Clears the backbuffer
        2. Calls the current screen's render method
        3. Does NOT present to framebuffer (call present() for that)
        """
        if not self.screen_manager:
            logger.warning("No screen manager attached to renderer")
            return

        # Clear backbuffer
        self.clear()

        # Prepare rendering context for the screen
        context = {
            "image": self.backbuffer,
            "draw": self.draw,
            "fonts": self._fonts,
            "width": self.width,
            "height": self.height,
            "scale_rect": self.scale_rect,
            "scale_value": self.scale_value,
            "scale": min(self.width / 480.0, self.height / 320.0)  # Uniform scale factor
        }

        # Let the screen manager render the current screen
        self.screen_manager.render(context)

    def present(self) -> None:
        """
        Present the backbuffer to the hardware framebuffer.

        This performs the actual framebuffer write and should be called
        after render() to display the frame.
        """
        try:
            self.fb.push(self.backbuffer)
        except Exception as e:
            logger.error(f"Failed to present to framebuffer: {e}")

    def set_screen_manager(self, manager: "ScreenManagerV2") -> None:
        """
        Attach a screen manager to this renderer.

        Args:
            manager: ScreenManagerV2 instance
        """
        self.screen_manager = manager
        logger.info("Screen manager attached to renderer")

    def render_and_present(self) -> None:
        """
        Convenience method to render and present in one call.

        Equivalent to:
            renderer.render()
            renderer.present()
        """
        self.render()
        self.present()

    def scale_rect(self, x_pct: float, y_pct: float, w_pct: float, h_pct: float) -> tuple:
        """
        Convert percentage-based rectangle to pixel coordinates.

        Args:
            x_pct: X position as percentage of width (0.0 - 1.0)
            y_pct: Y position as percentage of height (0.0 - 1.0)
            w_pct: Width as percentage of screen width (0.0 - 1.0)
            h_pct: Height as percentage of screen height (0.0 - 1.0)

        Returns:
            (x, y, width, height) tuple in pixels

        Example:
            # Button at 10% from left, 20% from top, 80% wide, 15% tall
            rect = renderer.scale_rect(0.1, 0.2, 0.8, 0.15)
        """
        return (
            int(x_pct * self.width),
            int(y_pct * self.height),
            int(w_pct * self.width),
            int(h_pct * self.height)
        )

    def scale_value(self, value: int, dimension: str = "width") -> int:
        """
        Scale a value from 480x320 baseline to current resolution.

        Args:
            value: Value in pixels at 480x320 resolution
            dimension: "width" or "height" for scaling reference

        Returns:
            Scaled pixel value for current resolution

        Example:
            # 50px button width at 480px -> scales to ~13px at 128px
            button_width = renderer.scale_value(50, "width")
        """
        if dimension == "width":
            return int(value * (self.width / 480.0))
        elif dimension == "height":
            return int(value * (self.height / 320.0))
        else:
            # Use minimum scale factor for uniform scaling
            scale = min(self.width / 480.0, self.height / 320.0)
            return int(value * scale)

    def close(self) -> None:
        """Clean up renderer resources."""
        # Framebuffer is owned externally, don't close it here
        self.backbuffer = None
        self.draw = None
        logger.info("Renderer closed")
