"""
Theme definitions and lightweight loader for the DFPlayer UI.

This is a preparatory stub for user-extensible themes (LCARS, retro, etc.).
It reads JSON theme files from the repo's `themes/` directory or a custom path
specified by DFPLAYER_THEME (name or absolute path).
"""

from dataclasses import dataclass, field
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from PIL import ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    ImageFont = None  # type: ignore

logger = logging.getLogger(__name__)


Color = Tuple[int, int, int]


def _hex_to_rgb(value: str, default: Color) -> Color:
    """Convert #RRGGBB hex to RGB tuple, falling back on errors."""
    if not isinstance(value, str):
        return default
    value = value.strip()
    if value.startswith("#"):
        value = value[1:]
    if len(value) != 6:
        return default
    try:
        return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except Exception:
        return default


def _merge(
    defaults: Dict[str, Any],
    incoming: Optional[Dict[str, Any]],
    section_name: str = "unknown",
    validate_types: bool = True
) -> Dict[str, Any]:
    """
    Shallow merge preserving defaults when keys are missing.

    Args:
        defaults: Default values dictionary
        incoming: Incoming values to merge
        section_name: Name of section for logging (e.g., "palette", "metrics")
        validate_types: Whether to validate and log type mismatches

    Returns:
        Merged dictionary
    """
    data = dict(defaults)
    if not isinstance(incoming, dict):
        return data

    for key, value in incoming.items():
        # Type validation based on section
        if validate_types and key in defaults:
            default_val = defaults[key]
            expected_type = type(default_val)

            # Special handling for numeric types (allow int/float interchangeably)
            if isinstance(default_val, (int, float)):
                if not isinstance(value, (int, float)):
                    logger.warning(
                        "Type mismatch in %s.%s: expected number, got %s (using default)",
                        section_name, key, type(value).__name__
                    )
                    continue  # Skip this value, keep default
            # Special handling for lists
            elif isinstance(default_val, list):
                if not isinstance(value, list):
                    logger.warning(
                        "Type mismatch in %s.%s: expected list, got %s (using default)",
                        section_name, key, type(value).__name__
                    )
                    continue
            # All other types must match exactly
            elif not isinstance(value, expected_type):
                logger.warning(
                    "Type mismatch in %s.%s: expected %s, got %s (using default)",
                    section_name, key, expected_type.__name__, type(value).__name__
                )
                continue

        data[key] = value
    return data


def _clamp(value: float, min_val: float, max_val: float) -> int:
    """Clamp a value to a specified range and return as int."""
    return int(max(min_val, min(max_val, value)))


def _resolve_reference(ref: str, palette: Dict[str, Any], fallback: Color) -> Color:
    """
    Resolve a reference string to an RGB color from the palette.

    Supports:
    - "bg" → palette["bg"]
    - "accents[0]" → palette["accents"][0]
    - "status_good" → palette["status_good"]

    Args:
        ref: Reference string (e.g., "bg", "accents[0]")
        palette: Dictionary of palette colors
        fallback: Color to return if resolution fails

    Returns:
        RGB tuple or fallback
    """
    if not isinstance(ref, str):
        return fallback

    ref = ref.strip()

    # Check for array indexing pattern: "accents[0]"
    if "[" in ref and "]" in ref:
        try:
            key, idx_part = ref.split("[", 1)
            idx_str = idx_part.rstrip("]")
            idx = int(idx_str)

            array_val = palette.get(key.strip())
            if isinstance(array_val, list) and 0 <= idx < len(array_val):
                return _hex_to_rgb(array_val[idx], fallback)
        except (ValueError, IndexError, TypeError):
            pass
        return fallback

    # Simple key lookup
    hex_val = palette.get(ref)
    if hex_val:
        return _hex_to_rgb(hex_val, fallback)

    return fallback


def _font_available(font_name: str, size: int = 12) -> bool:
    """
    Check if a TrueType font is available.

    Args:
        font_name: Name of the font (e.g., "Nunito", "Arial")
        size: Font size for testing (default 12)

    Returns:
        True if font can be loaded, False otherwise
    """
    if not PIL_AVAILABLE or not ImageFont:
        return False

    # Common font paths to check
    font_paths = [
        f"/usr/share/fonts/truetype/{font_name.lower()}/{font_name}-Regular.ttf",
        f"/usr/share/fonts/truetype/{font_name.lower()}/{font_name}.ttf",
        f"/System/Library/Fonts/{font_name}.ttf",  # macOS
        f"/Library/Fonts/{font_name}.ttf",  # macOS
        f"C:\\Windows\\Fonts\\{font_name}.ttf",  # Windows
    ]

    for path in font_paths:
        try:
            ImageFont.truetype(path, size)
            return True
        except (OSError, IOError):
            continue

    return False


