from src.ui.draw_utils import xywh_to_xyxy, inside, clamp, iter_lines_by_width


def test_xywh_to_xyxy_and_inside():
    rect = (10, 20, 30, 40)
    x0, y0, x1, y1 = xywh_to_xyxy(rect)
    assert (x0, y0, x1, y1) == (10, 20, 40, 60)
    assert inside(rect, 10, 20)
    assert inside(rect, 40, 60)
    assert not inside(rect, 9, 20)
    assert not inside(rect, 41, 60)


def test_clamp():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10


def test_iter_lines_by_width_greedy():
    words = "This is a long title string".split()

    # Fake measure: 1 char = 6px incl. space
    def measure(s: str) -> int:
        return len(s) * 6

    lines = list(iter_lines_by_width(words, max_width=18, measure=measure))
    # Max 3 chars per line (18/6), space counted → no two-word lines fit here
    assert lines == [
        "This",
        "is",
        "a",
        "long",
        "title",
        "string",
    ]
