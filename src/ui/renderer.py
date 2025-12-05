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

from .touch_debug_overlay import TouchDebugOverlay

if TYPE_CHECKING:
    from .framework.manager import ScreenManagerV2
    from ..hardware.framebuffer import Framebuffer

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

        # Touch debug overlay
        self.touch_debug = TouchDebugOverlay()

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
        3. Renders status messages (if any)
        4. Does NOT present to framebuffer (call present() for that)
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

        # Render status message overlay (if any)
        self._render_status_message()

        # Render touch debug overlay
        self.touch_debug.render(self.draw, self._fonts.get("small"))

    def present(self, dirty_rects=None) -> None:
        """
        Present the backbuffer to the hardware framebuffer.

        If dirty_rects is provided, only those regions are pushed.
        """
        try:
            # Validate framebuffer reference
            if self.fb is None:
                logger.error("CRITICAL: Framebuffer reference is None!")
                raise RuntimeError("Framebuffer not initialized")

            # Validate backbuffer
            if self.backbuffer is None:
                logger.error("CRITICAL: Backbuffer is None!")
                raise RuntimeError("Backbuffer not initialized")

            # Log detailed state before push (only in debug mode)
            logger.debug(f"Presenting: fb={self.fb}, bb_size={self.backbuffer.size}, fb_size=({self.fb.width},{self.fb.height}), dirty={dirty_rects}")

            # Push to framebuffer (full or partial)
            if dirty_rects:
                for rect in dirty_rects:
                    self.fb.push_partial(self.backbuffer, rect)
            else:
                self.fb.push(self.backbuffer)

            logger.debug("Present completed successfully")

        except Exception as e:
            # Log detailed error with stack trace
            logger.error(f"CRITICAL: Failed to present to framebuffer: {e}", exc_info=True)
            logger.error(f"  Framebuffer: {self.fb}")
            logger.error(f"  Backbuffer: {self.backbuffer}")
            logger.error(f"  Backbuffer size: {self.backbuffer.size if self.backbuffer else 'None'}")

            # Re-raise to ensure caller knows about the error
            raise

    def set_screen_manager(self, manager: "ScreenManagerV2") -> None:
        """
        Attach a screen manager to this renderer.

        Args:
            manager: ScreenManagerV2 instance
        """
        self.screen_manager = manager
        logger.info("Screen manager attached to renderer")

    def render_and_present(self, dirty_rects=None) -> None:
        """
        Convenience method to render and present in one call.

        Equivalent to:
            renderer.render()
            renderer.present(dirty_rects)
        """
        self.render()
        self.present(dirty_rects)

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

    def _render_status_message(self) -> None:
        """
        Render status message banner at bottom of screen (if any).

        Gets status from the app instance via screen manager services.
        Uses theme colors for consistency with the rest of the UI.
        """
        # Get app instance from screen manager services
        if not self.screen_manager or not hasattr(self.screen_manager, 'services'):
            return

        app = self.screen_manager.services.get('app')
        if not app or not hasattr(app, 'get_status'):
            return

        # Check if there's a status message to display
        status = app.get_status()
        if not status:
            return

        message, level = status

        # Debug logging to track duplicate renders
        logger.debug(f"Rendering status message: '{message}' ({level}) at banner_y={self.height - self.scale_value(30, 'height')}")

        # Get theme colors (with fallbacks if theme not available)
        try:
            from ui.theme import load_theme
            theme = load_theme(None)
            palette = theme.palette if theme else {}
        except Exception:
            palette = {}

        # Map status levels to theme palette keys (with hardcoded fallbacks)
        theme_mappings = {
            "info": ("status_info", "#2196F3"),
            "success": ("status_good", "#4CAF50"),
            "warning": ("status_warn", "#FF9800"),
            "error": ("status_bad", "#F44336"),
        }

        theme_key, fallback = theme_mappings.get(level, ("status_info", "#2196F3"))
        bg_color = palette.get(theme_key, fallback)

        # Determine text color based on background (light text for dark bg, dark text for light bg)
        # Use theme text color if available, otherwise choose based on background
        try:
            # Parse background color to determine if it's light or dark
            if isinstance(bg_color, str) and bg_color.startswith('#'):
                r, g, b = int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)
                # Use perceived luminance formula
                luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
                text_color = palette.get("text", "#FFFFFF") if luminance < 0.5 else palette.get("bg", "#000000")
            else:
                text_color = palette.get("text", "#FFFFFF")
        except Exception:
            text_color = "#FFFFFF"  # Safe fallback

        # Position at bottom of screen
        banner_height = self.scale_value(30, "height")
        banner_y = self.height - banner_height

        # Draw background banner
        self.draw.rectangle(
            [(0, banner_y), (self.width, self.height)],
            fill=bg_color
        )

        # Draw message text centered
        font = self.get_font("medium")

        # Get text bounding box for centering
        bbox = self.draw.textbbox((0, 0), message, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        text_x = (self.width - text_width) // 2
        text_y = banner_y + (banner_height - text_height) // 2

        self.draw.text((text_x, text_y), message, fill=text_color, font=font)

    def close(self) -> None:
        """Clean up renderer resources."""
        # Framebuffer is owned externally, don't close it here
        self.backbuffer = None
        self.draw = None
        logger.info("Renderer closed")
