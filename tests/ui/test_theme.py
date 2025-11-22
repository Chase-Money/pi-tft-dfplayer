"""
Unit tests for the theme module.

Tests theme loading, validation, caching, and helper methods.
"""

import json
import logging
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from src.ui.theme import (
    Theme,
    load_theme,
    default_theme,
    _hex_to_rgb,
    _clamp,
    _resolve_reference,
    _merge,
    _theme_cache,
)


class TestHexToRgb:
    """Test hex color parsing."""

    def test_valid_hex(self):
        """Test valid hex color conversion."""
        assert _hex_to_rgb("#ff0000", (0, 0, 0)) == (255, 0, 0)
        assert _hex_to_rgb("#00ff00", (0, 0, 0)) == (0, 255, 0)
        assert _hex_to_rgb("#0000ff", (0, 0, 0)) == (0, 0, 255)

    def test_valid_hex_no_hash(self):
        """Test hex without # prefix."""
        assert _hex_to_rgb("ff0000", (0, 0, 0)) == (255, 0, 0)

    def test_uppercase_hex(self):
        """Test uppercase hex values."""
        assert _hex_to_rgb("#FF0000", (0, 0, 0)) == (255, 0, 0)

    def test_mixed_case_hex(self):
        """Test mixed case hex values."""
        assert _hex_to_rgb("#FfAa00", (0, 0, 0)) == (255, 170, 0)

    def test_invalid_hex_returns_default(self):
        """Test invalid hex returns fallback."""
        fallback = (100, 100, 100)
        assert _hex_to_rgb("#gggggg", fallback) == fallback
        assert _hex_to_rgb("#ff", fallback) == fallback  # Too short
        assert _hex_to_rgb("#ff00000", fallback) == fallback  # Too long
        assert _hex_to_rgb("", fallback) == fallback
        assert _hex_to_rgb("not a color", fallback) == fallback

    def test_non_string_returns_default(self):
        """Test non-string input returns fallback."""
        fallback = (100, 100, 100)
        assert _hex_to_rgb(123, fallback) == fallback  # type: ignore
        assert _hex_to_rgb(None, fallback) == fallback  # type: ignore
        assert _hex_to_rgb([], fallback) == fallback  # type: ignore


class TestClamp:
    """Test numeric clamping."""

    def test_clamp_within_range(self):
        """Test values within range are unchanged."""
        assert _clamp(5, 0, 10) == 5
        assert _clamp(0, 0, 10) == 0
        assert _clamp(10, 0, 10) == 10

    def test_clamp_below_minimum(self):
        """Test values below minimum are clamped."""
        assert _clamp(-5, 0, 10) == 0
        assert _clamp(-100, 0, 10) == 0

    def test_clamp_above_maximum(self):
        """Test values above maximum are clamped."""
        assert _clamp(15, 0, 10) == 10
        assert _clamp(100, 0, 10) == 10

    def test_clamp_float_to_int(self):
        """Test float values are converted to int."""
        assert _clamp(5.7, 0, 10) == 5
        assert _clamp(9.9, 0, 10) == 9


