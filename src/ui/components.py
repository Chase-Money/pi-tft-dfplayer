"""
UI components for the DFPlayer GUI, such as buttons and sliders.
"""

from PIL import ImageDraw, ImageFont

class Button:
    def __init__(self, rect, label, action, fill_color=(80, 110, 185), text_color=(255, 255, 255), radius=16):
        self.rect = rect
        self.label = label
        self.action = action
        self.fill_color = fill_color
        self.text_color = text_color
        self.radius = radius

    def get_label(self, state):
        if callable(self.label):
            return self.label(state)
        return self.label

    def is_inside(self, x, y):
        """Check if a point is inside the button's rectangle."""
        bx, by, bw, bh = self.rect
        return bx <= x <= bx + bw and by <= y <= by + bh

    def draw(self, draw_context, font, state):
        """Draw the button on the screen."""
        x, y, w, h = self.rect
        label = self.get_label(state)
        draw_context.rounded_rectangle((x, y, x + w, y + h), radius=self.radius, fill=self.fill_color)
        
        # Draw text centered
        text_bbox = draw_context.textbbox((0, 0), label, font=font)
        tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        draw_context.text((x + (w - tw) // 2, y + (h - th) // 2), label, font=font, fill=self.text_color)

class VolumeSlider:
    def __init__(self, rect, vol_rect):
        self.rect = rect
        self.vol_rect = vol_rect

    def draw(self, draw_context, volume, font):
        """Draw the volume slider."""
        # Volume bar
        vx, vy, vw, vh = self.vol_rect
        draw_context.text((vx, vy - 28), "Volume", font=font, fill=(215, 215, 215))
        draw_context.rounded_rectangle((vx, vy, vx + vw, vy + vh), radius=10, fill=(55, 60, 75))
        fill_width = int(vw * volume / 30)
        draw_context.rounded_rectangle((vx, vy, vx + fill_width, vy + vh), radius=10, fill=(230, 195, 80))
        draw_context.text((vx + vw + 8, vy - 4), f"{volume:02d}", font=font, fill=(235, 235, 235))

    def is_inside(self, x, y):
        """Check if a point is inside the slider's rectangle."""
        sx, sy, sw, sh = self.rect
        return sx <= x <= sx + sw and sy <= y <= sy + sh

    def get_volume_from_x(self, x):
        """Calculate the volume based on the x-coordinate of a touch."""
        sx, _, sw, _ = self.rect
        clamped_x = max(sx, min(sx + sw, x))
        new_volume = int(round((clamped_x - sx) * 30 / sw))
        return max(0, min(30, new_volume))
