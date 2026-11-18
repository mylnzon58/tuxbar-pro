"""
tuxbar_pro/renderer.py — Native 2170x60 Retina OLED Touch Bar Renderer (2x Supersampled)
Matches macOS ControlStrip geometry (42px key height, radius=6, #36373B keycaps, 1.5px strokes)
and returns exact (x0, x1, action_id) touch hit-boxes for evdev multitouch dispatch.
"""
import math
import os
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

WIDTH = 2170
HEIGHT = 60
SS = 2

BG = (0, 0, 0)
KEY_BG = (54, 55, 59)          # #36373B exact macOS Touch Bar keycap
KEY_ACTIVE = (74, 76, 82)
KEY_DARK = (30, 31, 34)        # #1E1F22 dark popover / well
DIVIDER = (44, 45, 50)
KEY_BLUE = (10, 132, 255)
KEY_GREEN = (48, 209, 88)
KEY_GOLD = (255, 214, 10)
KEY_RED = (255, 69, 58)
TEXT_MAIN = (255, 255, 255)
TEXT_MUTED = (165, 168, 178)

HitZone = Tuple[int, int, str]


def _load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/usr/share/fonts/truetype/inter/Inter-Medium.ttf" if bold else "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
        "/usr/share/fonts/truetype/inter/Inter-Regular.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size * SS)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_SM = _load_font(12, False)
FONT_MD = _load_font(15, True)
FONT_LG = _load_font(17, True)


def _pill(draw: ImageDraw.ImageDraw, x: int, w: int, fill=KEY_BG, radius: int = 6):
    # Exact Apple Touch Bar key height: 42px centered (y=9..51)
    y0, y1 = 9 * SS, 51 * SS
    draw.rounded_rectangle((x * SS, y0, (x + w) * SS, y1), radius=radius * SS, fill=fill)


def _text_center(draw: ImageDraw.ImageDraw, x: int, w: int, text: str, font=FONT_MD, fill=TEXT_MAIN):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    cx = (x + w / 2.0) * SS - tw / 2.0
    cy = (HEIGHT * SS) / 2.0 - th / 2.0 - 2 * SS
    draw.text((cx, cy), text, font=font, fill=fill)


def _draw_sun(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, rays: int = 8, col=TEXT_MAIN):
    cx *= SS
    cy *= SS
    r *= SS
    core = r * 0.44
    draw.ellipse((cx - core, cy - core, cx + core, cy + core), outline=col, width=int(1.6 * SS))
    for i in range(rays):
        ang = (2.0 * math.pi * i) / rays
        x0 = cx + math.cos(ang) * (r * 0.68)
        y0 = cy + math.sin(ang) * (r * 0.68)
        x1 = cx + math.cos(ang) * r
        y1 = cy + math.sin(ang) * r
        draw.line((x0, y0, x1, y1), fill=col, width=int(1.6 * SS))


def _draw_speaker(draw: ImageDraw.ImageDraw, cx: float, cy: float, muted: bool = False, col=TEXT_MAIN):
    x = cx * SS
    y = cy * SS
    draw.polygon(
        [
            (x - 9 * SS, y - 3.5 * SS),
            (x - 4 * SS, y - 3.5 * SS),
            (x + 2 * SS, y - 8.5 * SS),
            (x + 2 * SS, y + 8.5 * SS),
            (x - 4 * SS, y + 3.5 * SS),
            (x - 9 * SS, y + 3.5 * SS),
        ],
        fill=col,
    )
    if muted:
        draw.line((x - 10 * SS, y + 9 * SS, x + 10 * SS, y - 9 * SS), fill=col, width=int(1.7 * SS))
    else:
        draw.arc((x + 1 * SS, y - 5 * SS, x + 8 * SS, y + 5 * SS), start=-55, end=55, fill=col, width=int(1.6 * SS))
        draw.arc((x + 3 * SS, y - 9 * SS, x + 13 * SS, y + 9 * SS), start=-55, end=55, fill=col, width=int(1.6 * SS))


