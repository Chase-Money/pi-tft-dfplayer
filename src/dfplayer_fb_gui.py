import os, sys, time, mmap, serial, statistics
from PIL import Image, ImageDraw, ImageFont
from evdev import InputDevice, ecodes, list_devices

FB = "/dev/fb1"

def get_fb_size(fb):
    try:
        node = "/sys/class/graphics/" + os.path.basename(fb) + "/virtual_size"
        w, h = map(int, open(node).read().strip().split(','))
        return w, h
    except Exception:
        return 480, 320

W, H = get_fb_size(FB)

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
CAL_PATH = "/home/chase/.touch_cal.txt"
cal_raw = None  # (minx, maxx, miny, maxy)

# ---- DFPlayer on UART0 (/dev/serial0) ----
ser = serial.Serial('/dev/serial0', 9600, timeout=0.1)
def send(cmd, p1=0, p2=1):
    pkt = bytearray([0x7E,0xFF,0x06,cmd,0x00,p1,p2,0x00,0x00,0xEF])
    cs = (-sum(pkt[1:7])) & 0xFFFF
    pkt[7], pkt[8] = (cs>>8)&0xFF, cs&0xFF
    ser.write(pkt)
def vol_set(v): v = max(0, min(30, int(v))); send(0x06,0,v)

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
            return tracks
    return [dict(number=i+1, title=f"Track {i+1:03d}") for i in range(CATALOG_FALLBACK_COUNT)]

tracks = load_track_catalog()
track_scroll = 0
selected_track_idx = 0 if tracks else None
now_playing_idx = None

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

def play_track_number(track_number):
    hi = (track_number >> 8) & 0xFF
    lo = track_number & 0xFF
    send(0x03, hi, lo)

def play_track_index(idx, note=None):
    global selected_track_idx, now_playing_idx
    if not tracks:
        draw_ui("No tracks available")
        return
    idx = max(0, min(len(tracks) - 1, idx))
    selected_track_idx = idx
    now_playing_idx = idx
    ensure_track_visible(idx)
    track = tracks[idx]
    play_track_number(track["number"])
    if note is None:
        note = f"Playing {track_label(track)}"
    draw_ui(note)

def advance_track(delta):
    if not tracks:
        return False
    global selected_track_idx
    if selected_track_idx is None:
        selected_track_idx = 0 if delta >= 0 else len(tracks) - 1
    else:
        selected_track_idx = max(0, min(len(tracks) - 1, selected_track_idx + delta))
    play_track_index(selected_track_idx)
    return True

def stop_playback(note=None):
    global now_playing_idx
    now_playing_idx = None
    draw_ui(note)

# ---- Touch device ----
def open_touch():
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

touch = open_touch()
ax = touch.absinfo(ecodes.ABS_X)
ay = touch.absinfo(ecodes.ABS_Y)
if ax is None or ay is None:
    print(f"Touch device lacks ABS axes: {touch.path} {touch.name}", file=sys.stderr); sys.exit(1)
drv_minx, drv_maxx = ax.min, ax.max
drv_miny, drv_maxy = ay.min, ay.max

# load saved calibration if present
if os.path.exists(CAL_PATH):
    try:
        with open(CAL_PATH,"r") as f:
            vals = list(map(int, f.read().strip().split()))
            if len(vals)==4: cal_raw = tuple(vals)
    except Exception:
        pass

def current_ranges():
    return cal_raw if cal_raw else (drv_minx, drv_maxx, drv_miny, drv_maxy)

# ---- Framebuffer (RGB565 LE) ----
fb = open(FB, "r+b", buffering=0)
mm = mmap.mmap(fb.fileno(), W*H*2, mmap.MAP_SHARED, mmap.PROT_WRITE)

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

# ---- UI ----
try:
    FONTB = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 44)
    FONTM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
    FONTS = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 18)
except Exception:
    FONTB = ImageFont.load_default(); FONTM = ImageFont.load_default(); FONTS = ImageFont.load_default()

buttons = {
    "Play": (20,  20, 200, 90),
    "Stop": (20, 120, 200, 70),
    "Prev": (20, 200, 90,  70),
    "Next": (130, 200, 90,  70),
}
volbar = (20, 250, 200, 20)
vol = 18
BTN_CAL = (4, 4, 52, 30)             # top-left  CAL
BTN_CFG = (W-56, 4, 52, 30)          # top-right CFG

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

