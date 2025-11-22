import json
import os, sys, time, mmap, serial, statistics, atexit, logging
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from evdev import InputDevice, ecodes, list_devices
try:
    # The theme module lives under src/ui/theme.py; this import will succeed when run from repo root.
    from ui.theme import load_theme, default_theme, _hex_to_rgb
except Exception:  # fallback if module import fails
    load_theme = None
    default_theme = None
    _hex_to_rgb = None

# Set up logging
# Legacy framebuffer UI (monolithic). Prefer v2 stack via `src/main.py`.

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

FB = "/dev/fb1"

def get_fb_size(fb):
    try:
        node = "/sys/class/graphics/" + os.path.basename(fb) + "/virtual_size"
        w, h = map(int, open(node).read().strip().split(','))
        return w, h
    except Exception:
        return 480, 320

W, H = get_fb_size(FB)

METADATA_PATH = os.environ.get("DFPLAYER_METADATA", "/boot/dfplayer_metadata.json")
ART_ROOT = os.environ.get("DFPLAYER_ART_ROOT")
THEMES_DIR = Path(__file__).resolve().parents[1] / "themes"

# 8 orientation combos we can cycle through
ORIENTS = [
    dict(SWAP_XY=False, FLIP_X=False, FLIP_Y=False),
    dict(SWAP_XY=False, FLIP_X=True , FLIP_Y=False),
    dict(SWAP_XY=False, FLIP_X=False, FLIP_Y=True ),
    dict(SWAP_XY=False, FLIP_X=True , FLIP_Y=True ),
    dict(SWAP_XY=True , FLIP_X=False, FLIP_Y=False),
    dict(SWAP_XY=True , FLIP_X=True , FLIP_Y=False),
    dict(SWAP_XY=True , FLIP_X=False, FLIP_Y=True ),
    dict(SWAP_XY=True , FLIP_X=True , FLIP_Y=True ),
]
orient_idx = 6  # good first guess for your rotated panel
CAL_PATH = os.path.expanduser("~/.touch_cal.txt")
ORIENT_PATH = os.path.expanduser("~/.touch_orient.txt")
cal_raw = None  # (minx, maxx, miny, maxy)


def load_orientation():
    global orient_idx
    try:
        with open(ORIENT_PATH, "r", encoding="utf-8") as f:
            idx = int(f.read().strip())
    except Exception:
        return
    if 0 <= idx < len(ORIENTS):
        orient_idx = idx


def save_orientation():
    try:
        with open(ORIENT_PATH, "w", encoding="utf-8") as f:
            f.write(f"{orient_idx}\n")
    except Exception:
        pass

TOUCH_CFG_PATH = os.path.expanduser("~/.dfplayer_touch.json")


def _touch_cfg_dir(path):
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def save_touch_settings():
    """Persist orientation index and calibration values to disk."""
    data = {}
    if os.path.exists(TOUCH_CFG_PATH):
        try:
            with open(TOUCH_CFG_PATH, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict):
                data.update(existing)
        except Exception:
            data = {}
    data["orientation_index"] = int(orient_idx)
    if cal_raw and len(cal_raw) == 4:
        data["calibration"] = [int(v) for v in cal_raw]
    else:
        data.pop("calibration", None)
    try:
        _touch_cfg_dir(TOUCH_CFG_PATH)
        tmp_path = TOUCH_CFG_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp_path, TOUCH_CFG_PATH)
    except Exception:
        pass


