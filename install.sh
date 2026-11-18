#!/usr/bin/env bash
# install.sh — TuxBar Pro Installer for Linux T2 (Ubuntu 24.04 LTS / Debian)
set -euo pipefail

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "[-] TuxBar Pro es para Linux (kernel linux-t2, Ubuntu 24.04 LTS)."
    exit 1
fi
if [[ "$(id -u)" -ne 0 ]]; then
    echo "[-] Ejecuta como root: sudo ./install.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REAL_USER="${SUDO_USER:-$USER}"

echo "[+] 1. Instalando dependencias (libdrm, Pillow, Inter font, playerctl, xdotool, PipeWire, brightnessctl)..."
apt-get update -qq
apt-get install -y -qq gcc pkg-config libdrm-dev python3 python3-pil playerctl xdotool pulseaudio-utils brightnessctl fonts-inter || \
apt-get install -y -qq gcc pkg-config libdrm-dev python3 python3-pil playerctl xdotool pulseaudio-utils brightnessctl

echo "[+] 2. Compilando puente DRM/KMS + evdev + uinput (libtuxbar_hw.so)..."
make -C "$SCRIPT_DIR" clean
make -C "$SCRIPT_DIR" all
install -m 755 "$SCRIPT_DIR/build/libtuxbar_hw.so" /usr/local/lib/libtuxbar_hw.so

echo "[+] 3. Instalando reglas udev de mínimo privilegio (video/input sin root en UI)..."
cp "$SCRIPT_DIR/99-tuxbar-pro.rules" /etc/udev/rules.d/99-tuxbar-pro.rules
usermod -aG video,input "$REAL_USER" 2>/dev/null || true
udevadm control --reload-rules && udevadm trigger || true

echo "[+] 4. Instalando TuxBar Pro en /opt/tuxbar-pro..."
rm -rf /opt/tuxbar-pro
mkdir -p /opt/tuxbar-pro
cp -R "$SCRIPT_DIR/tuxbar_pro" /opt/tuxbar-pro/

cat << 'EOF' > /usr/local/bin/tuxbar-pro
#!/usr/bin/env bash
export PYTHONPATH="/opt/tuxbar-pro"
exec python3 -m tuxbar_pro.main --hw-lib /usr/local/lib/libtuxbar_hw.so "$@"
EOF
chmod +x /usr/local/bin/tuxbar-pro

echo "[+] 5. Configurando servicio systemd --user (acceso nativo a PipeWire y MPRIS2)..."
mkdir -p /etc/systemd/user
cp "$SCRIPT_DIR/tuxbar-pro.service" /etc/systemd/user/tuxbar-pro.service
systemctl --global enable tuxbar-pro.service 2>/dev/null || true

echo "[OK] TuxBar Pro instalado. Cierra sesión o reinicia para activar los grupos video/input y disfrutar PipeWire dB + MPRIS2."