def draw_ui(note=None):
    global track_scroll

    def xywh(rect):
        x,y,w,h = rect
        return [x, y, x+w, y+h]

    img = Image.new("RGB",(W,H),(15,15,18))
    d = ImageDraw.Draw(img)

    # main buttons
    for label,(x,y,w,h) in buttons.items():
        d.rounded_rectangle([x,y,x+w,y+h], radius=16, fill=(60,170,90))
        draw_text_center(d, x,y,w,h, label, FONTB)

    # volume bar
    x,y,w,h = volbar
    d.rounded_rectangle([x,y,x+w,y+h], radius=8, fill=(60,60,60))
    fillw = int(w*vol/30)
    d.rounded_rectangle([x,y,x+fillw,y+h], radius=8, fill=(200,200,60))
    d.text((x, y+24), f"Vol {vol:02d}", font=FONTM, fill=(230,230,230))

    # top buttons (use xywh -> xyxy)
    d.rounded_rectangle(xywh(BTN_CAL), radius=6, fill=(90,90,140))
    draw_text_center(d, *BTN_CAL, "CAL", FONTS)

    d.rounded_rectangle(xywh(BTN_CFG), radius=6, fill=(90,140,90))
    draw_text_center(d, *BTN_CFG, "CFG", FONTS)

    # track list panel
    tx, ty, tw, th = TRACK_PANEL
    d.rounded_rectangle([tx, ty, tx+tw, ty+th], radius=16, fill=(28,30,36))
    d.text((tx + 14, ty + 8), "Tracks", font=FONTM, fill=(225,225,225))
    if now_playing_idx is not None and 0 <= now_playing_idx < len(tracks):
        status = track_label(tracks[now_playing_idx])
        d.text((tx + 14, ty + 8 + font_line_height(FONTM) + 2), f"Now playing: {status}", font=FONTS, fill=(200,200,200))
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
            fill = (45,48,60)
            text_color = (220,220,220)
            label = track_label(tracks[idx])
            if idx == now_playing_idx:
                fill = (190,140,40)
                text_color = (25,25,25)
                label = f"▶ {label}"
            elif idx == selected_track_idx:
                fill = (80,100,160)
            d.rounded_rectangle([row_rect[0], row_rect[1], row_rect[0]+row_rect[2], row_rect[1]+row_rect[3]], radius=10, fill=fill)
            draw_text_center(d, *row_rect, label, FONTS, color=text_color)
    else:
        d.text((list_x, list_y + 6), "No tracks found", font=FONTS, fill=(210,210,210))

    # scroll buttons
    up_fill = (90,90,110) if track_scroll > 0 else (55,55,70)
    down_fill = (90,90,110) if track_scroll < max_scroll else (55,55,70)
    up_color = (235,235,235) if track_scroll > 0 else (130,130,130)
    down_color = (235,235,235) if track_scroll < max_scroll else (130,130,130)
    d.rounded_rectangle(xywh(up_rect), radius=10, fill=up_fill)
    d.rounded_rectangle(xywh(down_rect), radius=10, fill=down_fill)
    ux, uy, uw, uh = up_rect
    dx, dy, dw, dh = down_rect
    up_arrow = [(ux + uw/2, uy + 8), (ux + uw - 10, uy + uh - 8), (ux + 10, uy + uh - 8)]
    down_arrow = [(dx + 10, dy + 8), (dx + dw - 10, dy + 8), (dx + dw/2, dy + dh - 8)]
    d.polygon(up_arrow, fill=up_color)
    d.polygon(down_arrow, fill=down_color)

    if note:
        d.text((6, H-22), note, font=FONTS, fill=(210,210,210))

    push(img)

def inside(rect, px, py):
    x,y,w,h = rect
    return x<=px<=x+w and y<=py<=y+h

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
    with open(CAL_PATH,"w") as f:
        f.write(f"{left_x} {right_x} {top_y} {bot_y}\n")
    cal_raw = (left_x, right_x, top_y, bot_y)
    draw_ui("Calibrated."); time.sleep(0.6)

def main_loop():
    global orient_idx, vol, track_scroll, selected_track_idx
    draw_ui(); vol_set(vol)
    touching=False; drag_vol=False
    raw_bufx,raw_bufy=[],[]
    last_drag=0.0

    for ev in touch.read_loop():
        if ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
            touching = (ev.value == 1)
            if not touching:
                raw_bufx.clear(); raw_bufy.clear(); drag_vol=False
        elif ev.type == ecodes.EV_ABS:
            if ev.code == ecodes.ABS_X: rx = ev.value; raw_bufx.append(rx)
            elif ev.code == ecodes.ABS_Y: ry = ev.value; raw_bufy.append(ry)
            else: continue

            if touching and len(raw_bufx)>=4 and len(raw_bufy)>=4:
                med_rx = int(statistics.median(raw_bufx[-6:]))
                med_ry = int(statistics.median(raw_bufy[-6:]))
                px,py = scale_xy(med_rx, med_ry)

                if not drag_vol and len(raw_bufx)==4 and len(raw_bufy)==4:
                    if inside(BTN_CFG, px, py):
                        orient_idx = (orient_idx+1) % len(ORIENTS)
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

                    handled=False
                    for label,(x,y,w,h) in buttons.items():
                        if inside((x,y,w,h), px, py):
                            if label == "Play":
                                if tracks:
                                    target = selected_track_idx if selected_track_idx is not None else 0
                                    play_track_index(target)
                                else:
                                    send(0x0F,0,1); draw_ui()
                                handled=True; break
                            elif label == "Prev":
                                if not advance_track(-1):
                                    send(0x02); draw_ui()
                                handled=True; break
                            elif label == "Next":
                                if not advance_track(1):
                                    send(0x01); draw_ui()
                                handled=True; break
                            elif label == "Stop":
                                send(0x16)
                                stop_playback("Stopped")
                                handled=True; break
                    if handled:
                        continue
                    x,y,w,h = volbar
                    if inside((x,y,w,h), px, py):
                        drag_vol=True

                if drag_vol:
                    now=time.time()
                    if now-last_drag>0.02:
                        x,y,w,h = volbar
                        clamped=max(x,min(x+w,px))
                        vol = int((clamped-x)*30/w)
                        vol_set(vol); draw_ui()
                        last_drag=now

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        pass
