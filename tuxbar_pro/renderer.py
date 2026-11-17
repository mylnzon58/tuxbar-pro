"""
tuxbar_pro/renderer.py — Native 2170x60 OLED Touch Bar Renderer (Pillow)
Renders all 5 complete Touch Bar strips:
  1. app_control   — Esc + Active App Context Buttons + Control Strip
  2. media_db      — MPRIS2 Music Player + Live PipeWire dBFS Decibel Meter
  3. thermal       — A2141 CPU °C, Watts, Fan RPMs & RAM Telemetry
  4. fn_keys       — Classic Esc + F1..F12 + Control Strip
  5. expanded      — Full macOS-style Expanded Control Strip (Brightness, Mission, Kb, Media, Vol, Lock)
"""
from PIL import Image, ImageDraw, ImageFont
import os


WIDTH = 2170
HEIGHT = 60

BG = (10, 11, 14)
KEY_BG = (36, 38, 44)
KEY_ACCENT = (201, 164, 90)     # Brass Gold
KEY_BLUE = (76, 154, 240)
KEY_GREEN = (82, 183, 136)
KEY_RED = (217, 83, 79)
TEXT_MAIN = (242, 242, 247)
TEXT_MUTED = (158, 162, 174)


def _load_font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT_SM = _load_font(15, False)
FONT_MD = _load_font(18, True)
FONT_LG = _load_font(20, True)


def _pill(draw: ImageDraw.ImageDraw, x: int, w: int, label: str, fill=KEY_BG, fg=TEXT_MAIN, sub: str = None):
    y0, y1 = 6, HEIGHT - 6
    draw.rounded_rectangle((x, y0, x + w, y1), radius=10, fill=fill)
    if sub:
        draw.text((x + 14, 11), label, font=FONT_SM, fill=fg)
        draw.text((x + 14, 31), sub, font=FONT_SM, fill=TEXT_MUTED)
    else:
        bbox = draw.textbbox((0, 0), label, font=FONT_MD)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x + (w - tw) // 2, (HEIGHT - th) // 2 - 2), label, font=FONT_MD, fill=fg)


def _draw_control_strip(draw: ImageDraw.ImageDraw, start_x: int = 1656):
    items = [
        ("<", 52, (48, 50, 58), TEXT_MAIN),
        ("Brillo -/+", 110, KEY_BG, TEXT_MAIN),
        ("Vol 72%", 108, KEY_BG, TEXT_MAIN),
        ("Mute", 72, KEY_BG, TEXT_MUTED),
        ("dB", 54, (32, 62, 52), KEY_GREEN),
        ("Lock", 68, (60, 32, 32), (245, 160, 155)),
    ]
    x = start_x
    for lbl, w, bg, fg in items:
        _pill(draw, x, w, lbl, fill=bg, fg=fg)
        x += w + 8


