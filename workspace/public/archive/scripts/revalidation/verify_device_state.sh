#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  ./scripts/revalidation/verify_device_state.sh [--serial SERIAL] [--skip-wifi]

Checks the common baseline signals used across the revalidation plan:
  - adb connectivity
  - sys.boot_completed
  - build fingerprint
  - verified boot props
  - root via Magisk su
  - optional Wi-Fi status
EOF
}

require_cmd() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        printf 'Missing required command: %s\n' "$cmd" >&2
        exit 1
    fi
}

trim_cr() {
    tr -d '\r'
}

serial=""
skip_wifi=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--serial)
            serial="${2:-}"
            shift 2
            ;;
        --skip-wifi)
            skip_wifi=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown argument: %s\n' "$1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

require_cmd adb

adb_cmd=(adb)
if [[ -n "$serial" ]]; then
    adb_cmd+=(-s "$serial")
fi

"${adb_cmd[@]}" wait-for-device >/dev/null

printf '## adb devices\n'
"${adb_cmd[@]}" devices | trim_cr
printf '\n'

serial_value="$("${adb_cmd[@]}" get-serialno 2>/dev/null | trim_cr || true)"
printf 'serial: %s\n' "${serial_value:-unknown}"

props=(
    ro.product.model
    ro.build.fingerprint
    sys.boot_completed
    ro.boot.verifiedbootstate
    ro.boot.vbmeta.device_state
    ro.boot.flash.locked
    ro.boot.warranty_bit
)

printf '\n## properties\n'
for prop in "${props[@]}"; do
    value="$("${adb_cmd[@]}" shell getprop "$prop" 2>/dev/null | trim_cr || true)"
    printf '%s=%s\n' "$prop" "${value:-}"
done

printf '\n## root\n'
root_id="$("${adb_cmd[@]}" shell su -c id 2>/dev/null | trim_cr || true)"
if [[ -n "$root_id" ]]; then
    printf '%s\n' "$root_id"
else
    printf 'su unavailable or denied\n'
fi

if [[ "$skip_wifi" -eq 0 ]]; then
    printf '\n## wifi\n'
    wifi_status="$("${adb_cmd[@]}" shell cmd wifi status 2>/dev/null | trim_cr || true)"
    if [[ -n "$wifi_status" ]]; then
        printf '%s\n' "$wifi_status"
    else
        printf 'wifi status unavailable\n'
    fi
fi
