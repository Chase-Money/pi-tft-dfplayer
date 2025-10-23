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
CAL_PATH = os.path.expanduser("~/.touch_cal.txt")
cal_raw = None  # (minx, maxx, miny, maxy)

# ---- DFPlayer on UART0 (/dev/serial0) ----
ser = serial.Serial('/dev/serial0', 9600, timeout=0.1)
def send(cmd, p1=0, p2=1):
    pkt = bytearray([0x7E,0xFF,0x06,cmd,0x00,p1,p2,0x00,0x00,0xEF])
    cs = (-sum(pkt[1:7])) & 0xFFFF
    pkt[7], pkt[8] = (cs>>8)&0xFF, cs&0xFF
    ser.write(pkt)
def vol_set(v): v = max(0, min(30, int(v))); send(0x06,0,v)

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
    "Prev": (260, 20, 90,  90),
    "Next": (360, 20, 90,  90),
    "Stop": (20, 130, 200, 80),
}
volbar = (260, 130, 190, 20)
vol = 18
BTN_CAL = (4, 4, 52, 30)             # top-left  CAL
BTN_CFG = (W-56, 4, 52, 30)          # top-right CFG
playback_playing = False

def draw_text_center(d, x, y, w, h, text, font, color=(255,255,255)):
    x0,y0,x1,y1 = d.textbbox((0,0), text, font=font)
    tw,th = x1-x0, y1-y0
    d.text((x + (w-tw)//2, y + (h-th)//2), text, font=font, fill=color)

def draw_ui(note=None):
    def xywh(rect):
        x,y,w,h = rect
        return [x, y, x+w, y+h]

    img = Image.new("RGB",(W,H),(15,15,18))
    d = ImageDraw.Draw(img)

    # main buttons
    for label,(x,y,w,h) in buttons.items():
        d.rounded_rectangle([x,y,x+w,y+h], radius=16, fill=(60,170,90))
        if label == "Play" and playback_playing:
            display_label = "Pause"
        else:
            display_label = label
        draw_text_center(d, x,y,w,h, display_label, FONTB)

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
    cal_dir = os.path.dirname(CAL_PATH)
    if cal_dir and not os.path.exists(cal_dir):
        os.makedirs(cal_dir, exist_ok=True)
    with open(CAL_PATH,"w") as f:
        f.write(f"{left_x} {right_x} {top_y} {bot_y}\n")
    cal_raw = (left_x, right_x, top_y, bot_y)
    draw_ui("Calibrated."); time.sleep(0.6)

def main_loop():
    global orient_idx, vol, playback_playing
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

                    for label,(x,y,w,h) in buttons.items():
                        if inside((x,y,w,h), px, py):
                            if label=="Play":
                                if playback_playing:
                                    send(0x0E)
                                    playback_playing = False
                                else:
                                    send(0x0D)
                                    playback_playing = True
                            elif label=="Prev":
                                send(0x02)
                                playback_playing = True
                            elif label=="Next":
                                send(0x01)
                                playback_playing = True
                            elif label=="Stop":
                                send(0x16)
                                playback_playing = False
                            draw_ui()
                            break
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
