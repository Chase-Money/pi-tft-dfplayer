from src.core.profile_select_v2 import select_hardware


def test_select_hardware_defaults_to_touch():
    disp, inp = select_hardware("")
    assert disp.endswith("hardware.framebuffer.Framebuffer")
    assert inp.endswith("hardware.touch.TouchInput")


def test_select_hardware_buttons_profile():
    disp, inp = select_hardware("st7735_buttons")
    assert disp.endswith("hardware.display_st7735.DisplayST7735")
    assert inp.endswith("hardware.button_input.ButtonInput")

