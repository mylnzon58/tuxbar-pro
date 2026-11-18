"""
tuxbar_pro/main.py — Main Event Loop & Preview Exporter for TuxBar Pro
"""
import argparse
import ctypes
import os
import sys
import time
from PIL import Image, ImageDraw

from .audio_db import PipeWireDecibelMeter
from .renderer import render_strip, WIDTH, HEIGHT
from .services import classify_app_profile, read_a2141_thermals, read_active_app, read_mpris_media


def export_all_previews(out_dir: str):
    """Render all 8 macOS-parity + Linux T2 Touch Bar strips with MacBook bezel."""
    os.makedirs(out_dir, exist_ok=True)
    specs = [
        ("strip-01-expanded-control.png", dict(mode="expanded_control")),
        ("strip-02-slider-overlay.png", dict(mode="slider_overlay")),
        ("strip-03-typing-emoji.png", dict(mode="typing_emoji")),
        ("strip-04-browser-tabs.png", dict(mode="browser_tabs")),
        ("strip-05-screenshot-bar.png", dict(mode="screenshot_bar")),
        ("strip-06-media-decibels.png", dict(mode="media_decibels", rms_db=-14.2, peak_db=-5.8)),
        ("strip-07-thermal-a2141.png", dict(mode="thermal_a2141", cpu_temp_c=65.4, cpu_power_w=14.2, fan0_rpm=3120, fan1_rpm=2940, ram_pct=44)),
        ("strip-08-fn-keys.png", dict(mode="fn_keys")),
    ]
    for fname, kwargs in specs:
        strip = render_strip(**kwargs)
        framed = Image.new("RGB", (WIDTH + 40, HEIGHT + 40), (16, 17, 20))
        draw = ImageDraw.Draw(framed)
        draw.rounded_rectangle((14, 14, WIDTH + 26, HEIGHT + 26), radius=14, outline=(52, 55, 64), width=2)
        framed.paste(strip, (20, 20))
        framed.save(os.path.join(out_dir, fname), "PNG")
    print(f"[+] Exported {len(specs)} Touch Bar strip previews to {out_dir}")


def run_live_daemon(lib_path: str):
    if not os.path.exists(lib_path):
        print(f"[-] Hardware bridge not found at {lib_path}. Build with 'make' on Linux.", file=sys.stderr)
        sys.exit(1)

    hw_lib = ctypes.CDLL(lib_path)
    hw_buf = ctypes.create_string_buffer(256)
    if hw_lib.tuxbar_hw_open(hw_buf) != 0:
        print("[-] Could not open Apple Touch Bar DRM connector (/dev/dri/card*).", file=sys.stderr)
        sys.exit(2)

    db_meter = PipeWireDecibelMeter()
    db_meter.start()

    mode = "media_db"
    try:
        while True:
            app_cls = read_active_app()
            profile = classify_app_profile(app_cls)
            media = read_mpris_media()
            therm = read_a2141_thermals()

            if media.active and media.status == "Playing":
                mode = "media_db"
            elif profile in ("browser", "ide"):
                mode = "app_control"

            img = render_strip(
                mode=mode,
                app_profile=profile,
                media_title=media.title,
                media_artist=media.artist,
                media_playing=(media.status == "Playing"),
                rms_db=db_meter.rms_db,
                peak_db=db_meter.peak_db,
                bands_db=db_meter.bands_db,
                cpu_temp_c=therm.cpu_temp_c or 65.0,
                cpu_power_w=therm.cpu_power_w or 14.0,
                fan0_rpm=therm.fan0_rpm,
                fan1_rpm=therm.fan1_rpm,
                ram_pct=therm.ram_pct,
            )
            bgra = img.convert("RGBA")
            r, g, b, a = bgra.split()
            xrgb = Image.merge("RGBA", (b, g, r, a)).tobytes()
            hw_lib.tuxbar_hw_blit(hw_buf, xrgb)
            time.sleep(0.04)  # 25 FPS smooth OLED refresh
    except KeyboardInterrupt:
        pass
    finally:
        db_meter.stop()
        hw_lib.tuxbar_hw_close(hw_buf)


def main():
    parser = argparse.ArgumentParser(description="TuxBar Pro — Dynamic Apple Touch Bar Suite for Linux T2")
    parser.add_argument("--export-previews", metavar="DIR", help="Render PNG previews of all Touch Bar modes")
    parser.add_argument("--hw-lib", default="/usr/local/lib/libtuxbar_hw.so", help="Path to libtuxbar_hw.so")
    args = parser.parse_args()

    if args.export_previews:
        export_all_previews(args.export_previews)
    else:
        run_live_daemon(args.hw_lib)


if __name__ == "__main__":
    main()
