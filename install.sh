#!/usr/bin/env bash
# Kut GRUB theme installer.
#
#   sudo ./install.sh
#
# The script is intentionally conservative: it backs up the existing theme,
# /etc/default/grub and the two Kut hooks, then changes only the settings
# this theme needs.  Set KUT_SKIP_UPDATE=1 to install files without
# running update-grub (useful in a chroot or for testing).
set -euo pipefail

THEME_NAME="kut"
THEME_DIR="/boot/grub/themes/${THEME_NAME}"
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

for required in \
    "$SCRIPT_DIR/kut/theme.txt.in" \
    "$SCRIPT_DIR/kut/background.png" \
    "$SCRIPT_DIR/tools/render_theme.sh" \
    "$SCRIPT_DIR/tools/grub.d/05_kut_telemetry" \
    "$SCRIPT_DIR/tools/grub.d/06_kut_info"; do
    [[ -f $required ]] || die "Gerekli dosya bulunamadı: $required"
done

[[ -f $DEFAULT_GRUB ]] || die "$DEFAULT_GRUB bulunamadı (GRUB kurulu değil?)"

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="/var/backups/kut-grub/$STAMP"
mkdir -p "$BACKUP_DIR"
chmod 0700 "$BACKUP_DIR"

info "Mevcut yapılandırma yedekleniyor: $BACKUP_DIR"
cp -a "$DEFAULT_GRUB" "$BACKUP_DIR/grub.default"
if [[ -d $THEME_DIR ]]; then
    cp -a "$THEME_DIR" "$BACKUP_DIR/theme"
fi
for hook in "$HOOK_TELEMETRY" "$HOOK_INFO"; do
    if [[ -f $hook ]]; then
        cp -a "$hook" "$BACKUP_DIR/$(basename "$hook")"
    fi
done

# ---------------------------------------------------------------------------
# Theme files
# ---------------------------------------------------------------------------
info "Tema dosyaları kopyalanıyor: $THEME_DIR"
rm -rf "$THEME_DIR"
install -d -m 0755 "$THEME_DIR"
cp -a "$SCRIPT_DIR/kut/." "$THEME_DIR/"
chmod -R a+rX "$THEME_DIR"

info "Tema bilgi üreticisi ve GRUB kancaları kuruluyor"
install -d -m 0755 /usr/local/sbin
install -m 0755 "$SCRIPT_DIR/tools/render_theme.sh" "$RENDERER"
install -m 0755 "$SCRIPT_DIR/tools/grub.d/05_kut_telemetry" "$HOOK_TELEMETRY"
install -m 0755 "$SCRIPT_DIR/tools/grub.d/06_kut_info" "$HOOK_INFO"

# ---------------------------------------------------------------------------
# /etc/default/grub
# ---------------------------------------------------------------------------
read_grub_var() {
    sed -n "s/^[[:space:]]*$1[[:space:]]*=[[:space:]]*//p" "$DEFAULT_GRUB" |
        tail -n 1 |
        sed -e 's/^"//' -e 's/"$//' -e "s/^'//" -e "s/'$//"
}

set_grub_var() {
    local key=$1 value=$2 escaped
    escaped=$(printf '%s' "$value" | sed 's/[&|\\]/\\&/g')
    if grep -q "^[[:space:]]*${key}[[:space:]]*=" "$DEFAULT_GRUB"; then
        sed -i "s|^[[:space:]]*${key}[[:space:]]*=.*|${key}=\"${escaped}\"|" "$DEFAULT_GRUB"
    else
        printf '%s="%s"\n' "$key" "$value" >>"$DEFAULT_GRUB"
    fi
}

add_grub_var_if_missing() {
    local key=$1 value=$2
    if ! grep -q "^[[:space:]]*${key}[[:space:]]*=" "$DEFAULT_GRUB"; then
        set_grub_var "$key" "$value"
    fi
}

info "GRUB ayarları güncelleniyor"
set_grub_var GRUB_THEME "$THEME_DIR/theme.txt"
set_grub_var GRUB_GFXMODE "1920x1080,1600x900,1366x768,1280x720,1024x768,auto"

current_timeout=$(read_grub_var GRUB_TIMEOUT)
case "$current_timeout" in
    '' | 0) set_grub_var GRUB_TIMEOUT "5" ;;
esac
set_grub_var GRUB_TIMEOUT_STYLE "menu"

add_grub_var_if_missing KUT_TELEMETRY "1"
add_grub_var_if_missing KUT_TELEMETRY_DELAY "3"

# ---------------------------------------------------------------------------
# Render the information labels from the installed machine, then regenerate
# grub.cfg. 06_kut_info repeats the render on every future update-grub.
# ---------------------------------------------------------------------------
info "Sistem bilgileri tema etiketlerine yazılıyor"
"$RENDERER" "$THEME_DIR/theme.txt.in" "$THEME_DIR/theme.txt"

if grep -qE 'text[[:space:]]*=.*@KUT_' "$THEME_DIR/theme.txt"; then
    warn "theme.txt içinde çözümlenmemiş @KUT_*@ değişkenleri var."
fi

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

    if [[ -r $GRUB_CFG ]]; then
        grep -q 'set theme=' "$GRUB_CFG" || warn "grub.cfg içinde tema ayarı görünmüyor."
        grep -q 'Kut pre-menu telemetry' "$GRUB_CFG" ||
            warn "grub.cfg içinde açılış öncesi telemetri ekranı görünmüyor."
    fi
fi

cat <<EOF

  Kut kuruldu.

  Tema       : $THEME_DIR/theme.txt
  Yedek      : $BACKUP_DIR
  Telemetri  : KUT_TELEMETRY=1, KUT_TELEMETRY_DELAY=3
  Kaldırma   : sudo $SCRIPT_DIR/uninstall.sh

  Bir sonraki açılışta yeni tema, gerçek sistem bilgileri ve
  Kut açılış telemetrisi görünecek.
EOF