class TestResolveReference:
    """Test palette reference resolution."""

    def test_simple_reference(self):
        """Test simple key reference."""
        palette = {"bg": "#ff0000", "panel": "#00ff00"}
        assert _resolve_reference("bg", palette, (0, 0, 0)) == (255, 0, 0)
        assert _resolve_reference("panel", palette, (0, 0, 0)) == (0, 255, 0)

    def test_array_reference(self):
        """Test array indexing reference."""
        palette = {"accents": ["#ff0000", "#00ff00", "#0000ff"]}
        assert _resolve_reference("accents[0]", palette, (0, 0, 0)) == (255, 0, 0)
        assert _resolve_reference("accents[1]", palette, (0, 0, 0)) == (0, 255, 0)
        assert _resolve_reference("accents[2]", palette, (0, 0, 0)) == (0, 0, 255)

    def test_array_reference_out_of_bounds(self):
        """Test array reference with invalid index returns fallback."""
        palette = {"accents": ["#ff0000"]}
        fallback = (100, 100, 100)
        assert _resolve_reference("accents[5]", palette, fallback) == fallback
        assert _resolve_reference("accents[-1]", palette, fallback) == fallback

    def test_invalid_reference(self):
        """Test invalid reference returns fallback."""
        palette = {"bg": "#ff0000"}
        fallback = (100, 100, 100)
        assert _resolve_reference("nonexistent", palette, fallback) == fallback
        assert _resolve_reference("", palette, fallback) == fallback

    def test_non_string_reference(self):
        """Test non-string reference returns fallback."""
        palette = {"bg": "#ff0000"}
        fallback = (100, 100, 100)
        assert _resolve_reference(123, palette, fallback) == fallback  # type: ignore
        assert _resolve_reference(None, palette, fallback) == fallback  # type: ignore


class TestMerge:
    """Test dictionary merging with validation."""

    def test_merge_preserves_defaults(self):
        """Test merge preserves default values when keys missing."""
        defaults = {"a": 1, "b": 2, "c": 3}
        incoming = {"b": 20}
        result = _merge(defaults, incoming, "test")
        assert result == {"a": 1, "b": 20, "c": 3}

    def test_merge_with_none_incoming(self):
        """Test merge with None incoming returns defaults."""
        defaults = {"a": 1, "b": 2}
        result = _merge(defaults, None, "test")
        assert result == defaults

    def test_merge_validates_numeric_types(self, caplog):
        """Test merge validates numeric types."""
        defaults = {"value": 10}
        incoming = {"value": "not a number"}

        with caplog.at_level(logging.WARNING):
            result = _merge(defaults, incoming, "test")

        assert result == {"value": 10}  # Keeps default
        assert "Type mismatch" in caplog.text

    def test_merge_accepts_int_and_float_interchangeably(self):
        """Test merge allows int/float interchangeably."""
        defaults = {"value": 10}
        result1 = _merge(defaults, {"value": 15.5}, "test")
        assert result1["value"] == 15.5

        defaults = {"value": 10.5}
        result2 = _merge(defaults, {"value": 15}, "test")
        assert result2["value"] == 15

    def test_merge_validates_list_types(self, caplog):
        """Test merge validates list types."""
        defaults = {"items": ["a", "b"]}
        incoming = {"items": "not a list"}

        with caplog.at_level(logging.WARNING):
            result = _merge(defaults, incoming, "test")

        assert result == {"items": ["a", "b"]}  # Keeps default
        assert "Type mismatch" in caplog.text

    def test_merge_validates_string_types(self, caplog):
        """Test merge validates string types."""
        defaults = {"name": "default"}
        incoming = {"name": 123}

        with caplog.at_level(logging.WARNING):
            result = _merge(defaults, incoming, "test")

        assert result == {"name": "default"}  # Keeps default
        assert "Type mismatch" in caplog.text

    def test_merge_without_validation(self):
        """Test merge without type validation."""
        defaults = {"value": 10}
        incoming = {"value": "string"}
        result = _merge(defaults, incoming, "test", validate_types=False)
        assert result["value"] == "string"  # Accepts invalid type


class TestDefaultTheme:
    """Test default theme creation."""

    def test_default_theme_loads(self):
        """Test default theme loads without errors."""
        theme = default_theme()
        assert isinstance(theme, Theme)
        assert theme.name == "LCARS Default"

    def test_default_theme_has_palette(self):
        """Test default theme has palette colors."""
        theme = default_theme()
        assert "bg" in theme.palette
        assert "panel" in theme.palette
        assert "accents" in theme.palette

    def test_default_theme_has_metrics(self):
        """Test default theme has metrics."""
        theme = default_theme()
        assert "radius_lg" in theme.metrics
        assert "stroke" in theme.metrics
        assert "touch_min" in theme.metrics

    def test_default_theme_has_layout(self):
        """Test default theme has layout settings."""
        theme = default_theme()
        assert "header_color" in theme.layout
        assert "accent_cycle" in theme.layout


