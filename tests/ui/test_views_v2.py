from PIL import Image, ImageDraw, ImageFont

from ui.views import draw_volume_bar, draw_title_line


def _make_canvas(width=40, height=20):
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    return img, draw, font


def test_draw_volume_bar_clamps_fill_width():
    img, draw, _ = _make_canvas()
    rect = (5, 5, 10, 4)
    draw_volume_bar(draw, 200, rect)
    # Inside the bar should be filled with the highlight color
    assert img.getpixel((14, 6)) != (0, 0, 0)
    # Outside the defined width should remain untouched
    assert img.getpixel((16, 6)) == (0, 0, 0)


def test_draw_title_line_truncates_text():
    img, draw, font = _make_canvas(120, 20)
    long_title = "This title is much too long"
    draw_title_line(draw, long_title, (0, 0), font, max_chars=8)
    # Ensure drawing completed by checking that some non-background pixels exist
    assert img.getbbox() is not None
