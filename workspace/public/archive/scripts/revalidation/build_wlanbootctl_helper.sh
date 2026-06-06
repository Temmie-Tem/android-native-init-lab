#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="${ROOT_DIR}/stage3/linux_init/helpers/a90_wlanbootctl.c"
OUT="${1:-${ROOT_DIR}/stage3/linux_init/helpers/a90_wlanbootctl}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

need_cmd aarch64-linux-gnu-gcc
need_cmd aarch64-linux-gnu-strip
need_cmd aarch64-linux-gnu-readelf
need_cmd sha256sum
need_cmd file

aarch64-linux-gnu-gcc \
  -static \
  -Os \
  -Wall \
  -Wextra \
  -o "${OUT}" \
  "${SRC}"

aarch64-linux-gnu-strip "${OUT}"

echo
echo "artifact: ${OUT}"
ls -lh "${OUT}"
file "${OUT}"
sha256sum "${OUT}"

if aarch64-linux-gnu-readelf -l "${OUT}" | grep -q INTERP; then
  echo "warning: INTERP segment found; binary may not be static" >&2
  exit 1
fi

aarch64-linux-gnu-readelf -d "${OUT}" >/tmp/a90_wlanbootctl_dynamic_check.txt 2>&1 || true
cat /tmp/a90_wlanbootctl_dynamic_check.txt
if ! grep -q "There is no dynamic section" /tmp/a90_wlanbootctl_dynamic_check.txt; then
  echo "warning: dynamic section found; binary may not be static" >&2
  exit 1
fi
