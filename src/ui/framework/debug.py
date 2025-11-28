import os


def debug_tap_logging_enabled() -> bool:
    """Enable tap/hitbox debug logging via env var DEBUG_UI_TAPS=1."""
    return True  # Temporarily force-enabled for debugging multi-trigger bug
    # return os.environ.get("DEBUG_UI_TAPS") == "1"