def render_strip(
    mode: str,
    app_profile: str = "ide",
    media_title: str = "Daft Punk - Veridis Quo",
    media_artist: str = "Spotify · MPRIS2",
    media_playing: bool = True,
    rms_db: float = -18.4,
    peak_db: float = -9.2,
    bands_db=None,
    cpu_temp_c: float = 65.4,
    cpu_power_w: float = 14.2,
    fan0_rpm: int = 3120,
    fan1_rpm: int = 2940,
    ram_pct: int = 44,
) -> Image.Image:
    if bands_db is None:
        bands_db = [-42, -34, -26, -18, -14, -11, -15, -20, -16, -12, -19, -24, -29, -35, -40, -48]

    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)

    if mode == "fn_keys":
        _pill(draw, 10, 88, "esc", fill=(54, 56, 64))
        x = 112
        for i in range(1, 13):
            _pill(draw, x, 118, f"F{i}", fill=KEY_BG)
            x += 126
        _draw_control_strip(draw, start_x=1636)
        return img

    if mode == "expanded":
        _pill(draw, 10, 74, "X", fill=(54, 56, 64))
        controls = [
            ("Brillo -", 124), ("Brillo +", 124), ("Ventanas", 136), ("Apps", 116),
            ("Teclado -", 132), ("Teclado +", 132), ("Anterior", 124), ("Play/Pausa", 138),
            ("Siguiente", 128), ("Mute", 104), ("Vol -", 112), ("Vol +", 112),
            ("dB Live", 124), ("No Molestar", 148), ("Bloquear", 126)
        ]
        x = 98
        for lbl, w in controls:
            bg = (32, 62, 52) if lbl == "dB Live" else KEY_BG
            fg = KEY_GREEN if lbl == "dB Live" else TEXT_MAIN
            _pill(draw, x, w, lbl, fill=bg, fg=fg)
            x += w + 8
        return img

    if mode == "media_db":
        _pill(draw, 10, 84, "esc", fill=(54, 56, 64))
        _pill(draw, 106, 290, media_title[:24], fill=(24, 28, 36), fg=TEXT_MAIN, sub=media_artist[:26])
        _pill(draw, 408, 76, "<<", fill=KEY_BG)
        _pill(draw, 492, 92, "PAUSA" if media_playing else "PLAY", fill=(40, 70, 56), fg=KEY_GREEN)
        _pill(draw, 592, 76, ">>", fill=KEY_BG)

        # Scrub bar
        draw.rounded_rectangle((684, 18, 930, 42), radius=8, fill=(24, 26, 32))
        draw.rounded_rectangle((684, 24, 830, 36), radius=6, fill=KEY_BLUE)
        draw.ellipse((822, 18, 842, 42), fill=TEXT_MAIN)

        # PipeWire Real-time dBFS Decibel Meter (16 bands + dB numeric readout)
        draw.rounded_rectangle((946, 6, 1634, HEIGHT - 6), radius=10, fill=(18, 20, 25))
        draw.text((960, 10), f"AUDIO {rms_db:+.1f} dBFS", font=FONT_MD, fill=KEY_GREEN if peak_db < -3.0 else KEY_RED)
        draw.text((960, 33), f"PICO {peak_db:+.1f} dB · PipeWire", font=FONT_SM, fill=TEXT_MUTED)

        bar_x = 1178
        for db in bands_db[:16]:
            frac = max(0.05, min(1.0, (db + 60.0) / 60.0))
            bh = int(frac * 40)
            col = KEY_GREEN if db < -12 else (KEY_ACCENT if db < -3 else KEY_RED)
            draw.rounded_rectangle((bar_x, 10, bar_x + 20, 50), radius=3, fill=(30, 33, 40))
            draw.rounded_rectangle((bar_x, 50 - bh, bar_x + 20, 50), radius=3, fill=col)
            bar_x += 27

        _draw_control_strip(draw, start_x=1650)
        return img

    if mode == "thermal":
        _pill(draw, 10, 84, "esc", fill=(54, 56, 64))
        _pill(draw, 106, 260, f"CPU {cpu_temp_c:.1f} °C", fill=(26, 36, 30), fg=KEY_GREEN, sub="Core i7-9750H · A2141")
        _pill(draw, 378, 240, f"Consumo {cpu_power_w:.1f} W", fill=(32, 30, 22), fg=KEY_ACCENT, sub="T2 RAPL + GPU")
        _pill(draw, 630, 290, f"Turbinas {fan0_rpm} / {fan1_rpm}", fill=(22, 32, 44), fg=KEY_BLUE, sub="AppleSMC RPM en vivo")
        _pill(draw, 932, 230, f"RAM {ram_pct}% · ZSWAP", fill=KEY_BG, fg=TEXT_MAIN, sub="Compresión LZ4 activa")
        _pill(draw, 1174, 220, "Perfil: Ráfaga", fill=KEY_BG, fg=KEY_GREEN, sub="Core 0 protegido")
        _pill(draw, 1406, 228, "Ver Gráficas", fill=(44, 46, 54), fg=KEY_ACCENT)
        _draw_control_strip(draw, start_x=1650)
        return img

    # Default: app_control (Esc + Dynamic App Context + Control Strip)
    _pill(draw, 10, 84, "esc", fill=(54, 56, 64))
    if app_profile == "browser":
        buttons = [
            ("<< Atrás", 145), ("Adelante >>", 160), ("Recargar", 145),
            ("+ Pestaña", 165), ("Buscar", 140), ("Silenciar", 150),
            ("Captura", 150), ("Modo dB", 145), ("Modo CPU", 155)
        ]
        tag_bg = (26, 36, 52)
    else:  # IDE / Terminal
        buttons = [
            ("Ejecutar", 150), ("Compilar", 155), ("Debug", 135),
            ("Comentar", 155), ("Buscar", 140), ("Terminal", 155),
            ("Git Status", 165), ("Audio dB", 150), ("Térmica", 145)
        ]
        tag_bg = (34, 32, 46)

    x = 110
    for lbl, w in buttons:
        bg = (32, 62, 52) if "dB" in lbl else tag_bg
        fg = KEY_GREEN if "dB" in lbl else TEXT_MAIN
        _pill(draw, x, w, lbl, fill=bg, fg=fg)
        x += w + 12

    _draw_control_strip(draw, start_x=1650)
    return img
