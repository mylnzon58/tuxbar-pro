#!/usr/bin/env bash
set -euo pipefail
if [[ "$(id -u)" -ne 0 ]]; then
    echo "[-] Ejecuta como root: sudo ./uninstall.sh"
    exit 1
fi
systemctl disable --now tuxbar-pro.service 2>/dev/null || true
rm -f /etc/systemd/system/tuxbar-pro.service /usr/local/bin/tuxbar-pro /usr/local/lib/libtuxbar_hw.so
rm -rf /opt/tuxbar-pro
systemctl daemon-reload
echo "[OK] TuxBar Pro desinstalado."
