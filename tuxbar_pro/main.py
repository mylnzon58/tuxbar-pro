"""
tuxbar_pro/main.py — Main Event Loop, evdev Touch Dispatch & Preview Exporter for TuxBar Pro
"""
import argparse
import ctypes
import os
import subprocess
import sys
import time
from PIL import Image, ImageDraw

from .audio_db import PipeWireDecibelMeter
from .renderer import render_strip, render_strip_with_zones, WIDTH, HEIGHT
from .services import classify_app_profile, read_a2141_thermals, read_active_app, read_mpris_media

# Standard Linux input-event-codes.h keycodes for /dev/uinput injection
KEYCODES = {
    "esc": 1, "f1": 59, "f2": 60, "f3": 61, "f4": 62, "f5": 63, "f6": 64,
    "f7": 65, "f8": 66, "f9": 67, "f10": 68, "f11": 87, "f12": 88,
    "leftctrl": 29, "leftalt": 56, "leftmeta": 125,
    "b": 48, "i": 23, "u": 22, "t": 20, "r": 19, "l": 38,
    "left": 105, "right": 106, "space": 57,
}


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


def _run_bg(cmd):
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def dispatch_action(action: str, x: int, hw_lib, hw_buf, state: dict):
    if action.startswith("mode:"):
        state["mode"] = action.split(":", 1)[1]
        state["manual_override"] = True
        return

    if action == "drag:bright":
        pct = max(5, min(100, int(((x - 166) / (986 - 166)) * 100)))
        state["bright_pct"] = pct / 100.0
        _run_bg(["brightnessctl", "set", f"{pct}%"])
        return

    if action == "drag:vol":
        pct = max(0, min(100, int(((x - 1158) / (1978 - 1158)) * 100)))
        state["vol_pct"] = pct / 100.0
        _run_bg(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{pct}%"])
        return

    if action == "bright:down":
        state["bright_pct"] = max(0.05, state["bright_pct"] - 0.1)
        _run_bg(["brightnessctl", "set", "10%-"])
    elif action == "bright:up":
        state["bright_pct"] = min(1.0, state["bright_pct"] + 0.1)
        _run_bg(["brightnessctl", "set", "+10%"])
    elif action == "kb:down":
        _run_bg(["brightnessctl", "-d", "*kbd_backlight*", "set", "15%-"])
    elif action == "kb:up":
        _run_bg(["brightnessctl", "-d", "*kbd_backlight*", "set", "+15%"])
    elif action == "audio:mute":
        _run_bg(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
    elif action == "audio:mic_mute":
        _run_bg(["pactl", "set-source-mute", "@DEFAULT_SOURCE@", "toggle"])
    elif action == "audio:down":
        state["vol_pct"] = max(0.0, state["vol_pct"] - 0.08)
        _run_bg(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "-8%"])
    elif action == "audio:up":
        state["vol_pct"] = min(1.0, state["vol_pct"] + 0.08)
        _run_bg(["pactl", "set-sink-volume", "@DEFAULT_SINK@", "+8%"])
    elif action == "media:prev":
        _run_bg(["playerctl", "previous"])
    elif action == "media:playpause":
        _run_bg(["playerctl", "play-pause"])
    elif action == "media:next":
        _run_bg(["playerctl", "next"])
    elif action == "sys:lock":
        _run_bg(["loginctl", "lock-session"])
    elif action == "browser:back":
        hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES["left"], KEYCODES["leftalt"])
    elif action == "browser:fwd":
        hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES["right"], KEYCODES["leftalt"])
    elif action == "browser:newtab":
        hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES["t"], KEYCODES["leftctrl"])
    elif action == "browser:reload":
        hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES["r"], KEYCODES["leftctrl"])
    elif action == "browser:url":
        hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES["l"], KEYCODES["leftctrl"])
    elif action == "key:mission":
        hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES["leftmeta"], 0)
    elif action == "key:search":
        hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES["space"], KEYCODES["leftmeta"])
    elif action.startswith("key:"):
        kname = action.split(":", 1)[1]
        if kname in KEYCODES:
            hw_lib.tuxbar_hw_send_key(hw_buf, KEYCODES[kname], 0)


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

    state = {"mode": "fn_keys", "manual_override": False, "bright_pct": 0.72, "vol_pct": 0.68}
    zones = []
    touch_x = ctypes.c_int(0)
    last_service_poll = 0.0
    media = read_mpris_media()
    therm = read_a2141_thermals()

    try:
        while True:
            now = time.monotonic()
            # Poll evdev multitouch every loop (40ms = 25 Hz)
            ev_kind = hw_lib.tuxbar_hw_poll_touch(hw_buf, ctypes.byref(touch_x))
            if ev_kind in (1, 2):  # Touch down or drag
                x = touch_x.value
                for x0, x1, act in zones:
                    if x0 <= x <= x1:
                        if ev_kind == 1 or act.startswith("drag:"):
                            dispatch_action(act, x, hw_lib, hw_buf, state)
                        break

            # Poll D-Bus / sysfs every 250ms
            if (now - last_service_poll) >= 0.25:
                last_service_poll = now
                app_cls = read_active_app()
                profile = classify_app_profile(app_cls)
                media = read_mpris_media()
                therm = read_a2141_thermals()
                if not state["manual_override"]:
                    if media.active and media.status == "Playing":
                        state["mode"] = "media_decibels"
                    elif profile == "browser":
                        state["mode"] = "browser_tabs"
                    else:
                        state["mode"] = "fn_keys"

            img, zones = render_strip_with_zones(
                mode=state["mode"],
                rms_db=db_meter.rms_db,
                peak_db=db_meter.peak_db,
                bands_db=db_meter.bands_db,
                cpu_temp_c=therm.cpu_temp_c or 65.0,
                cpu_power_w=therm.cpu_power_w or 14.0,
                fan0_rpm=therm.fan0_rpm,
                fan1_rpm=therm.fan1_rpm,
                ram_pct=therm.ram_pct,
                bright_pct=state["bright_pct"],
                vol_pct=state["vol_pct"],
            )
            bgra = img.convert("RGBA")
            r, g, b, a = bgra.split()
            xrgb = Image.merge("RGBA", (b, g, r, a)).tobytes()
            hw_lib.tuxbar_hw_blit(hw_buf, xrgb)
            time.sleep(0.04)
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
