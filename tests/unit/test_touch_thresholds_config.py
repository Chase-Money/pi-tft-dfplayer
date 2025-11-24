"""
Tests for configurable touch gesture thresholds.

This test suite verifies that touch gesture thresholds (tap, drag, swipe)
can be configured via the config system rather than being hardcoded.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.core.config import Config, get_config


class TestTouchThresholdsConfig:
    """Tests for touch threshold configuration."""

    def test_default_touch_thresholds_exist(self):
        """Config should provide default touch threshold values."""
        config = Config()

        thresholds = config.get("touch_thresholds", {})

        # Verify defaults exist
        assert "tap_threshold_ms" in thresholds, "Should have tap_threshold_ms"
        assert "drag_threshold_px" in thresholds, "Should have drag_threshold_px"
        assert "swipe_threshold_px" in thresholds, "Should have swipe_threshold_px"

        # Verify default values are reasonable
        assert thresholds["tap_threshold_ms"] > 0, "Tap threshold should be positive"
        assert thresholds["drag_threshold_px"] > 0, "Drag threshold should be positive"
        assert thresholds["swipe_threshold_px"] > 0, "Swipe threshold should be positive"

    def test_get_touch_thresholds_helper_method(self):
        """Config should have a helper method to get touch thresholds."""
        config = Config()

        thresholds = config.get_touch_thresholds()

        assert isinstance(thresholds, dict), "Should return a dictionary"
        assert "tap_threshold_ms" in thresholds
        assert "drag_threshold_px" in thresholds
        assert "swipe_threshold_px" in thresholds

    def test_set_touch_thresholds_helper_method(self):
        """Config should have a helper method to set touch thresholds."""
        config = Config()

        # Set custom thresholds
        config.set_touch_thresholds(
            tap_threshold_ms=500,
            drag_threshold_px=15,
            swipe_threshold_px=60
        )

        thresholds = config.get_touch_thresholds()

        assert thresholds["tap_threshold_ms"] == 500
        assert thresholds["drag_threshold_px"] == 15
        assert thresholds["swipe_threshold_px"] == 60

    def test_touch_controller_uses_config_thresholds(self):
        """TouchController should use thresholds from config, not hardcoded values."""
        with patch('src.hardware.touch_controller.TouchInput'):
            mock_config = Mock()
            mock_config.get_touch_thresholds.return_value = {
                "tap_threshold_ms": 600,
                "drag_threshold_px": 20,
                "swipe_threshold_px": 80
            }

            from src.hardware.touch_controller import TouchController

            # Create controller - it should read from config
            controller = TouchController(config=mock_config)

            # Verify it used config values, not hardcoded ones
            assert controller.tap_threshold_ms == 600
            assert controller.drag_threshold_px == 20
            assert controller.swipe_threshold_px == 80

    def test_touch_controller_falls_back_to_defaults_if_no_config(self):
        """TouchController should use reasonable defaults if no config provided."""
        with patch('src.hardware.touch_controller.TouchInput'):
            from src.hardware.touch_controller import TouchController

            # Create controller without config
            controller = TouchController(config=None)

            # Should have reasonable defaults
            assert controller.tap_threshold_ms > 0
            assert controller.drag_threshold_px > 0
            assert controller.swipe_threshold_px > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
