from PIL import Image, ImageDraw, ImageFont

from src.ui.framework_v2.widgets import ButtonWidget, ListWidget, SliderWidget
from src.ui.framework_v2.events import UIEvent


def make_draw():
    img = Image.new("RGB", (200, 200), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    return img, draw, font


def test_button_widget_callback():
    called = []

    def on_press():
        called.append(True)

    button = ButtonWidget((10, 10, 50, 30), "Go", on_press)
    event = UIEvent("tap", {"pos": (20, 20)})
    assert button.handle_event(event)
    assert called


def test_list_widget_selection():
    items = ["one", "two", "three", "four"]
    widget = ListWidget(items, visible_rows=2)
    widget.move_selection(2)
    assert widget.selected_index == 2
    assert widget.scroll == 1  # scrolled to keep selection visible


def test_slider_widget_value_from_x():
    slider = SliderWidget((0, 0, 100, 10))
    event = UIEvent("drag", {"pos": (75, 5)})
    assert slider.handle_event(event)
    assert slider.value >= 20


def test_list_widget_scroll_pixels_clamps_bounds():
    widget = ListWidget(["one", "two", "three", "four"], visible_rows=2)
    widget.row_height = 20
    assert widget.scroll_pixels(40)  # scroll down
    assert widget.scroll == 2
    assert not widget.scroll_pixels(0)  # no delta
    assert widget.scroll_pixels(-40)  # scroll up
    assert widget.scroll == 0
