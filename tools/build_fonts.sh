#!/usr/bin/env bash
#
# Convert the source TTFs into GRUB PF2 fonts.
# GRUB automatically loads every *.pf2 file that sits next to theme.txt
# (see /etc/grub.d/00_header), so the generated files are copied straight
# into kut/.
#
# Usage: ./tools/build_fonts.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/assets/fonts"
OUT="$ROOT/kut"

command -v grub-mkfont >/dev/null || {
    echo "grub-mkfont is missing (install grub-common / grub2-tools)" >&2
    exit 1
}

# Basic Latin, Latin-1, Latin Extended-A (Turkish İ/ı/Ş/ş/Ğ/ğ/Ç/ç/Ö/ö/Ü/ü)
# plus the typographic punctuation used by the theme text.
RANGE="32-383,8211-8212,8216-8222,8226-8226,8230-8230,8482-8482"

# name:size:source
FONTS=(
    "Rajdhani UI Medium:24:Rajdhani-Medium.ttf"
    "Rajdhani UI:24:Rajdhani-Bold.ttf"
    "Rajdhani UI:48:Rajdhani-Bold.ttf"
    "Rajdhani UI Medium:16:Rajdhani-Medium.ttf"
    "Share Tech Mono:15:ShareTechMono-Regular.ttf"
    "Share Tech Mono:16:ShareTechMono-Regular.ttf"
    "Share Tech Mono:14:ShareTechMono-Regular.ttf"
)

for spec in "${FONTS[@]}"; do
    IFS=: read -r name size source <<<"$spec"
    out="$OUT/${name// /-}-${size}.pf2"
    printf '  %-30s -> %s\n' "$name $size" "$(basename "$out")"
    grub-mkfont \
        --name "$name" \
        --size "$size" \
        --range "$RANGE" \
        --output "$out" \
        "$SRC/$source"
done

echo "PF2 fonts written to $OUT"
