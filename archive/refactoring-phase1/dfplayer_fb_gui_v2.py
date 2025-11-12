"""
Main application entry point for the v2 refactored DFPlayer GUI.
"""

import sys
import time
import logging
import statistics

from core.app_state import AppState
from core.config import get_config, ORIENTS
from evdev import ecodes
from hardware.dfplayer import DFPlayer
from hardware.framebuffer import Framebuffer
from hardware.touch import TouchController
from ui.screen import Screen
from ui.components import Button, VolumeSlider

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from core.track_manager import TrackManager

from core.metadata_manager import MetadataManager

class App:
    def __init__(self):
        self.config = get_config()
        self.state = AppState()
        self.state.load_from_config(self.config)
        self.track_manager = TrackManager(self.config)
        self.state.set_track_manager(self.track_manager)
        self.metadata_manager = MetadataManager(self.config)
        self.touch_event = None

        try:
            self.framebuffer = Framebuffer()
            self.touch_controller = TouchController()
            self.dfplayer = DFPlayer()
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            sys.exit(1)

        self.screen = Screen(self.framebuffer.width, self.framebuffer.height, self.framebuffer)
        self.setup_ui_components()

    def setup_ui_components(self):
        """Initialize UI components."""
        TRACK_PANEL = (240, 50, max(180, self.screen.width - 260), max(130, self.screen.height - 70))
        TRACK_HEADER_HEIGHT = 44
        TRACK_ROW_HEIGHT = 32
        TRACK_SCROLL_BTN_W = 40
        
        tx, ty, tw, th = TRACK_PANEL
        list_x = tx + 10
        list_y = ty + TRACK_HEADER_HEIGHT
        list_w = max(40, tw - TRACK_SCROLL_BTN_W - 24)
        list_h = max(24, th - TRACK_HEADER_HEIGHT - 16)
        
        scroll_x = list_x + list_w + 8
        up_rect = (scroll_x, list_y, TRACK_SCROLL_BTN_W, 36)
        down_rect = (scroll_x, list_y + list_h - 36, TRACK_SCROLL_BTN_W, 36)

        self.components = {
            "play": Button((20, 24, 200, 86), lambda state: "Pause" if state.is_playing else "Play", self.handle_play_button, fill_color=(70, 175, 120)),
            "stop": Button((20, 124, 200, 72), "Stop", self.handle_stop_button, fill_color=(195, 80, 80)),
            "prev": Button((20, 212, 94, 72), "Prev", self.handle_prev_button),
            "next": Button((126, 212, 94, 72), "Next", self.handle_next_button),
            "volume": VolumeSlider((20, 292, 200, 20), (20, 292, 200, 20)),
            "scroll_up": Button(up_rect, "Up", self.handle_scroll_up),
            "scroll_down": Button(down_rect, "Down", self.handle_scroll_down),
            "track_list": Button((list_x, list_y, list_w, list_h), "", self.handle_track_select),
            "cal": Button((4, 4, 52, 30), "CAL", self.handle_cal_button, fill_color=(90, 90, 140)),
            "cfg": Button((self.screen.width - 56, 4, 52, 30), "CFG", self.handle_cfg_button, fill_color=(90, 140, 90)),
        }

    def handle_scroll_up(self):
        if self.state.track_scroll_position > 0:
            self.state.track_scroll_position -= 1

    def handle_scroll_down(self):
        if self.state.track_scroll_position < len(self.state.tracks) - 1:
            self.state.track_scroll_position += 1

    def handle_track_select(self, x, y):
        TRACK_PANEL = (240, 50, max(180, self.screen.width - 260), max(130, self.screen.height - 70))
        TRACK_HEADER_HEIGHT = 44
        TRACK_ROW_HEIGHT = 32
        
        tx, ty, tw, th = TRACK_PANEL
        list_x = tx + 10
        list_y = ty + TRACK_HEADER_HEIGHT
        
        row = (y - list_y) // TRACK_ROW_HEIGHT
        track_index = self.state.track_scroll_position + row
        
        if 0 <= track_index < len(self.state.tracks):
            self.state.selected_track_index = track_index
            self.dfplayer.play_track(self.state.tracks[track_index]["number"])
            self.state.is_playing = True
            self.state.now_playing_index = track_index

    def handle_cal_button(self):
        """Handle the calibration button press."""
        logger.info("Starting calibration...")
        
        points = [(20, 20), (self.screen.width - 20, 20), (self.screen.width - 20, self.screen.height - 20), (20, self.screen.height - 20)]
        raw_points = []

        for x, y in points:
            self.screen.draw_calibration_target(x, y)
            raw_point = self.touch_controller.wait_for_touch()
            if raw_point is None:
                logger.info("Calibration timed out.")
                return
            raw_points.append(raw_point)

        # Invert orientation to driver axes to compute true min/max
        orientation = ORIENTS[self.state.orientation_index]
        
        def invert_raw(rx, ry):
            x, y = rx, ry
            if orientation["FLIP_Y"]:
                y = (self.touch_controller.min_y + self.touch_controller.max_y) - y
            if orientation["FLIP_X"]:
                x = (self.touch_controller.min_x + self.touch_controller.max_x) - x
            if orientation["SWAP_XY"]:
                x, y = y, x
            return x, y

        inverted_points = [invert_raw(rx, ry) for rx, ry in raw_points]
        
        left_x = int(statistics.median([inverted_points[0][0], inverted_points[3][0]]))
        right_x = int(statistics.median([inverted_points[1][0], inverted_points[2][0]]))
        top_y = int(statistics.median([inverted_points[0][1], inverted_points[1][1]]))
        bottom_y = int(statistics.median([inverted_points[2][1], inverted_points[3][1]]))

        if right_x <= left_x: right_x = left_x + 1
        if bottom_y <= top_y: bottom_y = top_y + 1

        self.state.calibration = (left_x, right_x, top_y, bottom_y)
        self.config.set_touch_calibration(left_x, right_x, top_y, bottom_y)
        self.config.save()
        
        logger.info("Calibration complete.")
        self.screen.render(self.state, self.components, self.metadata_manager)


    def handle_cfg_button(self):
        logger.info("Configuration button pressed")
        self.state.orientation_index = (self.state.orientation_index + 1) % len(ORIENTS)
        # Save orientation to config
        self.config.set_touch_orientation(self.state.orientation_index)
        self.config.save()


    def handle_play_button(self):
        logger.info("Play button pressed")
        if self.state.is_playing:
            self.dfplayer.pause()
            self.state.is_playing = False
        else:
            self.dfplayer.play()
            self.state.is_playing = True

    def handle_stop_button(self):
        logger.info("Stop button pressed")
        self.dfplayer.stop()
        self.state.is_playing = False

    def handle_prev_button(self):
        logger.info("Prev button pressed")
        self.dfplayer.prev_track()

    def handle_next_button(self):
        logger.info("Next button pressed")
        self.dfplayer.next_track()

    def run(self):
        """Main application loop."""
        self.screen.render(self.state, self.components, self.metadata_manager) # Initial render

        for event in self.touch_controller.device.read_loop():
            try:
                if event.type == ecodes.EV_KEY and event.code == ecodes.BTN_TOUCH and event.value == 0:
                    # Touch released
                    if self.touch_event:
                        px, py = self.touch_controller.scale_xy(
                            self.touch_event['x'], 
                            self.touch_event['y'], 
                            self.screen.width, 
                            self.screen.height, 
                            ORIENTS[self.state.orientation_index], 
                            self.state.calibration
                        )

                        for name, component in self.components.items():
                            if isinstance(component, Button) and component.is_inside(px, py):
                                if name == "track_list":
                                    component.action(px, py)
                                else:
                                    component.action()
                                break
                        
                        self.screen.render(self.state, self.components, self.metadata_manager)
                    self.touch_event = None

                elif event.type == ecodes.EV_ABS:
                    # Touch pressed or dragged
                    if not self.touch_event:
                        self.touch_event = {'x': 0, 'y': 0}
                    
                    if event.code == ecodes.ABS_X:
                        self.touch_event['x'] = event.value
                    elif event.code == ecodes.ABS_Y:
                        self.touch_event['y'] = event.value

                    px, py = self.touch_controller.scale_xy(
                        self.touch_event['x'], 
                        self.touch_event['y'], 
                        self.screen.width, 
                        self.screen.height, 
                        ORIENTS[self.state.orientation_index], 
                        self.state.calibration
                    )

                    volume_slider = self.components.get("volume")
                    if isinstance(volume_slider, VolumeSlider) and volume_slider.is_inside(px, py):
                        new_volume = volume_slider.get_volume_from_x(px)
                        if new_volume != self.state.volume:
                            self.state.volume = new_volume
                            self.dfplayer.set_volume(new_volume)
                            self.screen.render(self.state, self.components, self.metadata_manager)

            except KeyboardInterrupt:
                logger.info("Exiting...")
                break
            except Exception as e:
                logger.error(f"An error occurred in the main loop: {e}")
                break

        self.cleanup()

    def __init__(self):
        self.config = get_config()
        self.state = AppState()
        self.state.load_from_config(self.config)
        self.touch_event = None

        try:
            self.framebuffer = Framebuffer()
            self.touch_controller = TouchController()
            self.dfplayer = DFPlayer()
        except Exception as e:
            logger.error(f"Failed to initialize hardware: {e}")
            sys.exit(1)

        self.screen = Screen(self.framebuffer.width, self.framebuffer.height, self.framebuffer)
        self.setup_ui_components()

    def cleanup(self):
        """Clean up resources."""
        self.dfplayer.close()
        self.framebuffer.close()

if __name__ == "__main__":
    app = App()
    app.run()