def _get_font_path(font_name: str, repo_root: Optional[Path] = None) -> Optional[str]:
    """
    Get the path to a TrueType font, checking multiple locations.

    Search order:
    1. Bundled fonts in repo's fonts/ directory
    2. System fonts in standard locations
    3. None (will use PIL default font)

    Args:
        font_name: Name of the font (e.g., "Nunito", "Arial")
        repo_root: Path to repository root (defaults to 2 levels up from this file)

    Returns:
        Path to font file, or None if not found
    """
    if not PIL_AVAILABLE:
        return None

    if repo_root is None:
        repo_root = Path(__file__).resolve().parents[2]

    # Check bundled fonts first
    bundled_paths = [
        repo_root / "fonts" / f"{font_name.lower()}-regular.ttf",
        repo_root / "fonts" / f"{font_name.lower()}.ttf",
        repo_root / "fonts" / f"{font_name}.ttf",
    ]

    for path in bundled_paths:
        if path.is_file():
            return str(path)

    # Check system fonts
    system_paths = [
        f"/usr/share/fonts/truetype/{font_name.lower()}/{font_name}-Regular.ttf",
        f"/usr/share/fonts/truetype/{font_name.lower()}/{font_name}.ttf",
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Common fallback
        f"/System/Library/Fonts/{font_name}.ttf",  # macOS
        f"/Library/Fonts/{font_name}.ttf",  # macOS
        f"C:\\Windows\\Fonts\\{font_name}.ttf",  # Windows
    ]

    for path in system_paths:
        if os.path.exists(path):
            return path

    return None


@dataclass
class Theme:
    name: str
    description: str
    palette: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    layout: Dict[str, Any] = field(default_factory=dict)
    base_font: str = "Nunito"
    mono_font: str = "ShareTechMono"

    def accent_cycle(self) -> List[Color]:
        """
        Return list of RGB accents for cycling UI bars.

        Uses layout.accent_cycle if defined (supports references like "bg", "accents[0]"),
        otherwise falls back to palette.accents.

        Returns:
            List of RGB tuples
        """
        # Try layout.accent_cycle first (with reference parsing)
        cycle_refs = self.layout.get("accent_cycle")
        if cycle_refs and isinstance(cycle_refs, list):
            resolved = []
            for ref in cycle_refs:
                color = _resolve_reference(ref, self.palette, (255, 255, 255))
                if isinstance(color, tuple) and len(color) == 3:
                    resolved.append(color)
            if resolved:  # Only use if we successfully resolved at least one
                return resolved

        # Fallback to palette.accents (direct hex values)
        accents = self.palette.get("accents") or []
        rgb = [_hex_to_rgb(val, (255, 255, 255)) for val in accents]
        return [c for c in rgb if isinstance(c, tuple) and len(c) == 3]

    def color(self, key: str, fallback: Color) -> Color:
        """Get a palette color by key, converting hex to RGB."""
        return _hex_to_rgb(self.palette.get(key, ""), fallback)

    @property
    def radius_lg_px(self) -> int:
        """Large border radius in pixels (clamped 0-100)."""
        return _clamp(self.metrics.get("radius_lg", 24), 0, 100)

    @property
    def radius_md_px(self) -> int:
        """Medium border radius in pixels (clamped 0-50)."""
        return _clamp(self.metrics.get("radius_md", 12), 0, 50)

    @property
    def radius_sm_px(self) -> int:
        """Small border radius in pixels (clamped 0-25)."""
        return _clamp(self.metrics.get("radius_sm", 8), 0, 25)

    @property
    def stroke_px(self) -> int:
        """Stroke/border width in pixels (clamped 0-10)."""
        return _clamp(self.metrics.get("stroke", 2), 0, 10)

    @property
    def padding_px(self) -> int:
        """Default padding in pixels (clamped 0-50)."""
        return _clamp(self.metrics.get("padding", 12), 0, 50)

    @property
    def gap_px(self) -> int:
        """Gap between elements in pixels (clamped 0-50)."""
        return _clamp(self.metrics.get("gap", 8), 0, 50)

    @property
    def touch_min_px(self) -> int:
        """Minimum touch target size in pixels (clamped 20-100)."""
        return _clamp(self.metrics.get("touch_min", 44), 20, 100)

    def font_path(self, font_type: str = "base") -> Optional[str]:
        """
        Get the path to a theme font with fallback.

        Args:
            font_type: "base" for base_font or "mono" for mono_font

        Returns:
            Path to font file, or None to use PIL default font
        """
        font_name = self.base_font if font_type == "base" else self.mono_font
        path = _get_font_path(font_name)

        if not path:
            logger.warning(
                "Font '%s' not found; application should use PIL default font",
                font_name
            )

        return path

    def layout_color(self, key: str, fallback: Color = (255, 255, 255)) -> Color:
        """
        Get a layout color by key, converting hex to RGB.

        Args:
            key: Layout key (e.g., "header_color", "button_primary")
            fallback: RGB tuple to use if key not found or invalid

        Returns:
            RGB tuple
        """
        return _hex_to_rgb(self.layout.get(key, ""), fallback)

    def layout_int(self, key: str, fallback: int = 0) -> int:
        """
        Get a layout integer value by key.

        Args:
            key: Layout key (e.g., "progress_height", "volume_width")
            fallback: Value to use if key not found or invalid

        Returns:
            Integer value
        """
        try:
            return int(self.layout.get(key, fallback))
        except (ValueError, TypeError):
            return fallback

    def layout_str(self, key: str, fallback: str = "") -> str:
        """
        Get a layout string value by key.

        Args:
            key: Layout key
            fallback: Value to use if key not found

        Returns:
            String value
        """
        value = self.layout.get(key, fallback)
        return str(value) if value is not None else fallback


