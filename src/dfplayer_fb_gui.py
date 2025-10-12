import os, sys, time, mmap, serial
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

# Basic orientation that worked for your panel; we'll refine next commit
SWAP_XY = True
FLIP_X  = False
FLIP_Y  = True

# ---- DFPlayer on UART0 (/dev/serial0) ----
ser = serial.Serial('/dev/serial0', 9600, timeout=0.1)
def send(cmd, p1=0, p2=1):
    pkt = bytearray([0x7E,0xFF,0x06,cmd,0x00,p1,p2,0x00,0x00,0xEF])
    cs = (-sum(pkt[1:7])) & 0xFFFF
    pkt[7], pkt[8] = (cs>>8)&0xFF, cs&0xFF
    ser.write(pkt)
def vol_set(v): v=max(0,min(30,int(v))); send(0x06,0,v)

# ---- Touch device discovery ----
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
minx,maxx = ax.min, ax.max
miny,maxy = ay.min, ay.max

def scale_xy(rx, ry):
    x, y = rx, ry
    if SWAP_XY: x, y = y, x
    if FLIP_X:  x = maxx - (x - minx)
    if FLIP_Y:  y = maxy - (y - miny)
    if maxx==minx: maxx=minx+1
    if maxy==miny: maxy=miny+1
    sx = int((x - minx) * (W-1) / (maxx - minx))
    sy = int((y - miny) * (H-1) / (maxy - miny))
    return max(0,min(W-1,sx)), max(0,min(H-1,sy))

# ---- Framebuffer (RGB565 little-endian) ----
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
    FONTM = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
except Exception:
    FONTB = ImageFont.load_default(); FONTM = ImageFont.load_default()

buttons = {
    "Play": (20,  20, 200, 90),
    "Prev": (260, 20, 90,  90),
    "Next": (360, 20, 90,  90),
    "Stop": (20, 130, 200, 80),
}
volbar = (260, 130, 190, 20)
vol = 18

def draw():
    img = Image.new("RGB",(W,H),(15,15,18))
    d = ImageDraw.Draw(img)
    for label,(x,y,w,h) in buttons.items():
        d.rounded_rectangle([x,y,x+w,y+h], radius=16, fill=(60,170,90))
        bbox = d.textbbox((0,0), label, font=FONTB); tw,th = bbox[2]-bbox[0], bbox[3]-bbox[1]
        d.text((x+w//2 - tw//2, y+h//2 - th//2), label, font=FONTB, fill=(255,255,255))
    x,y,w,h = volbar
    d.rounded_rectangle([x,y,x+w,y+h], radius=8, fill=(60,60,60))
    fillw = int(w*vol/30)
    d.rounded_rectangle([x,y,x+fillw,y+h], radius=8, fill=(200,200,60))
    d.text((x, y+24), f"Vol {vol:02d}", font=FONTM, fill=(230,230,230))
    push(img)

def handle_press(px,py):
    global vol
    for label,(x,y,w,h) in buttons.items():
        if x<=px<=x+w and y<=py<=y+h:
            if   label=="Play": send(0x0F,0,1)
            elif label=="Prev": send(0x02)
            elif label=="Next": send(0x01)
            elif label=="Stop": send(0x16)
            draw(); return
    x,y,w,h = volbar
    if y<=py<=y+h and x<=px<=x+w:
        vol = int((px-x)*30/w); vol_set(vol); draw()

# initial paint + volume
draw(); vol_set(vol)

# ---- Touch loop (simple) ----
rx=ry=None; touching=False
for ev in touch.read_loop():
    if ev.type == ecodes.EV_ABS:
        if ev.code == ecodes.ABS_X: rx = ev.value
        elif ev.code == ecodes.ABS_Y: ry = ev.value
        if touching and rx is not None and ry is not None:
            sx,sy = scale_xy(rx,ry)
            handle_press(sx,sy)
    elif ev.type == ecodes.EV_KEY and ev.code == ecodes.BTN_TOUCH:
        touching = (ev.value == 1)
        if not touching: rx=ry=None