class TestThemeClass:
    """Test Theme class methods."""

    def test_color_method(self):
        """Test color() method."""
        theme = default_theme()
        bg_color = theme.color("bg", (0, 0, 0))
        assert isinstance(bg_color, tuple)
        assert len(bg_color) == 3

    def test_color_method_with_invalid_key(self):
        """Test color() with invalid key returns fallback."""
        theme = default_theme()
        fallback = (100, 100, 100)
        result = theme.color("nonexistent", fallback)
        assert result == fallback

    def test_accent_cycle_from_layout(self):
        """Test accent_cycle uses layout.accent_cycle."""
        theme = default_theme()
        accents = theme.accent_cycle()
        assert isinstance(accents, list)
        assert len(accents) > 0
        assert all(isinstance(c, tuple) and len(c) == 3 for c in accents)

    def test_accent_cycle_fallback_to_palette(self):
        """Test accent_cycle falls back to palette.accents."""
        theme = default_theme()
        # Remove layout.accent_cycle
        theme.layout.pop("accent_cycle", None)
        accents = theme.accent_cycle()
        assert isinstance(accents, list)
        assert len(accents) > 0

    def test_metric_properties_with_clamping(self):
        """Test metric properties clamp values."""
        theme = default_theme()

        # Test extreme values get clamped
        theme.metrics["stroke"] = -10
        assert theme.stroke_px == 0  # Clamped to minimum

        theme.metrics["stroke"] = 1000
        assert theme.stroke_px == 10  # Clamped to maximum

        theme.metrics["radius_lg"] = 200
        assert theme.radius_lg_px == 100  # Clamped to maximum

        theme.metrics["touch_min"] = 10
        assert theme.touch_min_px == 20  # Clamped to minimum

    def test_all_metric_properties(self):
        """Test all metric property accessors."""
        theme = default_theme()
        assert isinstance(theme.radius_lg_px, int)
        assert isinstance(theme.radius_md_px, int)
        assert isinstance(theme.radius_sm_px, int)
        assert isinstance(theme.stroke_px, int)
        assert isinstance(theme.padding_px, int)
        assert isinstance(theme.gap_px, int)
        assert isinstance(theme.touch_min_px, int)

    def test_layout_color_method(self):
        """Test layout_color() method."""
        theme = default_theme()
        header_color = theme.layout_color("header_color", (0, 0, 0))
        assert isinstance(header_color, tuple)
        assert len(header_color) == 3

    def test_layout_int_method(self):
        """Test layout_int() method."""
        theme = default_theme()
        progress_height = theme.layout_int("progress_height", 0)
        assert isinstance(progress_height, int)
        assert progress_height > 0

    def test_layout_str_method(self):
        """Test layout_str() method."""
        theme = default_theme()
        # Add a string value to layout for testing
        theme.layout["test_string"] = "test_value"
        result = theme.layout_str("test_string", "fallback")
        assert result == "test_value"

    def test_font_path_method(self):
        """Test font_path() method."""
        theme = default_theme()
        # Font may or may not exist on system
        base_path = theme.font_path("base")
        mono_path = theme.font_path("mono")
        # Should return None or a string path
        assert base_path is None or isinstance(base_path, str)
        assert mono_path is None or isinstance(mono_path, str)