load_orientation()
def load_touch_settings():
    """Load persisted orientation and calibration (with legacy support)."""
    global orient_idx, cal_raw
    try:
        with open(TOUCH_CFG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = None
    if isinstance(data, dict):
        idx = data.get("orientation_index")
        if isinstance(idx, int) and 0 <= idx < len(ORIENTS):
            orient_idx = idx
        cal = data.get("calibration")
        if isinstance(cal, (list, tuple)) and len(cal) == 4:
            try:
                cal_raw = tuple(int(v) for v in cal)
            except Exception:
                cal_raw = None
    if cal_raw is None and os.path.exists(CAL_PATH):
        try:
            with open(CAL_PATH, "r", encoding="utf-8") as f:
                vals = [int(v) for v in f.read().strip().split()]
            if len(vals) == 4:
                cal_raw = tuple(vals)
        except Exception:
            pass

load_touch_settings()

# ---- Track metadata & artwork ----
metadata = {}
current_track_number = None
current_art_thumb = None
current_art_path = None
artwork_cache = {}

ART_RECT = (260, 20, 200, 200)
INFO_RECT = (260, 230, 200, 72)

def metadata_dir():
    if os.path.isdir(METADATA_PATH):
        return METADATA_PATH
    return os.path.dirname(METADATA_PATH) or "."

def _validate_artwork_path(artwork_path, base_dir):
    """
    Validate artwork path to prevent directory traversal attacks.

    Args:
        artwork_path: Raw artwork path from metadata
        base_dir: Base directory for relative paths

    Returns:
        str: Validated absolute path, or None if path is unsafe
    """
    if not artwork_path:
        return None

    try:
        # If absolute path, allow it (but could add whitelist in production)
        if os.path.isabs(artwork_path):
            return os.path.abspath(artwork_path)

        # For relative paths, normalize to remove .. or . components
        normalized = os.path.normpath(artwork_path)

        # Reject if normalization introduces path traversal
        if normalized.startswith('..') or normalized.startswith('/'):
            print(f"WARNING: Path traversal detected in artwork path: {artwork_path}")
            return None

        # Join with base_dir and resolve to absolute path
        full_path = os.path.join(base_dir, normalized)
        resolved = os.path.abspath(full_path)

        # Ensure resolved path is within base_dir
        base_abs = os.path.abspath(base_dir)
        if not resolved.startswith(base_abs + os.sep) and resolved != base_abs:
            print(f"WARNING: Artwork path escapes base directory: {artwork_path} -> {resolved}")
            return None

        return resolved

    except Exception as e:
        print(f"ERROR: Failed to validate artwork path {artwork_path}: {e}")
        return None

def load_metadata():
    global metadata
    base_dir = metadata_dir()
    try:
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        tracks = loaded.get("tracks") if isinstance(loaded, dict) else None
        if tracks is None:
            tracks = loaded if isinstance(loaded, dict) else {}
    except Exception:
        metadata = {}
        return

    parsed = {}
    for key, info in tracks.items():
        try:
            track_no = int(key)
        except Exception:
            continue
        if not isinstance(info, dict):
            info = {}
        entry = {
            "title": info.get("title"),
            "artist": info.get("artist"),
            "artwork": None,
        }
        art_path = info.get("artwork")
        if art_path:
            # Use secure path validation
            validated_path = _validate_artwork_path(art_path, ART_ROOT or base_dir)
            if validated_path:
                entry["artwork"] = validated_path
            else:
                # Path was rejected for security reasons
                entry["artwork"] = None
        parsed[track_no] = entry
    metadata = parsed

load_metadata()

# ---- DFPlayer on UART0 (/dev/serial0) ----
def init_serial():
    """Initialize serial connection with error handling."""
    try:
        ser = serial.Serial('/dev/serial0', 9600, timeout=0.1)
        logger.info("Serial port initialized successfully")
        return ser
    except serial.SerialException as e:
        logger.error(f"Failed to open serial port: {e}")
        logger.error("DFPlayer commands will not work. Check /dev/serial0 connection.")
        return None
    except PermissionError as e:
        logger.error(f"Permission denied accessing serial port: {e}")
        logger.error("Try: sudo usermod -a -G dialout $USER")
        return None
    except Exception as e:
        logger.error(f"Unexpected error initializing serial: {e}")
        return None

ser = init_serial()

def _dfplayer_checksum(payload):
    total = sum(payload) & 0xFFFF
    return (0xFFFF - total + 1) & 0xFFFF


def send(cmd, p1=0, p2=1):
    """Send command to DFPlayer with error handling.

    Args:
        cmd: Command byte (0-255).
        p1: High-order payload byte (0-255) when a 16-bit parameter is needed.
        p2: Low-order payload byte (0-255) when a 16-bit parameter is needed.
    """
    global ser
    if ser is None:
        logger.warning("Serial port not initialized, cannot send command")
        return

    try:
        if not ser.is_open:
            logger.warning("Serial port is closed, cannot send command")
            return

        pkt = bytearray([0x7E,0xFF,0x06,cmd,0x00,p1,p2,0x00,0x00,0xEF])
        cs = _dfplayer_checksum(pkt[1:7])
        pkt[7], pkt[8] = (cs>>8)&0xFF, cs&0xFF
        ser.write(pkt)
    except serial.SerialException as e:
        logger.error(f"Serial write failed: {e}")
    except OSError as e:
        logger.error(f"OS error during serial write: {e}")
    except Exception as e:
        logger.error(f"Unexpected error sending command: {e}")

def read_dfplayer_response(timeout=0.3):
    """Read 10-byte response from DFPlayer.

    Returns:
        bytes: 10-byte response packet, or None if timeout/error
    """
    global ser
    if ser is None or not ser.is_open:
        return None

    original_timeout = ser.timeout
    try:
        ser.timeout = timeout
        response = ser.read(10)
    
        if len(response) == 10 and response[0] == 0x7E and response[9] == 0xEF:
            # Validate checksum
            cs = _dfplayer_checksum(response[1:7])
            cs_high, cs_low = (cs >> 8) & 0xFF, cs & 0xFF
            if response[7] == cs_high and response[8] == cs_low:
                return response
            else:
                logger.warning("DFPlayer response checksum mismatch")
        return None
    except Exception as e:
        logger.warning(f"Error reading DFPlayer response: {e}")
        return None
    finally:
        ser.timeout = original_timeout

def query_dfplayer_file_count():
    """Query DFPlayer for number of files.

    Tries multiple query methods:
    1. Command 0x48 - Total files on TF card (all folders)
    2. Command 0x4C - Files in /mp3 folder specifically

    Returns:
        int: Number of files, or None if query failed
    """
    global ser
    if ser is None:
        return None

    try:
        # Clear any pending data
        if ser.in_waiting:
            ser.read(ser.in_waiting)

        # Try 0x48 first (total TF card files)
        logger.info("Querying DFPlayer with 0x48 (total TF card files)...")
        send(0x48, 0, 0)
        time.sleep(0.2)  # Give DFPlayer time to respond

        response = read_dfplayer_response(timeout=0.5)
        if response:
            logger.info(f"0x48 response: {response.hex()}")
            if response[3] == 0x48:
                file_count = (response[5] << 8) | response[6]
                logger.info(f"DFPlayer reports {file_count} total files on TF card")
                if file_count > 0:
                    return file_count

        # Clear buffer and try 0x4C (mp3 folder)
        if ser.in_waiting:
            ser.read(ser.in_waiting)

        logger.info("Querying DFPlayer with 0x4C (/mp3 folder files)...")
        send(0x4C, 0, 0)
        time.sleep(0.2)

        response = read_dfplayer_response(timeout=0.5)
        if response:
            logger.info(f"0x4C response: {response.hex()}")
            if response[3] == 0x4C:
                file_count = (response[5] << 8) | response[6]
                logger.info(f"DFPlayer reports {file_count} files in /mp3 folder")
                return file_count

        logger.warning("DFPlayer did not respond to file count queries (tried 0x48 and 0x4C)")
        logger.warning("Consider creating config/track_catalog.txt with your track list")
        return None
    except Exception as e:
        logger.error(f"Error querying DFPlayer file count: {e}")
        return None

def vol_set(v): v = max(0, min(30, int(v))); send(0x06,0,v)

def ensure_track_selected():
    """Ensure there is a valid selection and metadata/artwork is in sync."""
    global selected_track_idx, current_track_number
    if tracks:
        if selected_track_idx is None or not (0 <= selected_track_idx < len(tracks)):
            selected_track_idx = 0
        track_no = tracks[selected_track_idx]["number"]
    else:
        track_no = current_track_number or 1
    if current_track_number != track_no:
        current_track_number = track_no
        update_artwork_cache()

def update_artwork_cache():
    global current_art_thumb, current_art_path
    meta = metadata.get(current_track_number, {}) if current_track_number else {}
    art_path = meta.get("artwork") if isinstance(meta, dict) else None
    if art_path == current_art_path:
        return
    current_art_path = art_path
    current_art_thumb = None
    if not art_path:
        return
    if art_path in artwork_cache:
        current_art_thumb = artwork_cache[art_path]
        return
    try:
        with Image.open(art_path) as im:
            im = im.convert("RGB")
            thumb = im.copy()
            thumb.thumbnail((ART_RECT[2], ART_RECT[3]), Image.LANCZOS)
    except Exception:
        artwork_cache[art_path] = None
        return
    canvas = Image.new("RGB", (ART_RECT[2], ART_RECT[3]), (35, 35, 40))
    ox = (canvas.width - thumb.width)//2
    oy = (canvas.height - thumb.height)//2
    canvas.paste(thumb, (ox, oy))
    artwork_cache[art_path] = canvas
    current_art_thumb = canvas

def step_track(delta):
    global current_track_idx, current_track_number
    ensure_track_selected()
    if track_numbers:
        if current_track_idx is None:
            current_track_idx = 0
        current_track_idx = (current_track_idx + delta) % len(track_numbers)
        current_track_number = track_numbers[current_track_idx]
    else:
        current_track_number = max(1, current_track_number + delta)
    update_artwork_cache()

def set_track(track_no):
    global current_track_idx, current_track_number, selected_track_idx
    ensure_track_selected()
    current_track_number = max(1, int(track_no))
    if track_numbers:
        try:
            current_track_idx = track_numbers.index(current_track_number)
        except ValueError:
            pass
    for idx, info in enumerate(tracks):
        if info.get("number") == current_track_number:
            selected_track_idx = idx
            ensure_track_visible(idx)
            break
    update_artwork_cache()
# ---- Track catalog + panel geometry ----
CATALOG_FALLBACK_COUNT = 30
TRACK_HEADER_HEIGHT = 44
TRACK_ROW_HEIGHT = 32
TRACK_SCROLL_BTN_W = 40
TRACK_PANEL = (240, 50, max(180, W-260), max(130, H-70))

def _catalog_paths():
    env_path = os.environ.get("DFPLAYER_TRACK_CATALOG")
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    return [
        env_path,
        os.path.join(base_dir, "config", "track_catalog.txt"),
        "/home/pi/dfplayer_tracks.txt",
    ]

def load_track_catalog():
    """Load track catalog from file, DFPlayer query, or fallback.

    Priority order:
    1. Manual catalog file (config/track_catalog.txt or similar)
    2. Query DFPlayer for file count (auto-generate generic names)
    3. Fallback to 30 placeholder tracks

    Returns:
        list: List of track dicts with 'number' and 'title' keys
    """
    # Try manual catalog file first
    for path in _catalog_paths():
        if not path:
            continue
        try:
            if not os.path.exists(path):
                continue
        except Exception:
            continue
        tracks = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "|" in line:
                        num_str, title = line.split("|", 1)
                    else:
                        parts = line.split(None, 1)
                        if parts:
                            num_str = parts[0]
                            title = parts[1] if len(parts) > 1 else ""
                        else:
                            continue
                    try:
                        track_no = int(num_str, 10)
                    except ValueError:
                        continue
                    title = title.strip() or f"Track {track_no:03d}"
                    tracks.append(dict(number=track_no, title=title))
        except Exception:
            tracks = []
        if tracks:
            tracks.sort(key=lambda t: t["number"])
            logger.info(f"Loaded {len(tracks)} tracks from catalog file: {path}")
            return tracks

    # No catalog file found - try querying DFPlayer
    logger.info("No track catalog file found, querying DFPlayer...")
    file_count = query_dfplayer_file_count()
    if file_count and file_count > 0:
        logger.info(f"Auto-generating catalog for {file_count} tracks from DFPlayer")
        return [dict(number=i+1, title=f"Track {i+1:03d}") for i in range(file_count)]

    # Last resort: fallback placeholder tracks
    logger.warning(f"Could not query DFPlayer, using fallback {CATALOG_FALLBACK_COUNT}-track catalog")
    logger.warning("Create config/track_catalog.txt with your actual track names to fix this")
    return [dict(number=i+1, title=f"Track {i+1:03d}") for i in range(CATALOG_FALLBACK_COUNT)]

tracks = load_track_catalog()
track_numbers = [t["number"] for t in tracks]  # List of track numbers
current_track_idx = None  # Current index in track_numbers list
track_scroll = 0
selected_track_idx = 0 if tracks else None
now_playing_idx = None

def rebuild_track_numbers():
    """Rebuild track_numbers list from tracks."""
    global track_numbers
    track_numbers = [t["number"] for t in tracks]

def track_list_rect():
    tx, ty, tw, th = TRACK_PANEL
    list_x = tx + 10
    list_y = ty + TRACK_HEADER_HEIGHT
    list_w = max(40, tw - TRACK_SCROLL_BTN_W - 24)
    list_h = max(24, th - TRACK_HEADER_HEIGHT - 16)
    return list_x, list_y, list_w, list_h

def track_scroll_button_rects():
    tx, ty, tw, th = TRACK_PANEL
    list_x, list_y, list_w, list_h = track_list_rect()
    scroll_x = list_x + list_w + 8
    up_rect = (scroll_x, list_y, TRACK_SCROLL_BTN_W, 36)
    down_rect = (scroll_x, list_y + list_h - 36, TRACK_SCROLL_BTN_W, 36)
    return up_rect, down_rect

def track_visible_count():
    _, _, _, list_h = track_list_rect()
    return max(1, list_h // TRACK_ROW_HEIGHT)

def ensure_track_scroll_bounds():
    global track_scroll
    visible = track_visible_count()
    max_scroll = max(0, len(tracks) - visible)
    if track_scroll > max_scroll:
        track_scroll = max_scroll
    if track_scroll < 0:
        track_scroll = 0
    return visible

def ensure_track_visible(idx):
    global track_scroll
    visible = ensure_track_scroll_bounds()
    if idx < track_scroll:
        track_scroll = idx
    elif idx >= track_scroll + visible:
        track_scroll = idx - visible + 1
    ensure_track_scroll_bounds()

def track_label(track):
    return f"{track['number']:03d} {track['title']}"

def select_track_index(idx):
    global selected_track_idx, current_track_number
    if not tracks:
        selected_track_idx = None
        return None
    idx = idx % len(tracks)
    selected_track_idx = idx
    ensure_track_visible(idx)
    track = tracks[idx]
    track_no = track["number"]
    if current_track_number != track_no:
        current_track_number = track_no
        update_artwork_cache()
    return track

def play_track_number(track_number):
    hi = (track_number >> 8) & 0xFF
    lo = track_number & 0xFF
    send(0x03, hi, lo)

def play_track_index(idx, note=None):
    global now_playing_idx, playback_playing
    track = select_track_index(idx)
    if track is None:
        draw_ui("No tracks available")
        return False
    play_track_number(track["number"])
    now_playing_idx = selected_track_idx
    playback_playing = True
    if note is None:
        note = f"Playing {track_label(track)}"
    draw_ui(note)
    return True

def advance_track(delta):
    if not tracks:
        return False
    base = selected_track_idx if selected_track_idx is not None else 0
    return play_track_index(base + delta)

def stop_playback(note=None):
    global now_playing_idx, playback_playing
    now_playing_idx = None
    playback_playing = False
    draw_ui(note)


def handle_play_button():
    global playback_playing
    ensure_track_selected()
    if playback_playing:
        send(0x0E)
        playback_playing = False
        draw_ui("Paused")
        return
    target = now_playing_idx if now_playing_idx is not None else (selected_track_idx or 0)
    if not play_track_index(target):
        send(0x0D)
        playback_playing = True
        draw_ui("Playing")


def handle_stop_button():
    send(0x16)
    stop_playback("Stopped")


def handle_prev_button():
    if not advance_track(-1):
        send(0x02)
        draw_ui("No tracks available")


def handle_next_button():
    if not advance_track(1):
        send(0x01)
        draw_ui("No tracks available")


BUTTON_ACTIONS = {
    "play": handle_play_button,
    "stop": handle_stop_button,
    "prev": handle_prev_button,
    "next": handle_next_button,
}

# ---- Touch device ----
def open_touch():
    """Open touch input device with error handling."""
    if os.path.exists("/dev/input/touchscreen"):
        return InputDevice("/dev/input/touchscreen")
    for devpath in list_devices():
        dev = InputDevice(devpath)
        name = (dev.name or "").lower()
        if "ads7846" in name or "xpt2046" in name:
            return dev
    devs = list_devices()
    if not devs:
        raise RuntimeError("No input event devices found")
    return InputDevice(devs[0])

def init_touch():
    """Initialize touch device with error handling."""
    try:
        touch = open_touch()
        ax = touch.absinfo(ecodes.ABS_X)
        ay = touch.absinfo(ecodes.ABS_Y)
        if ax is None or ay is None:
            logger.error(f"Touch device lacks ABS axes: {touch.path} {touch.name}")
            logger.error("Touch input will not work properly")
            return None, None, None, None, None
        drv_minx, drv_maxx = ax.min, ax.max
        drv_miny, drv_maxy = ay.min, ay.max
        logger.info(f"Touch device initialized: {touch.name}")
        return touch, drv_minx, drv_maxx, drv_miny, drv_maxy
    except RuntimeError as e:
        logger.error(f"Failed to initialize touch device: {e}")
        logger.error("Touch input will not work. Ensure touch device is connected.")
        return None, 0, 4095, 0, 4095
    except PermissionError as e:
        logger.error(f"Permission denied accessing touch device: {e}")
        logger.error("Try: sudo usermod -a -G input $USER")
        return None, 0, 4095, 0, 4095
    except Exception as e:
        logger.error(f"Unexpected error initializing touch device: {e}")
        return None, 0, 4095, 0, 4095

touch, drv_minx, drv_maxx, drv_miny, drv_maxy = init_touch()

def current_ranges():
    return cal_raw if cal_raw else (drv_minx, drv_maxx, drv_miny, drv_maxy)

# ---- Framebuffer (RGB565 LE) ----
fb = open(FB, "r+b", buffering=0)
mm = mmap.mmap(fb.fileno(), W*H*2, mmap.MAP_SHARED, mmap.PROT_WRITE)

def cleanup():
    """Clean up all resources: serial port, framebuffer, and memory map."""
    global ser, mm, fb
    try:
        if hasattr(ser, 'is_open') and ser.is_open:
            ser.close()
            logger.info("Serial port closed")
    except Exception as e:
        logger.warning(f"Error closing serial port: {e}")

    try:
        if mm:
            mm.close()
            logger.info("Memory map closed")
    except Exception as e:
        logger.warning(f"Error closing memory map: {e}")

    try:
        if fb:
            fb.close()
            logger.info("Framebuffer closed")
    except Exception as e:
        logger.warning(f"Error closing framebuffer: {e}")

# Register cleanup handler
atexit.register(cleanup)

def rgb888_to_rgb565le(img):
    b = img.tobytes()
    out = bytearray(W*H*2)
    j = 0
    for i in range(0, len(b), 3):
        r = b[i]>>3; g = b[i+1]>>2; bl = b[i+2]>>3
        v = (r<<11) | (g<<5) | bl
        out[j] = v & 0xFF; out[j+1] = (v>>8) & 0xFF; j += 2
    return out

def push(img):
    if img.size != (W,H): img = img.resize((W,H))
    mm.seek(0); mm.write(rgb888_to_rgb565le(img.convert("RGB")))

# ---- Theme helpers ----
def _fallback_hex_to_rgb(value, fallback):
    if isinstance(value, str):
        v = value.lstrip("#")
        if len(v) == 6:
            try:
                return tuple(int(v[i:i+2], 16) for i in (0, 2, 4))
            except Exception:
                pass
    if isinstance(value, (list, tuple)) and len(value) == 3:
        try:
            return tuple(int(x) for x in value)
        except Exception:
            return fallback
    return fallback


def _apply_theme():
    """Load active theme (env DFPLAYER_THEME), fall back safely."""
    if load_theme is None:
        return None
    name = os.environ.get("DFPLAYER_THEME")
    try:
        return load_theme(name, THEMES_DIR)
    except Exception as exc:
        logger.warning("Failed to load theme '%s': %s; using default", name, exc)
        return default_theme() if default_theme else None


THEME = _apply_theme()


def theme_color(key, fallback):
    if THEME and hasattr(THEME, "palette"):
        val = THEME.palette.get(key)
        parser = _hex_to_rgb or _fallback_hex_to_rgb
        parsed = parser(val, None)
        if parsed:
            return parsed
    return fallback


def layout_color(key, fallback):
    if THEME and hasattr(THEME, "layout"):
        val = THEME.layout.get(key)
        parser = _hex_to_rgb or _fallback_hex_to_rgb
        parsed = parser(val, None)
        if parsed:
            return parsed
    return fallback


ACCENTS = THEME.accent_cycle() if THEME else []
if not ACCENTS:
    ACCENTS = [
        (242, 184, 75),  # amber
        (244, 126, 106), # coral
        (126, 91, 166),  # plum
        (58, 182, 197),  # teal
        (127, 163, 217)  # steel
    ]

# Core palette with safe fallbacks to the legacy colors
COLORS = {
    "bg": theme_color("bg", (12, 16, 24)),
    "panel": theme_color("panel", (26, 28, 36)),
    "panel_mid": theme_color("panel_mid", (32, 34, 46)),
    "panel_meta": theme_color("panel_meta", (38, 42, 60)),
    "text": theme_color("text", (235, 235, 235)),
    "text_dim": theme_color("text_dim", (195, 195, 200)),
    "text_muted": theme_color("text_muted", (175, 175, 185)),
    "status_good": theme_color("status_good", (70, 175, 120)),
    "status_warn": theme_color("status_warn", (215, 165, 60)),
    "status_bad": theme_color("status_bad", (195, 80, 80)),
}

LAYOUT = {
    "radius_lg": int(THEME.metrics.get("radius_lg", 20)) if THEME else 20,
    "radius_sm": int(THEME.metrics.get("radius_sm", 10)) if THEME else 10,
    "stroke": int(THEME.metrics.get("stroke", 2)) if THEME else 2,
    "padding": int(THEME.metrics.get("padding", 12)) if THEME else 12,
    "gap": int(THEME.metrics.get("gap", 8)) if THEME else 8,
    "touch_min": int(THEME.metrics.get("touch_min", 44)) if THEME else 44,
    "progress_height": int(THEME.layout.get("progress_height", 10)) if THEME else 10,
    "volume_width": int(THEME.layout.get("volume_width", 22)) if THEME else 22,
}

BUTTON_FILL_MAIN = {
    "play": layout_color("button_primary", COLORS["status_good"]),
    "stop": COLORS["status_bad"],
    "prev": layout_color("button_secondary", ACCENTS[2] if len(ACCENTS) > 2 else (80, 110, 185)),
    "next": layout_color("button_secondary", ACCENTS[3] if len(ACCENTS) > 3 else (80, 110, 185)),
}

# ---- UI ----
try:
    FONTB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    FONTM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    FONTS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except Exception:
    FONTB = ImageFont.load_default(); FONTM = ImageFont.load_default(); FONTS = ImageFont.load_default()

BUTTONS = [
    dict(key="play", rect=(20,  20, 200, 80), fill=BUTTON_FILL_MAIN["play"], text=COLORS["text"]),
    dict(key="stop", rect=(20, 110, 200, 60), fill=BUTTON_FILL_MAIN["stop"], text=(255, 255, 255)),
    dict(key="prev", rect=(20,  180, 94,  60), fill=BUTTON_FILL_MAIN["prev"], text=COLORS["text"]),
    dict(key="next", rect=(126, 180, 94,  60), fill=BUTTON_FILL_MAIN["next"], text=COLORS["text"]),
]
VOLBAR_RECT = (20, 260, 200, 24)
vol = 18
BTN_CAL = (4, 4, 52, 30)             # top-left  CAL
BTN_CFG = (W-56, 4, 52, 30)          # top-right CFG
playback_playing = False

def font_line_height(font):
    try:
        bbox = font.getbbox("Ay")
        return bbox[3] - bbox[1]
    except Exception:
        try:
            return font.getsize("Ay")[1]
        except Exception:
            return 20

def draw_text_center(d, x, y, w, h, text, font, color=(255,255,255)):
    x0,y0,x1,y1 = d.textbbox((0,0), text, font=font)
    tw,th = x1-x0, y1-y0
    d.text((x + (w-tw)//2, y + (h-th)//2), text, font=font, fill=color)

def draw_wrapped_text(d, text, font, x, y, max_width, fill, line_spacing=4):
    if not text:
        return y
    ascent, descent = font.getmetrics() if hasattr(font, "getmetrics") else (font.size, 0)
    line_height = ascent + descent + line_spacing
    line = ""
    for word in text.split():
        candidate = word if not line else f"{line} {word}"
        try:
            width = d.textlength(candidate, font=font)
        except AttributeError:
            x0, _, x1, _ = d.textbbox((0, 0), candidate, font=font)
            width = x1 - x0
        if width <= max_width or not line:
            line = candidate
        else:
            d.text((x, y), line, font=font, fill=fill)
            y += line_height
            line = word
    if line:
        d.text((x, y), line, font=font, fill=fill)
        y += line_height
    return y

def current_track_meta():
    ensure_track_selected()
    return metadata.get(current_track_number, {}) if current_track_number else {}

def draw_ui(note=None):
    ensure_track_selected()
    global track_scroll

    def xywh(rect):
        x,y,w,h = rect
        return [x, y, x+w, y+h]

    img = Image.new("RGB", (W, H), COLORS["bg"])
    d = ImageDraw.Draw(img)

    # main buttons
    for button in BUTTONS:
        x, y, w, h = button["rect"]
        label_key = button["key"]
        label = {
            "play": "Pause" if playback_playing else "Play",
            "stop": "Stop",
            "prev": "Prev",
            "next": "Next",
        }[label_key]
        radius = LAYOUT["radius_lg"] if label_key in {"play", "stop"} else LAYOUT["radius_sm"]
        d.rounded_rectangle([x, y, x + w, y + h], radius=radius, fill=button["fill"])
        font = FONTB if label_key in {"play", "stop"} else FONTM
        draw_text_center(d, x, y, w, h, label, font, color=button["text"])

    # volume bar
    vx, vy, vw, vh = VOLBAR_RECT
    d.text((vx, vy - 28), "Volume", font=FONTS, fill=COLORS["text"])
    d.rounded_rectangle([vx, vy, vx + vw, vy + vh], radius=LAYOUT["radius_sm"], fill=COLORS["panel_mid"])
    fillw = int(vw * vol / 30)
    d.rounded_rectangle([vx, vy, vx + fillw, vy + vh], radius=LAYOUT["radius_sm"], fill=COLORS["status_warn"])
    d.text((vx + vw + 8, vy - 4), f"{vol:02d}", font=FONTM, fill=COLORS["text"])

    # artwork region
    ax, ay, aw, ah = ART_RECT
    d.rounded_rectangle([ax, ay, ax+aw, ay+ah], radius=LAYOUT["radius_lg"], fill=COLORS["panel_mid"])
    if current_art_thumb:
        img.paste(current_art_thumb, (ax, ay))
    else:
        d.text((ax + 24, ay + ah//2 - 10), "No artwork", font=FONTS, fill=COLORS["text_dim"])

    # metadata region
    ix, iy, iw, ih = INFO_RECT
    d.rounded_rectangle([ix, iy, ix+iw, iy+ih], radius=LAYOUT["radius_sm"], fill=COLORS["panel_meta"])
    meta = current_track_meta()
    title = meta.get("title") if isinstance(meta, dict) else None
    if not title:
        title = f"Track {current_track_number:03d}" if current_track_number else "Track"
    artist = meta.get("artist") if isinstance(meta, dict) else None
    if not artist:
        artist = "Unknown Artist"
    next_y = draw_wrapped_text(d, title, FONTM, ix+12, iy+8, iw-24, fill=COLORS["text"])
    draw_wrapped_text(d, artist, FONTS, ix+12, max(next_y, iy+44), iw-24, fill=COLORS["text_dim"])
    d.text((ix+12, iy+ih-24), f"#{current_track_number:03d}" if current_track_number else "#----", font=FONTS, fill=COLORS["text_muted"])

    # top buttons (use xywh -> xyxy)
    d.rounded_rectangle(xywh(BTN_CAL), radius=LAYOUT["radius_sm"], fill=ACCENTS[2 % len(ACCENTS)])
    draw_text_center(d, *BTN_CAL, "CAL", FONTS)

    d.rounded_rectangle(xywh(BTN_CFG), radius=LAYOUT["radius_sm"], fill=ACCENTS[0])
    draw_text_center(d, *BTN_CFG, "CFG", FONTS)

    # track list panel
    tx, ty, tw, th = TRACK_PANEL
    d.rounded_rectangle([tx, ty, tx+tw, ty+th], radius=LAYOUT["radius_lg"], fill=COLORS["panel"])
    d.text((tx + 14, ty + 10), "Tracks", font=FONTM, fill=COLORS["text"])
    if now_playing_idx is not None and 0 <= now_playing_idx < len(tracks):
        status = track_label(tracks[now_playing_idx])
        d.text((tx + 14, ty + 10 + font_line_height(FONTM) + 4), f"Now playing: {status}", font=FONTS, fill=COLORS["text_dim"])
    list_x, list_y, list_w, list_h = track_list_rect()
    up_rect, down_rect = track_scroll_button_rects()
    visible = ensure_track_scroll_bounds()
    max_scroll = max(0, len(tracks) - visible)

    # draw rows
    if tracks:
        for i in range(visible):
            idx = track_scroll + i
            if idx >= len(tracks):
                break
            row_y = list_y + i * TRACK_ROW_HEIGHT
            row_h = TRACK_ROW_HEIGHT - 6
            row_rect = (list_x, row_y, list_w, row_h)
            fill = COLORS["panel_meta"]
            text_color = COLORS["text"]
            label = track_label(tracks[idx])
            if idx == now_playing_idx:
                fill = COLORS["status_warn"]
                text_color = COLORS["bg"]
                label = f"▶ {label}"
            elif idx == selected_track_idx:
                fill = ACCENTS[3 % len(ACCENTS)]
            d.rounded_rectangle([row_rect[0], row_rect[1], row_rect[0]+row_rect[2], row_rect[1]+row_rect[3]], radius=LAYOUT["radius_sm"], fill=fill)
            draw_text_center(d, *row_rect, label, FONTS, color=text_color)
    else:
        d.text((list_x, list_y + 6), "No tracks found", font=FONTS, fill=COLORS["text"])

    # scroll buttons
    up_fill = COLORS["panel_mid"] if track_scroll > 0 else COLORS["panel"]
    down_fill = COLORS["panel_mid"] if track_scroll < max_scroll else COLORS["panel"]
    up_color = COLORS["text"] if track_scroll > 0 else COLORS["text_dim"]
    down_color = COLORS["text"] if track_scroll < max_scroll else COLORS["text_dim"]
    d.rounded_rectangle(xywh(up_rect), radius=LAYOUT["radius_sm"], fill=up_fill)
    d.rounded_rectangle(xywh(down_rect), radius=LAYOUT["radius_sm"], fill=down_fill)
    ux, uy, uw, uh = up_rect
    dx, dy, dw, dh = down_rect
    up_arrow = [(ux + uw/2, uy + 8), (ux + uw - 10, uy + uh - 8), (ux + 10, uy + uh - 8)]
    down_arrow = [(dx + 10, dy + 8), (dx + dw - 10, dy + 8), (dx + dw/2, dy + dh - 8)]
    d.polygon(up_arrow, fill=up_color)
    d.polygon(down_arrow, fill=down_color)

    if note:
        d.text((6, H-22), note, font=FONTS, fill=COLORS["text"])

    push(img)

def inside(rect, px, py):
    x,y,w,h = rect
    return x<=px<=x+w and y<=py<=y+h

def update_volume_from_x(px):
    global vol
    x, y, w, _ = VOLBAR_RECT
    clamped = max(x, min(x + w, px))
    new_vol = int(round((clamped - x) * 30 / w))
    new_vol = max(0, min(30, new_vol))
    if new_vol != vol:
        vol = new_vol
        vol_set(vol)
        draw_ui()


def handle_button_press(label):
    global playback_playing
    if label == "Play":
        if playback_playing:
            send(0x0E)
            stop_playback("Paused")
        else:
            if now_playing_idx is not None and 0 <= now_playing_idx < len(tracks):
                send(0x0D)
                playback_playing = True
                draw_ui("Resumed")
            elif tracks:
                target = selected_track_idx if selected_track_idx is not None else 0
                play_track_index(target)
            else:
                ensure_track_selected()
                send(0x0D)
                draw_ui("Play")
    elif label == "Prev":
        if not advance_track(-1):
            send(0x02)
            draw_ui()
    elif label == "Next":
        if not advance_track(1):
            send(0x01)
            draw_ui()
    elif label == "Stop":
        send(0x16)
        stop_playback("Stopped")


def handle_tap(px, py):
    global orient_idx, track_scroll
    if inside(BTN_CFG, px, py):
        orient_idx = (orient_idx + 1) % len(ORIENTS)
        save_orientation()
        draw_ui(f"Orientation {orient_idx+1}/8")
        return
    if inside(BTN_CAL, px, py):
        quick_calibration()
        draw_ui()
        return

    list_rect = track_list_rect()
    up_rect, down_rect = track_scroll_button_rects()
    if inside(up_rect, px, py):
        if track_scroll > 0:
            track_scroll -= 1
            ensure_track_scroll_bounds()
            draw_ui()
        return
    if inside(down_rect, px, py):
        visible = ensure_track_scroll_bounds()
        max_scroll = max(0, len(tracks) - visible)
        if track_scroll < max_scroll:
            track_scroll += 1
            ensure_track_scroll_bounds()
            draw_ui()
        return
    if inside(list_rect, px, py):
        if tracks:
            row = (py - list_rect[1]) // TRACK_ROW_HEIGHT
            visible = track_visible_count()
            if 0 <= row < visible:
                idx = track_scroll + int(row)
                if idx < len(tracks):
                    play_track_index(idx)
        else:
            draw_ui()
        return

    for button in BUTTONS:
        if inside(button["rect"], px, py):
            action = BUTTON_ACTIONS.get(button["key"])
            if action:
                action()
            return

    if inside(VOLBAR_RECT, px, py):
        update_volume_from_x(px)


def scale_xy(rx, ry):
    minx, maxx, miny, maxy = current_ranges()
    o = ORIENTS[orient_idx]
    x, y = rx, ry
    if o["SWAP_XY"]: x, y = y, x
    if o["FLIP_X"]:  x = maxx - (x - minx)
    if o["FLIP_Y"]:  y = maxy - (y - miny)
    if maxx==minx: maxx=minx+1
    if maxy==miny: maxy=miny+1
    sx = int((x - minx) * (W-1) / (maxx - minx))
    sy = int((y - miny) * (H-1) / (maxy - miny))
    return max(0,min(W-1,sx)), max(0,min(H-1,sy))

def wait_touch_median(timeout=8.0, samples=18):
    t0 = time.time(); touching=False
    bufx, bufy = [], []
    while time.time()-t0 < timeout:
        for ev in touch.read_loop():
            if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
                touching = (ev.value == 1)
                if not touching: bufx.clear(); bufy.clear()
            elif ev.type == ecodes.EV_ABS:
                if ev.code == ecodes.ABS_X: rx = ev.value
                elif ev.code == ecodes.ABS_Y: ry = ev.value
                else: continue
                if touching and 'rx' in locals() and 'ry' in locals():
                    bufx.append(rx); bufy.append(ry)
                    if len(bufx) >= samples:
                        return (int(statistics.median(bufx)), int(statistics.median(bufy)))
            if not touching: time.sleep(0.002)
    return None

def quick_calibration():
    global cal_raw
    pts = [(20,20), (W-20,20), (W-20,H-20), (20,H-20)]
    raw = []
    for (tx,ty) in pts:
        img = Image.new("RGB",(W,H),(0,0,0))
        d = ImageDraw.Draw(img)
        d.ellipse((tx-6,ty-6,tx+6,ty+6), fill=(255,255,0))
        d.line((tx-20,ty,tx+20,ty), fill=(255,255,0))
        d.line((tx,ty-20,tx,ty+20), fill=(255,255,0))
        d.text((10,H-24), "Tap target (hold ~0.5s)...", font=FONTS, fill=(220,220,220))
        push(img)
        med = wait_touch_median()
        if med is None: draw_ui("Calibration canceled."); time.sleep(0.8); return
        raw.append(med)

    # invert orientation to driver axes to compute true min/max
    o = ORIENTS[orient_idx]
    def inv_raw(rx,ry):
        x,y = rx,ry
        if o["FLIP_Y"]:  y = (drv_miny + drv_maxy) - y
        if o["FLIP_X"]:  x = (drv_minx + drv_maxx) - x
        if o["SWAP_XY"]: x,y = y,x
        return x,y

    inv = [inv_raw(rx,ry) for (rx,ry) in raw]
    left_x  = int(statistics.median([inv[0][0], inv[3][0]]))
    right_x = int(statistics.median([inv[1][0], inv[2][0]]))
    top_y   = int(statistics.median([inv[0][1], inv[1][1]]))
    bot_y   = int(statistics.median([inv[2][1], inv[3][1]]))
    if right_x <= left_x: right_x = left_x + 1
    if bot_y   <= top_y : bot_y   = top_y  + 1
    cal_dir = os.path.dirname(CAL_PATH)
    if cal_dir and not os.path.exists(cal_dir):
        os.makedirs(cal_dir, exist_ok=True)
    with open(CAL_PATH,"w") as f:
        f.write(f"{left_x} {right_x} {top_y} {bot_y}\n")
    cal_raw = (left_x, right_x, top_y, bot_y)
    save_touch_settings()
    draw_ui("Calibrated."); time.sleep(0.6)

def main_loop():
    global vol, playback_playing, selected_track_idx, touch

    if touch is None:
        logger.error("Touch device not initialized. Cannot start main loop.")
        logger.error("Please check touch device connection and permissions.")
        sys.exit(1)

    ensure_track_selected()
    if selected_track_idx is None and tracks:
        try:
            idx = next(i for i, info in enumerate(tracks) if info.get("number") == current_track_number)
        except StopIteration:
            idx = 0
        selected_track_idx = idx
        ensure_track_visible(idx)
    draw_ui()
    vol_set(vol)

    touching = False
    drag_vol = False
    raw_bufx, raw_bufy = [], []
    touch_start = None
    touch_last = None
    last_drag = 0.0

    for ev in touch.read_loop():
        if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
            touching = (ev.value == 1)
            if touching:
                raw_bufx.clear()
                raw_bufy.clear()
                touch_start = None
                touch_last = None
                drag_vol = False
            else:
                if drag_vol:
                    drag_vol = False
                elif touch_last:
                    handle_tap(*touch_last)
                raw_bufx.clear()
                raw_bufy.clear()
                touch_start = None
                touch_last = None
        elif ev.type == ecodes.EV_ABS:
            if ev.code == ecodes.ABS_X:
                raw_bufx.append(ev.value)
            elif ev.code == ecodes.ABS_Y:
                raw_bufy.append(ev.value)
            else:
                continue

            if touching and len(raw_bufx) >= 4 and len(raw_bufy) >= 4:
                med_rx = int(statistics.median(raw_bufx[-6:]))
                med_ry = int(statistics.median(raw_bufy[-6:]))
                px, py = scale_xy(med_rx, med_ry)
                touch_last = (px, py)

                if touch_start is None:
                    touch_start = (px, py)
                    if inside(VOLBAR_RECT, px, py):
                        drag_vol = True
                        last_drag = 0.0
                        update_volume_from_x(px)

                if not drag_vol and len(raw_bufx) == 4 and len(raw_bufy) == 4:
                    if inside(BTN_CFG, px, py):
                        orient_idx = (orient_idx + 1) % len(ORIENTS)
                        save_touch_settings()
                        draw_ui(f"Orientation {orient_idx+1}/8")
                        time.sleep(0.25)
                        continue
                    if inside(BTN_CAL, px, py):
                        quick_calibration(); draw_ui(); continue

                    list_rect = track_list_rect()
                    up_rect, down_rect = track_scroll_button_rects()
                    if inside(up_rect, px, py):
                        if track_scroll > 0:
                            track_scroll -= 1
                            ensure_track_scroll_bounds()
                            draw_ui()
                        continue
                    if inside(down_rect, px, py):
                        visible = ensure_track_scroll_bounds()
                        max_scroll = max(0, len(tracks) - visible)
                        if track_scroll < max_scroll:
                            track_scroll += 1
                            ensure_track_scroll_bounds()
                            draw_ui()
                        continue
                    if inside(list_rect, px, py):
                        if tracks:
                            row = (py - list_rect[1]) // TRACK_ROW_HEIGHT
                            visible = track_visible_count()
                            if 0 <= row < visible:
                                idx = track_scroll + int(row)
                                if idx < len(tracks):
                                    play_track_index(idx)
                        else:
                            draw_ui()
                        continue

                    handled = False
                    for button in BUTTONS:
                        if inside(button["rect"], px, py):
                            action = BUTTON_ACTIONS.get(button["key"])
                            if action:
                                action()
                            handled = True
                            break
                    if handled:
                        continue

                    vx, vy, vw, vh = VOLBAR_RECT
                    if inside((vx, vy, vw, vh), px, py):
                        drag_vol = True

                if drag_vol:
                    now = time.time()
                    if now - last_drag > 0.02:
                        update_volume_from_x(px)
                        last_drag = now

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        pass
