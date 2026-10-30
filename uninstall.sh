#!/usr/bin/env bash
# Remove the Kut GRUB theme and its hooks, then rebuild grub.cfg.
#
#   sudo ./uninstall.sh
set -euo pipefail

THEME_DIR="/boot/grub/themes/kut"
RENDERER="/usr/local/sbin/kut-render-theme"
HOOK_TELEMETRY="/etc/grub.d/05_kut_telemetry"
HOOK_INFO="/etc/grub.d/06_kut_info"
DEFAULT_GRUB="/etc/default/grub"
GRUB_CFG="${GRUB_CFG:-/boot/grub/grub.cfg}"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

info() { printf '\033[1;36m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mUYARI:\033[0m %s\n' "$*" >&2; }
die() {
    printf '\033[1;31mHATA:\033[0m %s\n' "$*" >&2
    exit 1
}

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then
        info "Yönetici yetkisi gerekiyor; sudo ile yeniden çalıştırılıyor..."
        exec sudo -- "$0" "$@"
    fi
    die "Bu betiği root olarak çalıştırın: sudo $0"
fi

[[ -f $DEFAULT_GRUB ]] || die "$DEFAULT_GRUB bulunamadı."

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/var/backups/kut-grub/$STAMP"
mkdir -p "$BACKUP_DIR"
chmod 0700 "$BACKUP_DIR"
info "Kaldırma öncesi yedek: $BACKUP_DIR"
cp -a "$DEFAULT_GRUB" "$BACKUP_DIR/grub.default"
if [[ -d $THEME_DIR ]]; then
    cp -a "$THEME_DIR" "$BACKUP_DIR/theme"
fi

info "Kut GRUB kancaları kaldırılıyor"
rm -f "$HOOK_TELEMETRY" "$HOOK_INFO" "$RENDERER"

if [[ -d $THEME_DIR ]]; then
    # Only delete a directory that is clearly ours.
    if [[ -f "$THEME_DIR/theme.txt.in" || -f "$THEME_DIR/background.png" ]]; then
        info "Tema dizini kaldırılıyor: $THEME_DIR"
        rm -rf "$THEME_DIR"
    else
        warn "$THEME_DIR Kut dizinine benzemiyor; dokunulmadı."
    fi
fi

info "/etc/default/grub temizleniyor"
# Remove only a GRUB_THEME assignment that points at this theme.
sed -i '\|^[[:space:]]*GRUB_THEME=.*/themes/kut/theme\.txt|d' "$DEFAULT_GRUB"
sed -i '/^[[:space:]]*KUT_TELEMETRY[[:space:]]*=/d' "$DEFAULT_GRUB"
sed -i '/^[[:space:]]*KUT_TELEMETRY_DELAY[[:space:]]*=/d' "$DEFAULT_GRUB"

if [[ ${KUT_SKIP_UPDATE:-0} == 1 ]]; then
    warn "KUT_SKIP_UPDATE=1: update-grub atlandı."
else
    info "GRUB yapılandırması yenileniyor"
    if command -v update-grub >/dev/null 2>&1; then
        update-grub
    elif command -v grub-mkconfig >/dev/null 2>&1; then
        grub-mkconfig -o "$GRUB_CFG"
    else
        die "update-grub veya grub-mkconfig bulunamadı."
    fi
fi

cat <<EOF

  Kut kaldırıldı.

  Yedek: $BACKUP_DIR
  GRUB_THEME ve Kut telemetri ayarları kaldırıldı.
  GRUB_GFXMODE ve GRUB_TIMEOUT_STYLE korundu. Tamamen eski hale
  dönmek için yedekteki grub.default ile karşılaştırabilirsiniz.
EOF