class TestLoadTheme:
    """Test theme loading functionality."""

    def test_load_default_theme(self):
        """Test loading default theme by name."""
        # Clear cache first
        _theme_cache.clear()

        with TemporaryDirectory() as tmpdir:
            themes_dir = Path(tmpdir)

            # Create lcars_default.json
            theme_file = themes_dir / "lcars_default.json"
            theme_data = {
                "name": "Test Theme",
                "description": "Test",
                "palette": {"bg": "#123456"},
            }
            theme_file.write_text(json.dumps(theme_data))

            theme = load_theme("lcars_default", themes_dir, use_cache=False)
            assert theme.name == "Test Theme"
            assert theme.palette["bg"] == "#123456"

    def test_load_theme_with_env_var(self):
        """Test loading theme from DFPLAYER_THEME env var."""
        _theme_cache.clear()

        with TemporaryDirectory() as tmpdir:
            themes_dir = Path(tmpdir)

            # Create custom theme
            theme_file = themes_dir / "custom.json"
            theme_data = {"name": "Custom Theme", "palette": {"bg": "#abcdef"}}
            theme_file.write_text(json.dumps(theme_data))

            with patch.dict("os.environ", {"DFPLAYER_THEME": "custom"}):
                theme = load_theme(themes_dir=themes_dir, use_cache=False)
                assert theme.name == "Custom Theme"

    def test_load_nonexistent_theme_returns_default(self):
        """Test loading nonexistent theme returns default."""
        _theme_cache.clear()

        with TemporaryDirectory() as tmpdir:
            themes_dir = Path(tmpdir)
            theme = load_theme("nonexistent", themes_dir, use_cache=False)
            assert theme.name == "LCARS Default"  # Falls back to default

    def test_load_malformed_json_returns_default(self, caplog):
        """Test loading malformed JSON returns default."""
        _theme_cache.clear()

        with TemporaryDirectory() as tmpdir:
            themes_dir = Path(tmpdir)

            # Create malformed JSON
            theme_file = themes_dir / "malformed.json"
            theme_file.write_text("{invalid json")

            with caplog.at_level(logging.WARNING):
                theme = load_theme("malformed", themes_dir, use_cache=False)

            assert theme.name == "LCARS Default"
            assert "Failed to read theme" in caplog.text

    def test_load_theme_caching(self):
        """Test theme caching works."""
        _theme_cache.clear()

        with TemporaryDirectory() as tmpdir:
            themes_dir = Path(tmpdir)

            theme_file = themes_dir / "cached.json"
            theme_data = {"name": "Cached Theme", "palette": {"bg": "#111111"}}
            theme_file.write_text(json.dumps(theme_data))

            # First load - should cache
            theme1 = load_theme("cached", themes_dir, use_cache=True)

            # Modify the file
            theme_data["name"] = "Modified Theme"
            theme_file.write_text(json.dumps(theme_data))

            # Second load - should return cached version
            theme2 = load_theme("cached", themes_dir, use_cache=True)

            assert theme1.name == theme2.name == "Cached Theme"

    def test_load_theme_without_cache(self):
        """Test loading theme with cache disabled."""
        _theme_cache.clear()

        with TemporaryDirectory() as tmpdir:
            themes_dir = Path(tmpdir)

            theme_file = themes_dir / "nocache.json"
            theme_data = {"name": "First", "palette": {"bg": "#111111"}}
            theme_file.write_text(json.dumps(theme_data))

            theme1 = load_theme("nocache", themes_dir, use_cache=False)

            # Modify the file
            theme_data["name"] = "Second"
            theme_file.write_text(json.dumps(theme_data))

            theme2 = load_theme("nocache", themes_dir, use_cache=False)

            # Should load fresh copy
            assert theme1.name == "First"
            assert theme2.name == "Second"

    def test_load_theme_merges_with_defaults(self):
        """Test partial theme merges with defaults."""
        _theme_cache.clear()

        with TemporaryDirectory() as tmpdir:
            themes_dir = Path(tmpdir)

            # Create theme with only palette override
            theme_file = themes_dir / "partial.json"
            theme_data = {
                "name": "Partial Theme",
                "palette": {"bg": "#000000"}
                # No metrics or layout
            }
            theme_file.write_text(json.dumps(theme_data))

            theme = load_theme("partial", themes_dir, use_cache=False)

            # Should have palette override
            assert theme.palette["bg"] == "#000000"

            # Should have default metrics and layout
            assert "radius_lg" in theme.metrics
            assert "header_color" in theme.layout


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
