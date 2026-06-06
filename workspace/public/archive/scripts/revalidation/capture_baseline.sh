#!/usr/bin/env bash
set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  ./scripts/revalidation/capture_baseline.sh [--serial SERIAL] [--label LABEL] [--output DIR]

Captures the current rooted baseline into a local backup directory:
  - boot / recovery / vbmeta images
  - getprop dump
  - root identity check
  - Wi-Fi status
  - by-name symlink listing
  - manual download mode note template

Default output directory:
  backups/<label>_<timestamp>
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

# Wrap argument in single quotes for the remote shell.
# Magisk su -c on this device only honors a single-token argument,
# so we must pre-quote the whole command before adb hands it off.
sq_escape() {
    local s="${1//\'/\'\\\'\'}"
    printf "'%s'" "$s"
}

validate_by_name() {
    local path="$1"
    [[ "$path" == /dev/block/*/by-name || "$path" == /dev/block/by-name ]] || return 1
    [[ "$path" =~ ^[A-Za-z0-9_./-]+$ ]] || return 1
    [[ "$path" != *"/../"* && "$path" != *"/.." && "$path" != *"../"* ]] || return 1
}

serial=""
label="baseline"
output_dir=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--serial)
            serial="${2:-}"
            shift 2
            ;;
        -l|--label)
            label="${2:-}"
            shift 2
            ;;
        -o|--output)
            output_dir="${2:-}"
            shift 2
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
require_cmd date
require_cmd mkdir
require_cmd sha256sum

timestamp="$(date +%Y%m%d_%H%M%S)"
if [[ -z "$output_dir" ]]; then
    output_dir="backups/${label}_${timestamp}"
fi

adb_cmd=(adb)
if [[ -n "$serial" ]]; then
    adb_cmd+=(-s "$serial")
fi

"${adb_cmd[@]}" wait-for-device >/dev/null
mkdir -p "$output_dir"

find_by_name_cmd='for path in /dev/block/by-name /dev/block/bootdevice/by-name /dev/block/platform/*/by-name; do if [ -d "$path" ]; then echo "$path"; exit 0; fi; done; exit 1'
by_name="$("${adb_cmd[@]}" shell "su -c $(sq_escape "$find_by_name_cmd")" 2>/dev/null | trim_cr || true)"

if [[ -z "$by_name" ]]; then
    printf 'Unable to locate by-name partition directory via su.\n' >&2
    exit 1
fi
if ! validate_by_name "$by_name"; then
    printf 'Unsafe by-name partition directory from device: %q\n' "$by_name" >&2
    exit 1
fi

printf 'label=%s\n' "$label" > "$output_dir/manifest.txt"
printf 'timestamp=%s\n' "$timestamp" >> "$output_dir/manifest.txt"
printf 'by_name=%s\n' "$by_name" >> "$output_dir/manifest.txt"

"${adb_cmd[@]}" devices | trim_cr > "$output_dir/adb_devices.txt"
"${adb_cmd[@]}" shell getprop | trim_cr > "$output_dir/device_getprop.txt"
("${adb_cmd[@]}" shell "su -c $(sq_escape id)" || true) | trim_cr > "$output_dir/root_id.txt"
("${adb_cmd[@]}" shell cmd wifi status || true) | trim_cr > "$output_dir/wifi_status.txt"
"${adb_cmd[@]}" shell "su -c $(sq_escape "ls -l $by_name")" | trim_cr > "$output_dir/by_name_listing.txt"

parts=(boot recovery vbmeta)
for part in "${parts[@]}"; do
    if ! "${adb_cmd[@]}" shell "su -c $(sq_escape "test -e $by_name/$part")" >/dev/null 2>&1; then
        printf '%s=missing\n' "$part" >> "$output_dir/manifest.txt"
        continue
    fi

    out_file="$output_dir/${part}.img"
    printf 'Pulling %s -> %s\n' "$part" "$out_file"
    "${adb_cmd[@]}" exec-out "su -c $(sq_escape "dd if=$by_name/$part bs=4M status=none")" > "$out_file"

    if [[ ! -s "$out_file" ]]; then
        printf 'Captured image is empty: %s\n' "$out_file" >&2
        exit 1
    fi

    sha256sum "$out_file" >> "$output_dir/SHA256SUMS"
    printf '%s=%s\n' "$part" "$out_file" >> "$output_dir/manifest.txt"
done

cat > "$output_dir/download_mode_notes.txt" <<EOF
Label: $label
Timestamp: $timestamp

Fill these values from Download Mode before the next flash:
- KG:
- OEM LOCK:
- Custom binary message:
- Download mode warning/error text:

If you use this capture for Stage 1 matrix work, also note:
- AP:
- Recovery:
- Factory reset:
- Flash result:
- First boot result:
- Recovery fallback:
- ADB:
- su:
EOF

printf 'Baseline capture saved to %s\n' "$output_dir"
