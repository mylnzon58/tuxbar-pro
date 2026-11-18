"""
tuxbar_pro/renderer.py — Native 2170x60 Retina OLED Touch Bar Renderer (2x Supersampled)
Renders exact macOS-parity Touch Bar strips with geometric vector icons + Linux T2 extensions:
  1. expanded_control — Full macOS Control Strip (Brightness, Mission, Launchpad, Kb, Media, Vol, Mute, Spotlight, Lock)
  2. slider_overlay   — Interactive macOS Brightness / Volume Popover Slider with Sun/Speaker icons
  3. typing_emoji     — macOS Typing Bar: Formatting (B/I/U/Color) + Predictive Words + Quick Emoji Picker
  4. browser_tabs     — macOS Browser Bar: Back/Fwd, Search/URL Pill, Tab Thumbnails, New Tab + Control Strip
  5. screenshot_bar   — macOS Screenshot/Capture Bar (Selection, Window, Fullscreen, Record, Save To)
  6. media_decibels   — MPRIS2 Music Player + Live PipeWire dBFS Decibel Meter (-60..0 dB)
  7. thermal_a2141    — Live A2141 Thermal, Watts, Fan RPMs & RAM/ZSWAP Telemetry
  8. fn_keys          — Classic macOS Esc + F1..F12 + Collapsed Control Strip
"""
import math
import os
from PIL import Image, ImageDraw, ImageFont

WIDTH = 2170
HEIGHT = 60
SS = 2  # 2x supersampling for crisp Retina-grade OLED vector icons

BG = (0, 0, 0)
KEY_BG = (42, 43, 48)
KEY_DARK = (28, 29, 33)
KEY_BLUE = (10, 132, 255)
KEY_GREEN = (48, 209, 88)
KEY_GOLD = (255, 214, 10)
KEY_RED = (255, 69, 58)
TEXT_MAIN = (255, 255, 255)
TEXT_MUTED = (165, 168, 178)


def _load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size * SS)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_SM = _load_font(13, False)
FONT_MD = _load_font(16, True)
FONT_LG = _load_font(18, True)


def _pill(draw: ImageDraw.ImageDraw, x: int, w: int, fill=KEY_BG, radius: int = 9):
    y0, y1 = 6 * SS, (HEIGHT - 6) * SS
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
    core = r * 0.48
    draw.ellipse((cx - core, cy - core, cx + core, cy + core), outline=col, width=2 * SS)
    for i in range(rays):
        ang = (2.0 * math.pi * i) / rays
        x0 = cx + math.cos(ang) * (r * 0.68)
        y0 = cy + math.sin(ang) * (r * 0.68)
        x1 = cx + math.cos(ang) * r
        y1 = cy + math.sin(ang) * r
        draw.line((x0, y0, x1, y1), fill=col, width=2 * SS)


def _draw_speaker(draw: ImageDraw.ImageDraw, cx: float, cy: float, muted: bool = False, col=TEXT_MAIN):
    x = cx * SS
    y = cy * SS
    # Speaker body
    draw.polygon(
        [
            (x - 10 * SS, y - 4 * SS),
            (x - 4 * SS, y - 4 * SS),
            (x + 3 * SS, y - 10 * SS),
            (x + 3 * SS, y + 10 * SS),
            (x - 4 * SS, y + 4 * SS),
            (x - 10 * SS, y + 4 * SS),
        ],
        fill=col,
    )
    if muted:
        draw.line((x - 11 * SS, y + 10 * SS, x + 11 * SS, y - 10 * SS), fill=KEY_RED, width=2 * SS)
    else:
        draw.arc((x + 2 * SS, y - 6 * SS, x + 10 * SS, y + 6 * SS), start=-55, end=55, fill=col, width=2 * SS)
        draw.arc((x + 4 * SS, y - 10 * SS, x + 15 * SS, y + 10 * SS), start=-55, end=55, fill=col, width=2 * SS)


