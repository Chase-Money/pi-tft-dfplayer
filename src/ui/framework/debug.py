import os


def debug_tap_logging_enabled() -> bool:
    """Enable tap/hitbox debug logging via env var DEBUG_UI_TAPS=1."""
    return os.environ.get("DEBUG_UI_TAPS") == "1"
