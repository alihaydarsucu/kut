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
warn() { printf '\033[1;33mWARNING:\033[0m %s\n' "$*" >&2; }
die() {
    printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2
    exit 1
}

if [[ ${EUID:-$(id -u)} -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then
        info "Administrator privileges are required; restarting with sudo..."
        exec sudo -- "$0" "$@"
    fi
    die "Run this script as root: sudo $0"
fi

[[ -f $DEFAULT_GRUB ]] || die "$DEFAULT_GRUB was not found."

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/var/backups/kut-grub/$STAMP"
mkdir -p "$BACKUP_DIR"
chmod 0700 "$BACKUP_DIR"
info "Backup before removal: $BACKUP_DIR"
cp -a "$DEFAULT_GRUB" "$BACKUP_DIR/grub.default"
if [[ -d $THEME_DIR ]]; then
    cp -a "$THEME_DIR" "$BACKUP_DIR/theme"
fi

info "Removing Kut GRUB hooks"
rm -f "$HOOK_TELEMETRY" "$HOOK_INFO" "$RENDERER"

if [[ -d $THEME_DIR ]]; then
    # Only delete a directory that is clearly ours.
    if [[ -f "$THEME_DIR/theme.txt.in" || -f "$THEME_DIR/background.png" ]]; then
        info "Removing theme directory: $THEME_DIR"
        rm -rf "$THEME_DIR"
    else
        warn "$THEME_DIR does not look like a Kut directory; leaving it untouched."
    fi
fi

info "Cleaning /etc/default/grub"
# Remove only a GRUB_THEME assignment that points at this theme.
sed -i '\|^[[:space:]]*GRUB_THEME=.*/themes/kut/theme\.txt|d' "$DEFAULT_GRUB"
sed -i '/^[[:space:]]*KUT_TELEMETRY[[:space:]]*=/d' "$DEFAULT_GRUB"
sed -i '/^[[:space:]]*KUT_TELEMETRY_DELAY[[:space:]]*=/d' "$DEFAULT_GRUB"

if [[ ${KUT_SKIP_UPDATE:-0} == 1 ]]; then
    warn "KUT_SKIP_UPDATE=1: skipping update-grub."
else
    info "Regenerating the GRUB configuration"
    if command -v update-grub >/dev/null 2>&1; then
        update-grub
    elif command -v grub-mkconfig >/dev/null 2>&1; then
        grub-mkconfig -o "$GRUB_CFG"
    else
        die "Neither update-grub nor grub-mkconfig was found."
    fi
fi

cat <<EOF

  Kut has been removed.

  Backup: $BACKUP_DIR
  GRUB_THEME and Kut telemetry settings were removed.
  GRUB_GFXMODE and GRUB_TIMEOUT_STYLE were preserved. To fully restore
  the prior configuration, compare it with the backup's grub.default file.
EOF
