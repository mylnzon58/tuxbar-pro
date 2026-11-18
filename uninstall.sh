#!/usr/bin/env bash
set -euo pipefail
if [[ "$(id -u)" -ne 0 ]]; then
    echo "[-] Ejecuta como root: sudo ./uninstall.sh"
    exit 1
fi
systemctl --global disable tuxbar-pro.service 2>/dev/null || true
rm -f /etc/systemd/user/tuxbar-pro.service /etc/udev/rules.d/99-tuxbar-pro.rules /usr/local/bin/tuxbar-pro /usr/local/lib/libtuxbar_hw.so
rm -rf /opt/tuxbar-pro
udevadm control --reload-rules 2>/dev/null || true
echo "[OK] TuxBar Pro desinstalado."