def _draw_kb_backlight(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x = cx * SS
    y = (cy + 3) * SS
    draw.line((x - 8 * SS, y, x + 8 * SS, y), fill=col, width=2 * SS)
    for ang_deg in (-150, -120, -90, -60, -30):
        ang = math.radians(ang_deg)
        x0 = x + math.cos(ang) * 7 * SS
        y0 = y + math.sin(ang) * 7 * SS
        x1 = x + math.cos(ang) * 12 * SS
        y1 = y + math.sin(ang) * 12 * SS
        draw.line((x0, y0, x1, y1), fill=col, width=2 * SS)


def _draw_mission_control(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x = cx * SS
    y = cy * SS
    draw.rounded_rectangle((x - 11 * SS, y - 8 * SS, x - 1 * SS, y - 1 * SS), radius=2 * SS, outline=col, width=2 * SS)
    draw.rounded_rectangle((x + 2 * SS, y - 8 * SS, x + 11 * SS, y + 1 * SS), radius=2 * SS, outline=col, width=2 * SS)
    draw.rounded_rectangle((x - 8 * SS, y + 2 * SS, x + 4 * SS, y + 9 * SS), radius=2 * SS, outline=col, width=2 * SS)


def _draw_launchpad(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    for r in (-6, 0, 6):
        for c in (-6, 0, 6):
            px = (cx + c) * SS
            py = (cy + r) * SS
            draw.rectangle((px - 1.5 * SS, py - 1.5 * SS, px + 1.5 * SS, py + 1.5 * SS), fill=col)


def _draw_search(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x, y = (cx - 2) * SS, (cy - 2) * SS
    r = 6 * SS
    draw.ellipse((x - r, y - r, x + r, y + r), outline=col, width=2 * SS)
    draw.line((x + 4 * SS, y + 4 * SS, x + 10 * SS, y + 10 * SS), fill=col, width=2 * SS)


def _draw_lock(draw: ImageDraw.ImageDraw, cx: float, cy: float, col=TEXT_MAIN):
    x, y = cx * SS, cy * SS
    draw.arc((x - 5 * SS, y - 10 * SS, x + 5 * SS, y), start=180, end=360, fill=col, width=2 * SS)
    draw.rounded_rectangle((x - 7 * SS, y - 2 * SS, x + 7 * SS, y + 9 * SS), radius=2 * SS, fill=col)


def _draw_play_icon(draw: ImageDraw.ImageDraw, cx: float, cy: float, playing: bool, col=TEXT_MAIN):
    x, y = cx * SS, cy * SS
    if playing:
        draw.rectangle((x - 6 * SS, y - 7 * SS, x - 2 * SS, y + 7 * SS), fill=col)
        draw.rectangle((x + 2 * SS, y - 7 * SS, x + 6 * SS, y + 7 * SS), fill=col)
    else:
        draw.polygon([(x - 5 * SS, y - 8 * SS), (x + 8 * SS, y), (x - 5 * SS, y + 8 * SS)], fill=col)


def _draw_collapsed_control_strip(draw: ImageDraw.ImageDraw, start_x: int = 1712):
    # Matches Apple's collapsed 4-button Control Strip + chevron
    _pill(draw, start_x, 56, fill=(48, 49, 56))
    _text_center(draw, start_x, 56, "<", font=FONT_MD, fill=TEXT_MAIN)

    x = start_x + 64
    _pill(draw, x, 88)
    _draw_sun(draw, x + 44, 30, 10)

    x += 96
    _pill(draw, x, 88)
    _draw_speaker(draw, x + 42, 30)

    x += 96
    _pill(draw, x, 88)
    _draw_speaker(draw, x + 44, 30, muted=True)

    x += 96
    _pill(draw, x, 92, fill=(32, 48, 38))
    _text_center(draw, x, 92, "dB", font=FONT_MD, fill=KEY_GREEN)


def render_strip(
    mode: str,
    rms_db: float = -14.2,
    peak_db: float = -5.8,
    bands_db=None,
    cpu_temp_c: float = 65.4,
    cpu_power_w: float = 14.2,
    fan0_rpm: int = 3120,
    fan1_rpm: int = 2940,
    ram_pct: int = 44,
) -> Image.Image:
    if bands_db is None:
        bands_db = [-44, -36, -27, -19, -13, -9, -14, -18, -15, -10, -16, -22, -28, -35, -42, -50]

    img = Image.new("RGB", (WIDTH * SS, HEIGHT * SS), BG)
    draw = ImageDraw.Draw(img)

    if mode == "expanded_control":
        _pill(draw, 10, 64, fill=(56, 57, 64))
        _text_center(draw, 10, 64, "X")
        slots = [
            ("sun_sm", 104), ("sun_lg", 104), ("mission", 112), ("launch", 112),
            ("kb_sm", 104), ("kb_lg", 104), ("prev", 104), ("play", 112), ("next", 104),
            ("mute", 104), ("vol_dn", 104), ("vol_up", 104), ("search", 104),
            ("db", 104), ("lock", 104),
        ]
        x = 92
        for kind, w in slots:
            bg = (32, 48, 38) if kind == "db" else KEY_BG
            _pill(draw, x, w, fill=bg)
            cx = x + w / 2.0
            if kind == "sun_sm": _draw_sun(draw, cx, 30, 8)
            elif kind == "sun_lg": _draw_sun(draw, cx, 30, 12)
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
            elif kind == "search": _draw_search(draw, cx, 30)
            elif kind == "db": _text_center(draw, x, w, "dB", font=FONT_MD, fill=KEY_GREEN)
            elif kind == "lock": _draw_lock(draw, cx, 30)
            x += w + 10

    elif mode == "slider_overlay":
        # Exact macOS Brightness & Volume slider popover layout
        _pill(draw, 10, 64, fill=(56, 57, 64))
        _text_center(draw, 10, 64, "X")

        # Left: Brightness slider (0..100%)
        _pill(draw, 100, 960, fill=KEY_DARK, radius=12)
        _draw_sun(draw, 134, 30, 8, col=TEXT_MUTED)
        draw.rounded_rectangle((170 * SS, 22 * SS, 990 * SS, 38 * SS), radius=8 * SS, fill=(58, 60, 68))
        draw.rounded_rectangle((170 * SS, 22 * SS, 760 * SS, 38 * SS), radius=8 * SS, fill=TEXT_MAIN)
        draw.ellipse((746 * SS, 14 * SS, 778 * SS, 46 * SS), fill=TEXT_MAIN)
        _draw_sun(draw, 1026, 30, 12, col=TEXT_MAIN)

        # Right: Volume slider (0..100%)
        _pill(draw, 1090, 960, fill=KEY_DARK, radius=12)
        _draw_speaker(draw, 1126, 30, muted=True, col=TEXT_MUTED)
        draw.rounded_rectangle((1162 * SS, 22 * SS, 1982 * SS, 38 * SS), radius=8 * SS, fill=(58, 60, 68))
        draw.rounded_rectangle((1162 * SS, 22 * SS, 1710 * SS, 38 * SS), radius=8 * SS, fill=KEY_BLUE)
        draw.ellipse((1696 * SS, 14 * SS, 1728 * SS, 46 * SS), fill=TEXT_MAIN)
        _draw_speaker(draw, 2014, 30, muted=False, col=TEXT_MAIN)

        _pill(draw, 2076, 84, fill=KEY_BG)
        _draw_lock(draw, 2118, 30)

    elif mode == "typing_emoji":
        # Exact macOS Typing Bar: Formatting + Predictive Text + Quick Emoji Bar
        _pill(draw, 10, 84, fill=(56, 57, 64))
        _text_center(draw, 10, 84, "esc")

        for idx, (lbl, w) in enumerate([("B", 68), ("I", 68), ("U", 68), ("A", 72)]):
            x = 110 + idx * 76
            _pill(draw, x, w)
            _text_center(draw, x, w, lbl, font=FONT_LG, fill=KEY_GOLD if lbl == "A" else TEXT_MAIN)

        # Predictive words (3-column macOS QuickType strip)
        words = ["hola", "gracias", "perfecto"]
        wx = 434
        for wtxt in words:
            _pill(draw, wx, 188, fill=KEY_DARK)
            _text_center(draw, wx, 188, wtxt, font=FONT_MD, fill=TEXT_MAIN)
            wx += 196

        # Emoji quick strip (custom vector smileys/badges for crisp cross-platform rendering)
        _pill(draw, 1030, 660, fill=KEY_DARK)
        ex = 1072
        emoji_colors = [KEY_GOLD, KEY_RED, KEY_GREEN, KEY_BLUE, (255, 159, 10), (191, 90, 242)]
        for i, ec in enumerate(emoji_colors):
            cx, cy = ex * SS, 30 * SS
            r = 14 * SS
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ec)
            if i % 2 == 0:
                draw.ellipse((cx - 5 * SS, cy - 5 * SS, cx - 2 * SS, cy - 2 * SS), fill=(25, 25, 28))
                draw.ellipse((cx + 2 * SS, cy - 5 * SS, cx + 5 * SS, cy - 2 * SS), fill=(25, 25, 28))
                draw.arc((cx - 6 * SS, cy - 2 * SS, cx + 6 * SS, cy + 7 * SS), start=15, end=165, fill=(25, 25, 28), width=2 * SS)
            else:
                draw.ellipse((cx - 5 * SS, cy - 4 * SS, cx + 5 * SS, cy + 4 * SS), fill=TEXT_MAIN)
            ex += 104

        _draw_collapsed_control_strip(draw)

    elif mode == "browser_tabs":
        # Exact macOS Safari/Chrome Touch Bar: Back/Fwd, Search Bar, Tab Thumbnails, + Tab
        _pill(draw, 10, 84, fill=(56, 57, 64))
        _text_center(draw, 10, 84, "esc")
        _pill(draw, 110, 72)
        _text_center(draw, 110, 72, "<")
        _pill(draw, 190, 72)
        _text_center(draw, 190, 72, ">")

        # Search / URL Pill
        _pill(draw, 278, 360, fill=KEY_DARK, radius=14)
        _draw_search(draw, 306, 30, TEXT_MUTED)
        _text_center(draw, 326, 300, "Buscar o escribir URL", font=FONT_SM, fill=TEXT_MUTED)

        # Tab Thumbnail Scrubber (macOS signature Safari tab preview strip)
        tabs = [("GitHub", KEY_BLUE), ("YouTube", KEY_RED), ("Docs", KEY_GREEN), ("Local", KEY_GOLD)]
        tx = 656
        for tname, tcol in tabs:
            _pill(draw, tx, 210, fill=(30, 32, 38) if tname != "GitHub" else (44, 52, 68), radius=8)
            draw.rounded_rectangle(((tx + 10) * SS, 12 * SS, (tx + 24) * SS, 48 * SS), radius=4 * SS, fill=tcol)
            _text_center(draw, tx + 22, 182, tname, font=FONT_SM, fill=TEXT_MAIN)
            tx += 220

        _pill(draw, 1546, 72)
        _text_center(draw, 1546, 72, "+", font=FONT_LG)
        _pill(draw, 1626, 72)
        _draw_sun(draw, 1662, 30, 9, col=KEY_GOLD)

        _draw_collapsed_control_strip(draw)

    elif mode == "screenshot_bar":
        # Exact macOS Cmd+Shift+5 Screenshot & Recording Bar
        _pill(draw, 10, 64, fill=(56, 57, 64))
        _text_center(draw, 10, 64, "X")

        actions = [
            ("Pantalla", 210, KEY_BG, TEXT_MAIN),
            ("Ventana", 210, KEY_BG, TEXT_MAIN),
            ("Selección", 220, (54, 62, 78), TEXT_MAIN),
            ("Grabar Todo", 240, (66, 34, 34), KEY_RED),
            ("Grabar Área", 240, (66, 34, 34), KEY_RED),
            ("Guardar en: Escritorio", 330, KEY_DARK, TEXT_MUTED),
            ("Capturar", 190, KEY_BLUE, TEXT_MAIN),
        ]
        x = 96
        for lbl, w, bg, fg in actions:
            _pill(draw, x, w, fill=bg)
            _text_center(draw, x, w, lbl, font=FONT_MD, fill=fg)
            x += w + 12

        _draw_collapsed_control_strip(draw)

    elif mode == "media_decibels":
        # MPRIS2 Media Player + Live PipeWire dBFS Decibel Meter
        _pill(draw, 10, 84, fill=(56, 57, 64))
        _text_center(draw, 10, 84, "esc")

        _pill(draw, 110, 310, fill=KEY_DARK)
        draw.rounded_rectangle((120 * SS, 12 * SS, 156 * SS, 48 * SS), radius=6 * SS, fill=KEY_GREEN)
        draw.text((168 * SS, 11 * SS), "Daft Punk - Veridis Quo", font=FONT_SM, fill=TEXT_MAIN)
        draw.text((168 * SS, 31 * SS), "Spotify · MPRIS2", font=FONT_SM, fill=TEXT_MUTED)

        _pill(draw, 432, 72)
        _text_center(draw, 432, 72, "|<<", font=FONT_SM)
        _pill(draw, 512, 82, fill=(32, 52, 40))
        _draw_play_icon(draw, 553, 30, playing=True, col=KEY_GREEN)
        _pill(draw, 602, 72)
        _text_center(draw, 602, 72, ">>|", font=FONT_SM)

        # Scrub slider
        draw.rounded_rectangle((690 * SS, 22 * SS, 940 * SS, 38 * SS), radius=8 * SS, fill=(40, 42, 48))
        draw.rounded_rectangle((690 * SS, 22 * SS, 840 * SS, 38 * SS), radius=8 * SS, fill=KEY_BLUE)
        draw.ellipse((828 * SS, 15 * SS, 856 * SS, 45 * SS), fill=TEXT_MAIN)

        # Live PipeWire dBFS Decibel Meter
        _pill(draw, 958, 738, fill=(18, 20, 26), radius=10)
        draw.text((976 * SS, 10 * SS), f"AUDIO {rms_db:+.1f} dBFS", font=FONT_MD, fill=KEY_GREEN)
        draw.text((976 * SS, 32 * SS), f"PICO {peak_db:+.1f} dB · PipeWire", font=FONT_SM, fill=TEXT_MUTED)

        bx = 1236
        for db in bands_db[:16]:
            frac = max(0.06, min(1.0, (db + 60.0) / 60.0))
            bh = int(frac * 40 * SS)
            col = KEY_GREEN if db < -12 else (KEY_GOLD if db < -3 else KEY_RED)
            draw.rounded_rectangle((bx * SS, 10 * SS, (bx + 20) * SS, 50 * SS), radius=3 * SS, fill=(32, 35, 42))
            draw.rounded_rectangle((bx * SS, 50 * SS - bh, (bx + 20) * SS, 50 * SS), radius=3 * SS, fill=col)
            bx += 28

        _draw_collapsed_control_strip(draw)

    elif mode == "thermal_a2141":
        _pill(draw, 10, 84, fill=(56, 57, 64))
        _text_center(draw, 10, 84, "esc")

        tiles = [
            (f"CPU {cpu_temp_c:.1f} °C", "Core i7-9750H", 260, (24, 42, 32), KEY_GREEN),
            (f"Potencia {cpu_power_w:.1f} W", "RAPL + GPU AMD", 260, (40, 36, 20), KEY_GOLD),
            (f"Turbinas {fan0_rpm}/{fan1_rpm}", "AppleSMC RPM", 300, (22, 34, 48), KEY_BLUE),
            (f"RAM {ram_pct}% · ZSWAP", "Compresión LZ4", 260, KEY_BG, TEXT_MAIN),
            ("Perfil: Ráfaga", "Core 0 protegido", 250, KEY_BG, KEY_GREEN),
            ("Modo dB", "Ver Audio", 190, (32, 48, 38), KEY_GREEN),
        ]
        tx = 110
        for t1, t2, w, bg, fg in tiles:
            _pill(draw, tx, w, fill=bg)
            draw.text(((tx + 16) * SS, 10 * SS), t1, font=FONT_MD, fill=fg)
            draw.text(((tx + 16) * SS, 32 * SS), t2, font=FONT_SM, fill=TEXT_MUTED)
            tx += w + 12

        _draw_collapsed_control_strip(draw)

    else:  # fn_keys
        _pill(draw, 10, 84, fill=(56, 57, 64))
        _text_center(draw, 10, 84, "esc")
        x = 108
        for i in range(1, 13):
            _pill(draw, x, 124)
            _text_center(draw, x, 124, f"F{i}", font=FONT_MD)
            x += 133
        _draw_collapsed_control_strip(draw)

    return img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
