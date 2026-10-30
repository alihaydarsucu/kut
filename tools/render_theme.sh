#!/usr/bin/env bash
# Render kut/theme.txt.in into a GRUB theme with real machine values.
#
# Usage: tools/render_theme.sh [--generic] TEMPLATE OUTPUT
#
# install.sh and /etc/grub.d/06_kut_info call this on every update-grub
# so the information labels never go stale. --generic writes portable
# placeholders and is useful for tests or for building on another machine.
set -euo pipefail

generic=0
if [[ ${1:-} == "--generic" ]]; then
    generic=1
    shift
fi

if [[ $# -ne 2 ]]; then
    echo "usage: $0 [--generic] TEMPLATE OUTPUT" >&2
    exit 2
fi

template=$1
output=$2

if [[ ! -r $template ]]; then
    echo "render_theme: cannot read template: $template" >&2
    exit 1
fi

# A value must never be able to break out of the double-quoted GRUB string or
# inject sed syntax. Keep the display on one line and neutralise quotes,
# backslashes and the sed delimiter.
clean() {
    printf '%s' "$1" |
        tr '\n\r\t' '   ' |
        sed -e 's/"/'\''/g' -e 's/[[:space:]]\+/ /g' -e 's/^ //' -e 's/ $//'
}

sed_escape() {
    printf '%s' "$1" | sed -e 's/[&|\\]/\\&/g'
}

first_value() {
    # $1 = file, $2 = key prefix ("KEY=")
    sed -n "s/^$2//p" "$1" 2>/dev/null | head -n 1
}

distro="GNU/LINUX"
kernel="LINUX"
memory="SYSTEM"
firmware="UEFI"
hostname_value="KUT"
cpu="KUT CORE"

if [[ $generic -eq 0 ]]; then
    if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        distro=${PRETTY_NAME:-${NAME:-GNU/LINUX}}
    fi

    kernel=$(uname -r 2>/dev/null || printf 'LINUX')

    if [[ -r /proc/meminfo ]]; then
        mem_kb=$(awk '/^MemTotal:/ {print $2; exit}' /proc/meminfo)
        if [[ -n ${mem_kb:-} && $mem_kb -gt 0 ]]; then
            if ((mem_kb >= 1048576)); then
                memory="$(((mem_kb + 524288) / 1048576)) GB"
            else
                memory="$(((mem_kb + 512) / 1024)) MB"
            fi
        fi
    fi

    if [[ -d /sys/firmware/efi ]]; then
        firmware="UEFI"
    else
        firmware="BIOS"
    fi

    hostname_value=$(hostname 2>/dev/null || cat /proc/sys/kernel/hostname 2>/dev/null || printf 'KUT')

    if [[ -r /proc/cpuinfo ]]; then
        cpu=$(awk -F': ' '/model name|Hardware|Processor/ {gsub(/^[ \t]+|[ \t]+$/, "", $2); print $2; exit}' /proc/cpuinfo)
    fi
    if [[ -z ${cpu:-} ]]; then
        cpu="UNKNOWN CPU"
    fi
fi

# The information band is deliberately compact; overlong CPU strings would
# run outside the safe zone at 1024x768 and 800x600.
distro=$(clean "$distro")
kernel=$(clean "$kernel")
memory=$(clean "$memory")
firmware=$(clean "$firmware")
hostname_value=$(clean "$hostname_value")
cpu=$(clean "$cpu" | cut -c1-42)

tmp=$(mktemp "${output}.XXXXXX")
trap 'rm -f "$tmp"' EXIT

sed \
    -e "s|@KUT_DISTRO@|$(sed_escape "$distro")|g" \
    -e "s|@KUT_KERNEL@|$(sed_escape "$kernel")|g" \
    -e "s|@KUT_MEMORY@|$(sed_escape "$memory")|g" \
    -e "s|@KUT_FIRMWARE@|$(sed_escape "$firmware")|g" \
    -e "s|@KUT_HOST@|$(sed_escape "$hostname_value")|g" \
    -e "s|@KUT_CPU@|$(sed_escape "$cpu")|g" \
    "$template" >"$tmp"

chmod 0644 "$tmp"
mv -f "$tmp" "$output"
trap - EXIT
printf 'render_theme: wrote %s (%s, kernel %s, %s RAM, %s)\n' \
    "$output" "$distro" "$kernel" "$memory" "$firmware"