DEFAULT_THEME_SPEC: Dict[str, Any] = {
    "name": "LCARS Default",
    "description": "LCARS bands with retro player cues",
    "base_font": "Nunito",
    "mono_font": "ShareTechMono",
    "palette": {
        "bg": "#0c0c10",
        "panel": "#f5e9d7",
        "text": "#f0f0f5",
        "text_dim": "#5a606e",
        "accents": ["#f2b84b", "#f47e6a", "#7e5ba6", "#3ab6c5", "#7fa3d9"],
        "status_good": "#3ab6c5",
        "status_warn": "#f2b84b",
        "status_bad": "#f47e6a"
    },
    "metrics": {
        "radius_lg": 24,
        "radius_sm": 8,
        "stroke": 2,
        "padding": 12,
        "gap": 8,
        "touch_min": 44
    },
    "layout": {
        "header_color": "#7fa3d9",
        "rail_color": "#7e5ba6",
        "button_primary": "#f2b84b",
        "button_secondary": "#f5e9d7",
        "progress_height": 10,
        "volume_width": 22,
        "accent_cycle": ["bg", "panel", "accents[0]", "accents[1]"]
    }
}


def default_theme() -> Theme:
    """Return the baked-in fallback theme."""
    return Theme(**DEFAULT_THEME_SPEC)


def _resolve_theme_path(theme_name: str, themes_dir: Path) -> Optional[Path]:
    """
    Resolve a theme name or path:
    - Absolute file path if it exists.
    - themes_dir/<name>.json if name has no extension.
    - themes_dir/<name> if name already ends with .json
    """
    candidate = Path(theme_name)
    if candidate.is_file():
        return candidate

    themes_dir.mkdir(parents=True, exist_ok=True)
    if candidate.suffix.lower() == ".json":
        possible = themes_dir / candidate.name
    else:
        possible = themes_dir / f"{theme_name}.json"
    return possible if possible.is_file() else None


# Module-level cache for loaded themes
_theme_cache: Dict[str, Theme] = {}


def load_theme(
    theme_name: Optional[str] = None,
    themes_dir: Optional[Path] = None,
    use_cache: bool = True
) -> Theme:
    """
    Load a theme by name (or DFPLAYER_THEME env). Returns default on error.

    Args:
        theme_name: Name (without .json), or absolute path to a JSON theme.
        themes_dir: Directory containing theme JSON files. Defaults to repo /themes.
        use_cache: If True, return cached theme if available (default: True)

    Returns:
        Theme object with all settings
    """
    name = theme_name or os.environ.get("DFPLAYER_THEME") or "lcars_default"
    base_dir = themes_dir or Path(__file__).resolve().parents[2] / "themes"

    # Check cache first
    cache_key = f"{name}:{base_dir}"
    if use_cache and cache_key in _theme_cache:
        logger.debug("Returning cached theme '%s'", name)
        return _theme_cache[cache_key]

    path = _resolve_theme_path(name, base_dir)

    if not path:
        logger.warning("Theme '%s' not found; falling back to default", name)
        return default_theme()

    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception as exc:
        logger.warning("Failed to read theme '%s': %s; using default", name, exc)
        return default_theme()

    merged = {
        "name": payload.get("name", name),
        "description": payload.get("description", ""),
        "base_font": payload.get("base_font", DEFAULT_THEME_SPEC["base_font"]),
        "mono_font": payload.get("mono_font", DEFAULT_THEME_SPEC["mono_font"]),
        "palette": _merge(DEFAULT_THEME_SPEC["palette"], payload.get("palette"), "palette"),
        "metrics": _merge(DEFAULT_THEME_SPEC["metrics"], payload.get("metrics"), "metrics"),
        "layout": _merge(DEFAULT_THEME_SPEC["layout"], payload.get("layout"), "layout"),
    }

    theme = Theme(**merged)

    # Cache the loaded theme
    if use_cache:
        _theme_cache[cache_key] = theme
        logger.debug("Cached theme '%s'", name)

    return theme
