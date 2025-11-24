from dataclasses import dataclass
from typing import Tuple
from ui.theme import load_theme, default_theme


Color = Tuple[int, int, int]


@dataclass
class Palette:
    bg: Color
    panel: Color
    text: Color
    text_dim: Color
    accent: Color
    accent_alt: Color
    danger: Color
    warn: Color


def get_palette():
    theme = load_theme(None) if load_theme else default_theme()
    def _c(val, fallback):
        try:
            from ui.theme import _hex_to_rgb
            return _hex_to_rgb(val, fallback)
        except Exception:
            return fallback
    accents = theme.accent_cycle() if theme else []
    return Palette(
        bg=_c(theme.palette.get("bg"), (12, 16, 24)) if theme else (12, 16, 24),
        panel=_c(theme.palette.get("panel"), (26, 28, 36)) if theme else (26, 28, 36),
        text=_c(theme.palette.get("text"), (235, 235, 235)) if theme else (235, 235, 235),
        text_dim=_c(theme.palette.get("text_dim"), (195, 195, 200)) if theme else (195, 195, 200),
        accent=accents[0] if accents else (242, 184, 75),
        accent_alt=accents[1] if len(accents) > 1 else (126, 91, 166),
        danger=_c(theme.palette.get("status_bad"), (195, 80, 80)) if theme else (195, 80, 80),
        warn=_c(theme.palette.get("status_warn"), (215, 165, 60)) if theme else (215, 165, 60),
    )
