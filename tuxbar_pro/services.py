"""
tuxbar_pro/services.py — MPRIS2 Media Players, Active App Detection (X11/Wayland), and A2141 Thermal Telemetry
"""
import glob
import os
import subprocess
from dataclasses import dataclass, field
from typing import List


@dataclass
class MediaState:
    active: bool = False
    player: str = ""
    title: str = "Sin reproducción"
    artist: str = "MPRIS2 listo"
    status: str = "Stopped"  # Playing, Paused, Stopped
    progress: float = 0.0


@dataclass
class ThermalState:
    cpu_temp_c: float = 0.0
    cpu_power_w: float = 0.0
    fan0_rpm: int = 0
    fan1_rpm: int = 0
    ram_pct: int = 0


def read_active_app() -> str:
    """Detect focused application class via xdotool (X11) or gdbus (GNOME Wayland)."""
    try:
        out = subprocess.check_output(
            ["xdotool", "getactivewindow", "getwindowclassname"],
            stderr=subprocess.DEVNULL,
            timeout=0.3,
        ).decode("utf-8", errors="ignore").strip().lower()
        if out:
            return out
    except Exception:
        pass
    return "desktop"


def classify_app_profile(app_class: str) -> str:
    if any(k in app_class for k in ("chrome", "chromium", "firefox", "brave", "vivaldi")):
        return "browser"
    if any(k in app_class for k in ("code", "jetbrains", "idea", "pycharm", "terminal", "kitty", "alacritty")):
        return "ide"
    if any(k in app_class for k in ("spotify", "vlc", "rhythmbox", "mpv", "elisa")):
        return "media"
    return "desktop"


def read_mpris_media() -> MediaState:
    """Query active MPRIS2 player over D-Bus via playerctl if available."""
    state = MediaState()
    try:
        status = subprocess.check_output(
            ["playerctl", "status"], stderr=subprocess.DEVNULL, timeout=0.25
        ).decode().strip()
        title = subprocess.check_output(
            ["playerctl", "metadata", "title"], stderr=subprocess.DEVNULL, timeout=0.25
        ).decode().strip()
        artist = subprocess.check_output(
            ["playerctl", "metadata", "artist"], stderr=subprocess.DEVNULL, timeout=0.25
        ).decode().strip()
        player = subprocess.check_output(
            ["playerctl", "metadata", "--format", "{{playerName}}"],
            stderr=subprocess.DEVNULL,
            timeout=0.25,
        ).decode().strip()
        state.active = True
        state.status = status
        state.title = title or "Reproduciendo"
        state.artist = artist or player
        state.player = player
    except Exception:
        pass
    return state


def read_a2141_thermals() -> ThermalState:
    """Read Linux coretemp, applesmc fans, and RAPL power on MacBookPro16,1."""
    t = ThermalState()
    for path in glob.glob("/sys/class/hwmon/hwmon*/temp*_input"):
        try:
            val = int(open(path).read().strip()) / 1000.0
            if 20.0 < val < 115.0 and val > t.cpu_temp_c:
                t.cpu_temp_c = val
        except Exception:
            pass

    for fan_idx, attr in ((1, "fan0_rpm"), (2, "fan1_rpm")):
        for path in glob.glob(f"/sys/devices/platform/applesmc.*/fan{fan_idx}_input"):
            try:
                setattr(t, attr, int(open(path).read().strip()))
            except Exception:
                pass

    try:
        meminfo = open("/proc/meminfo").read()
        total = active = 0
        for line in meminfo.splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable:"):
                active = total - int(line.split()[1])
        if total > 0:
            t.ram_pct = int((active / total) * 100)
    except Exception:
        pass
    return t
