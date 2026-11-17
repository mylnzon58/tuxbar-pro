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

echo "[+] 1. Instalando dependencias del sistema (libdrm, Pillow, playerctl, xdotool, PipeWire)..."
apt-get update -qq
apt-get install -y -qq gcc pkg-config libdrm-dev python3 python3-pil playerctl xdotool pulseaudio-utils

echo "[+] 2. Compilando puente DRM/KMS (libtuxbar_hw.so)..."
make -C "$SCRIPT_DIR" clean
make -C "$SCRIPT_DIR" all
install -m 755 "$SCRIPT_DIR/build/libtuxbar_hw.so" /usr/local/lib/libtuxbar_hw.so

echo "[+] 3. Instalando TuxBar Pro en /opt/tuxbar-pro..."
rm -rf /opt/tuxbar-pro
mkdir -p /opt/tuxbar-pro
cp -R "$SCRIPT_DIR/tuxbar_pro" /opt/tuxbar-pro/

cat << 'EOF' > /usr/local/bin/tuxbar-pro
#!/usr/bin/env bash
exec python3 -m tuxbar_pro.main --hw-lib /usr/local/lib/libtuxbar_hw.so "$@"
EOF
chmod +x /usr/local/bin/tuxbar-pro
export PYTHONPATH="/opt/tuxbar-pro"

echo "[+] 4. Configurando servicio systemd..."
cp "$SCRIPT_DIR/tuxbar-pro.service" /etc/systemd/system/tuxbar-pro.service
systemctl daemon-reload
systemctl enable --now tuxbar-pro.service

echo "[OK] TuxBar Pro instalado y ejecutándose."