def _draw_kb_backlight(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x = cx * SS
    y = (cy + 3) * SS
    draw.line((x - 7 * SS, y, x + 7 * SS, y), fill=col, width=int(1.6 * SS))
    for ang_deg in (-150, -120, -90, -60, -30):
        ang = math.radians(ang_deg)
        x0 = x + math.cos(ang) * 6 * SS
        y0 = y + math.sin(ang) * 6 * SS
        x1 = x + math.cos(ang) * 11 * SS
        y1 = y + math.sin(ang) * 11 * SS
        draw.line((x0, y0, x1, y1), fill=col, width=int(1.6 * SS))


def _draw_mission_control(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x = cx * SS
    y = cy * SS
    w = int(1.5 * SS)
    draw.rounded_rectangle((x - 10 * SS, y - 7 * SS, x - 1 * SS, y - 1 * SS), radius=1.5 * SS, outline=col, width=w)
    draw.rounded_rectangle((x + 2 * SS, y - 7 * SS, x + 10 * SS, y + 1 * SS), radius=1.5 * SS, outline=col, width=w)
    draw.rounded_rectangle((x - 7 * SS, y + 2 * SS, x + 4 * SS, y + 8 * SS), radius=1.5 * SS, outline=col, width=w)


def _draw_launchpad(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    for r in (-5, 0, 5):
        for c in (-5, 0, 5):
            px = (cx + c) * SS
            py = (cy + r) * SS
            draw.rectangle((px - 1.3 * SS, py - 1.3 * SS, px + 1.3 * SS, py + 1.3 * SS), fill=col)


def _draw_search(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x, y = (cx - 2) * SS, (cy - 2) * SS
    r = 5.5 * SS
    draw.ellipse((x - r, y - r, x + r, y + r), outline=col, width=int(1.6 * SS))
    draw.line((x + 4 * SS, y + 4 * SS, x + 9 * SS, y + 9 * SS), fill=col, width=int(1.6 * SS))


def _draw_lock(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x, y = cx * SS, cy * SS
    draw.arc((x - 4.5 * SS, y - 9 * SS, x + 4.5 * SS, y), start=180, end=360, fill=col, width=int(1.6 * SS))
    draw.rounded_rectangle((x - 6.5 * SS, y - 2 * SS, x + 6.5 * SS, y + 8 * SS), radius=2 * SS, fill=col)


def _draw_mic(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x, y = cx * SS, cy * SS
    draw.rounded_rectangle((x - 3 * SS, y - 8 * SS, x + 3 * SS, y + 1 * SS), radius=3 * SS, outline=col, width=int(1.6 * SS))
    draw.arc((x - 6 * SS, y - 3 * SS, x + 6 * SS, y + 5 * SS), start=0, end=180, fill=col, width=int(1.6 * SS))
    draw.line((x, y + 5 * SS, x, y + 9 * SS), fill=col, width=int(1.6 * SS))


def _draw_play_icon(draw: ImageDraw.ImageDraw, cx: float, cy: float, playing: bool, col=TEXT_MAIN):
    x, y = cx * SS, cy * SS
    if playing:
        draw.rectangle((x - 5 * SS, y - 6 * SS, x - 1.5 * SS, y + 6 * SS), fill=col)
        draw.rectangle((x + 1.5 * SS, y - 6 * SS, x + 5 * SS, y + 6 * SS), fill=col)
    else:
        draw.polygon([(x - 4 * SS, y - 7 * SS), (x + 7 * SS, y), (x - 4 * SS, y + 7 * SS)], fill=col)


def _draw_collapsed_control_strip(draw: ImageDraw.ImageDraw, zones: List[HitZone], start_x: int = 1712):
    # Subtle 1px Apple-style divider before Control Strip
    draw.line((1698 * SS, 14 * SS, 1698 * SS, 46 * SS), fill=DIVIDER, width=1 * SS)

    _pill(draw, start_x, 52, fill=KEY_DARK)
    _text_center(draw, start_x, 52, "<", font=FONT_MD, fill=TEXT_MUTED)
    zones.append((start_x, start_x + 52, "mode:expanded_control"))

    x = start_x + 60
    _pill(draw, x, 90)
    _draw_sun(draw, x + 45, 30, 9.5)
    zones.append((x, x + 90, "mode:slider_overlay"))

    x += 98
    _pill(draw, x, 90)
    _draw_speaker(draw, x + 43, 30)
    zones.append((x, x + 90, "mode:slider_overlay"))

    x += 98
    _pill(draw, x, 90)
    _draw_speaker(draw, x + 45, 30, muted=True)
    zones.append((x, x + 90, "audio:mute"))

    x += 98
    _pill(draw, x, 90, fill=(28, 42, 34))
    _text_center(draw, x, 90, "dB", font=FONT_MD, fill=KEY_GREEN)
    zones.append((x, x + 90, "mode:media_decibels"))


def render_strip_with_zones(
    mode: str,
    rms_db: float = -14.2,
    peak_db: float = -5.8,
    bands_db=None,
    cpu_temp_c: float = 65.4,
    cpu_power_w: float = 14.2,
    fan0_rpm: int = 3120,
    fan1_rpm: int = 2940,
    ram_pct: int = 44,
    bright_pct: float = 0.72,
    vol_pct: float = 0.68,
) -> Tuple[Image.Image, List[HitZone]]:
    if bands_db is None:
        bands_db = [-44, -36, -27, -19, -13, -9, -14, -18, -15, -10, -16, -22, -28, -35, -42, -50]

    img = Image.new("RGB", (WIDTH * SS, HEIGHT * SS), BG)
    draw = ImageDraw.Draw(img)
    zones: List[HitZone] = []

    if mode == "expanded_control":
        _pill(draw, 10, 62, fill=KEY_ACTIVE)
        _text_center(draw, 10, 62, "X", font=FONT_SM)
        zones.append((10, 72, "mode:fn_keys"))

        slots = [
            ("sun_sm", 98, "bright:down"),
            ("sun_lg", 98, "bright:up"),
            ("mission", 106, "key:mission"),
            ("launch", 106, "key:launchpad"),
            ("kb_sm", 98, "kb:down"),
            ("kb_lg", 98, "kb:up"),
            ("prev", 98, "media:prev"),
            ("play", 106, "media:playpause"),
            ("next", 98, "media:next"),
            ("mute", 98, "audio:mute"),
            ("vol_dn", 98, "audio:down"),
            ("vol_up", 98, "audio:up"),
            ("mic", 98, "audio:mic_mute"),
            ("search", 98, "key:search"),
            ("db", 98, "mode:media_decibels"),
            ("therm", 98, "mode:thermal_a2141"),
            ("lock", 98, "sys:lock"),
        ]
        x = 88
        for kind, w, act in slots:
            bg = (28, 42, 34) if kind == "db" else KEY_BG
            _pill(draw, x, w, fill=bg)
            cx = x + w / 2.0
            if kind == "sun_sm": _draw_sun(draw, cx, 30, 7.5)
            elif kind == "sun_lg": _draw_sun(draw, cx, 30, 11)
            elif kind == "mission": _draw_mission_control(draw, cx, 30)
            elif kind == "launch": _draw_launchpad(draw, cx, 30)
            elif kind == "kb_sm": _draw_kb_backlight(draw, cx, 30, TEXT_MUTED)
            elif kind == "kb_lg": _draw_kb_backlight(draw, cx, 30, TEXT_MAIN)
            elif kind == "prev": _text_center(draw, x, w, "|<<", font=FONT_SM)
            elif kind == "play": _draw_play_icon(draw, cx, 30, playing=False)
            elif kind == "next": _text_center(draw, x, w, ">>|", font=FONT_SM)
            elif kind == "mute": _draw_speaker(draw, cx, 30, muted=True)
            elif kind == "vol_dn": _draw_speaker(draw, cx - 2, 30, muted=False, col=TEXT_MUTED)
            elif kind == "vol_up": _draw_speaker(draw, cx - 2, 30, muted=False, col=TEXT_MAIN)
            elif kind == "mic": _draw_mic(draw, cx, 30)
            elif kind == "search": _draw_search(draw, cx, 30)
            elif kind == "db": _text_center(draw, x, w, "dB", font=FONT_MD, fill=KEY_GREEN)
            elif kind == "therm": _text_center(draw, x, w, f"{cpu_temp_c:.0f}°", font=FONT_SM, fill=KEY_GOLD)
            elif kind == "lock": _draw_lock(draw, cx, 30)
            zones.append((x, x + w, act))
            x += w + 8

    elif mode == "slider_overlay":
        _pill(draw, 10, 62, fill=KEY_ACTIVE)
        _text_center(draw, 10, 62, "X", font=FONT_SM)
        zones.append((10, 72, "mode:fn_keys"))

        # Left: Brightness slider
        _pill(draw, 96, 960, fill=KEY_DARK, radius=8)
        _draw_sun(draw, 130, 30, 7.5, col=TEXT_MUTED)
        bx0, bx1 = 166, 986
        bknob = int(bx0 + max(0.0, min(1.0, bright_pct)) * (bx1 - bx0))
        draw.rounded_rectangle((bx0 * SS, 26 * SS, bx1 * SS, 34 * SS), radius=4 * SS, fill=(68, 70, 78))
        draw.rounded_rectangle((bx0 * SS, 26 * SS, bknob * SS, 34 * SS), radius=4 * SS, fill=TEXT_MAIN)
        draw.ellipse(((bknob - 13) * SS, 17 * SS, (bknob + 13) * SS, 43 * SS), fill=TEXT_MAIN)
        _draw_sun(draw, 1022, 30, 11, col=TEXT_MAIN)
        zones.append((bx0, bx1, "drag:bright"))

        # Right: Volume slider
        _pill(draw, 1086, 960, fill=KEY_DARK, radius=8)
        _draw_speaker(draw, 1122, 30, muted=True, col=TEXT_MUTED)
        vx0, vx1 = 1158, 1978
        vknob = int(vx0 + max(0.0, min(1.0, vol_pct)) * (vx1 - vx0))
        draw.rounded_rectangle((vx0 * SS, 26 * SS, vx1 * SS, 34 * SS), radius=4 * SS, fill=(68, 70, 78))
        draw.rounded_rectangle((vx0 * SS, 26 * SS, vknob * SS, 34 * SS), radius=4 * SS, fill=KEY_BLUE)
        draw.ellipse(((vknob - 13) * SS, 17 * SS, (vknob + 13) * SS, 43 * SS), fill=TEXT_MAIN)
        _draw_speaker(draw, 2010, 30, muted=False, col=TEXT_MAIN)
        zones.append((vx0, vx1, "drag:vol"))

        _pill(draw, 2072, 84, fill=KEY_BG)
        _draw_lock(draw, 2114, 30)
        zones.append((2072, 2156, "sys:lock"))

    elif mode == "typing_emoji":
        _pill(draw, 10, 80, fill=KEY_ACTIVE)
        _text_center(draw, 10, 80, "esc", font=FONT_SM)
        zones.append((10, 90, "key:esc"))

        for idx, (lbl, act) in enumerate([("B", "key:bold"), ("I", "key:italic"), ("U", "key:underline"), ("A", "key:color")]):
            x = 108 + idx * 72
            _pill(draw, x, 64)
            _text_center(draw, x, 64, lbl, font=FONT_LG, fill=KEY_GOLD if lbl == "A" else TEXT_MAIN)
            zones.append((x, x + 64, act))

        wx = 416
        for wtxt in ("hola", "gracias", "perfecto"):
            _pill(draw, wx, 186, fill=KEY_DARK)
            _text_center(draw, wx, 186, wtxt, font=FONT_MD, fill=TEXT_MAIN)
            wx += 194

        _pill(draw, 1012, 668, fill=KEY_DARK)
        ex = 1058
        for i, ec in enumerate((KEY_GOLD, KEY_RED, KEY_GREEN, KEY_BLUE, (255, 159, 10), (191, 90, 242))):
            cx, cy = ex * SS, 30 * SS
            r = 12 * SS
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ec)
            if i % 2 == 0:
                draw.ellipse((cx - 4 * SS, cy - 4 * SS, cx - 1.5 * SS, cy - 1.5 * SS), fill=(25, 25, 28))
                draw.ellipse((cx + 1.5 * SS, cy - 4 * SS, cx + 4 * SS, cy - 1.5 * SS), fill=(25, 25, 28))
                draw.arc((cx - 5 * SS, cy - 1 * SS, cx + 5 * SS, cy + 6 * SS), start=15, end=165, fill=(25, 25, 28), width=int(1.6 * SS))
            ex += 102

        _draw_collapsed_control_strip(draw, zones)

    elif mode == "browser_tabs":
        _pill(draw, 10, 80, fill=KEY_ACTIVE)
        _text_center(draw, 10, 80, "esc", font=FONT_SM)
        zones.append((10, 90, "key:esc"))
        _pill(draw, 108, 68); _text_center(draw, 108, 68, "<"); zones.append((108, 176, "browser:back"))
        _pill(draw, 184, 68); _text_center(draw, 184, 68, ">"); zones.append((184, 252, "browser:fwd"))

        _pill(draw, 268, 360, fill=KEY_DARK, radius=12)
        _draw_search(draw, 296, 30, TEXT_MUTED)
        _text_center(draw, 316, 290, "Buscar o escribir URL", font=FONT_SM, fill=TEXT_MUTED)
        zones.append((268, 628, "browser:url"))

        tx = 646
        for tname, tcol in (("GitHub", KEY_BLUE), ("YouTube", KEY_RED), ("Docs", KEY_GREEN), ("Local", KEY_GOLD)):
            _pill(draw, tx, 212, fill=KEY_BG if tname == "GitHub" else KEY_DARK)
            draw.rounded_rectangle(((tx + 10) * SS, 14 * SS, (tx + 20) * SS, 46 * SS), radius=3 * SS, fill=tcol)
            _text_center(draw, tx + 18, 184, tname, font=FONT_SM, fill=TEXT_MAIN)
            tx += 222

        _pill(draw, 1542, 68); _text_center(draw, 1542, 68, "+", font=FONT_LG); zones.append((1542, 1610, "browser:newtab"))
        _pill(draw, 1618, 68); _text_center(draw, 1618, 68, "R", font=FONT_MD); zones.append((1618, 1686, "browser:reload"))

        _draw_collapsed_control_strip(draw, zones)

    elif mode == "screenshot_bar":
        _pill(draw, 10, 62, fill=KEY_ACTIVE)
        _text_center(draw, 10, 62, "X", font=FONT_SM)
        zones.append((10, 72, "mode:fn_keys"))

        actions = [
            ("Pantalla", 205, KEY_BG, TEXT_MAIN, "shot:full"),
            ("Ventana", 205, KEY_BG, TEXT_MAIN, "shot:win"),
            ("Selección", 215, KEY_ACTIVE, TEXT_MAIN, "shot:area"),
            ("Grabar Todo", 230, KEY_BG, KEY_RED, "shot:rec"),
            ("Guardar en: Imágenes", 320, KEY_DARK, TEXT_MUTED, "shot:dir"),
            ("Capturar", 190, KEY_BLUE, TEXT_MAIN, "shot:go"),
        ]
        x = 94
        for lbl, w, bg, fg, act in actions:
            _pill(draw, x, w, fill=bg)
            _text_center(draw, x, w, lbl, font=FONT_MD, fill=fg)
            zones.append((x, x + w, act))
            x += w + 14

        _draw_collapsed_control_strip(draw, zones)

    elif mode == "media_decibels":
        _pill(draw, 10, 80, fill=KEY_ACTIVE)
        _text_center(draw, 10, 80, "esc", font=FONT_SM)
        zones.append((10, 90, "key:esc"))

        _pill(draw, 108, 300, fill=KEY_DARK)
        draw.rounded_rectangle((118 * SS, 14 * SS, 150 * SS, 46 * SS), radius=5 * SS, fill=KEY_GREEN)
        draw.text((162 * SS, 13 * SS), "Daft Punk - Veridis Quo", font=FONT_SM, fill=TEXT_MAIN)
        draw.text((162 * SS, 32 * SS), "Spotify · MPRIS2", font=FONT_SM, fill=TEXT_MUTED)

        _pill(draw, 420, 68); _text_center(draw, 420, 68, "|<<", font=FONT_SM); zones.append((420, 488, "media:prev"))
        _pill(draw, 496, 76, fill=KEY_BG); _draw_play_icon(draw, 534, 30, playing=True, col=TEXT_MAIN); zones.append((496, 572, "media:playpause"))
        _pill(draw, 580, 68); _text_center(draw, 580, 68, ">>|", font=FONT_SM); zones.append((580, 648, "media:next"))

        draw.rounded_rectangle((666 * SS, 26 * SS, 920 * SS, 34 * SS), radius=4 * SS, fill=KEY_BG)
        draw.rounded_rectangle((666 * SS, 26 * SS, 816 * SS, 34 * SS), radius=4 * SS, fill=KEY_BLUE)
        draw.ellipse((804 * SS, 18 * SS, 828 * SS, 42 * SS), fill=TEXT_MAIN)

        _pill(draw, 938, 746, fill=KEY_DARK)
        draw.text((956 * SS, 12 * SS), f"AUDIO {rms_db:+.1f} dBFS", font=FONT_MD, fill=KEY_GREEN)
        draw.text((956 * SS, 32 * SS), f"PICO {peak_db:+.1f} dB · PipeWire", font=FONT_SM, fill=TEXT_MUTED)

        bx = 1222
        for db in bands_db[:16]:
            frac = max(0.06, min(1.0, (db + 60.0) / 60.0))
            bh = int(frac * 34 * SS)
            col = KEY_GREEN if db < -12 else (KEY_GOLD if db < -3 else KEY_RED)
            draw.rounded_rectangle((bx * SS, 13 * SS, (bx + 20) * SS, 47 * SS), radius=3 * SS, fill=KEY_BG)
            draw.rounded_rectangle((bx * SS, 47 * SS - bh, (bx + 20) * SS, 47 * SS), radius=3 * SS, fill=col)
            bx += 28

        _draw_collapsed_control_strip(draw, zones)

    elif mode == "thermal_a2141":
        _pill(draw, 10, 80, fill=KEY_ACTIVE)
        _text_center(draw, 10, 80, "esc", font=FONT_SM)
        zones.append((10, 90, "key:esc"))

        tiles = [
            (f"CPU {cpu_temp_c:.1f} °C", "Core i7-9750H", 260, KEY_DARK, KEY_GREEN, "mode:thermal_a2141"),
            (f"Potencia {cpu_power_w:.1f} W", "RAPL + GPU AMD", 260, KEY_DARK, KEY_GOLD, "mode:thermal_a2141"),
            (f"Turbinas {fan0_rpm}/{fan1_rpm}", "AppleSMC RPM", 300, KEY_DARK, KEY_BLUE, "mode:thermal_a2141"),
            (f"RAM {ram_pct}% · ZSWAP", "Compresión LZ4", 260, KEY_BG, TEXT_MAIN, "mode:thermal_a2141"),
            ("Perfil: Ráfaga", "Core 0 protegido", 250, KEY_BG, KEY_GREEN, "mode:fn_keys"),
            ("Audio dB", "Ver PipeWire", 190, (28, 42, 34), KEY_GREEN, "mode:media_decibels"),
        ]
        tx = 108
        for t1, t2, w, bg, fg, act in tiles:
            _pill(draw, tx, w, fill=bg)
            draw.text(((tx + 14) * SS, 12 * SS), t1, font=FONT_MD, fill=fg)
            draw.text(((tx + 14) * SS, 32 * SS), t2, font=FONT_SM, fill=TEXT_MUTED)
            zones.append((tx, tx + w, act))
            tx += w + 12

        _draw_collapsed_control_strip(draw, zones)

    else:  # fn_keys
        _pill(draw, 10, 80, fill=KEY_ACTIVE)
        _text_center(draw, 10, 80, "esc", font=FONT_SM)
        zones.append((10, 90, "key:esc"))
        x = 106
        for i in range(1, 13):
            _pill(draw, x, 122)
            _text_center(draw, x, 122, f"F{i}", font=FONT_MD)
            zones.append((x, x + 122, f"key:f{i}"))
            x += 132
        _draw_collapsed_control_strip(draw, zones)

    return img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS), zones


def render_strip(*args, **kwargs) -> Image.Image:
    img, _ = render_strip_with_zones(*args, **kwargs)
    return img
