#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="${ROOT_DIR}/stage3/linux_init/a90_usbnet.c"
BIN_DIR="${A90_EXTERNAL_TOOLS_ROOT:-${ROOT_DIR}/workspace/private/inputs/external_tools}/userland/bin"
OUT_BIN="${BIN_DIR}/a90_usbnet-aarch64-static"

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

mkdir -p "${BIN_DIR}"

aarch64-linux-gnu-gcc \
  -static \
  -Os \
  -Wall \
  -Wextra \
  -o "${OUT_BIN}" \
  "${SRC}"

aarch64-linux-gnu-strip "${OUT_BIN}"
ln -sfn "$(basename "${OUT_BIN}")" "${BIN_DIR}/a90_usbnet"

echo
echo "artifact: ${OUT_BIN}"
ls -lh "${OUT_BIN}"
file "${OUT_BIN}"
sha256sum "${OUT_BIN}"

if aarch64-linux-gnu-readelf -l "${OUT_BIN}" | grep -q INTERP; then
  echo "warning: INTERP segment found; binary may not be static" >&2
  exit 1
fi

aarch64-linux-gnu-readelf -d "${OUT_BIN}" >/tmp/a90_usbnet_dynamic_check.txt 2>&1 || true
cat /tmp/a90_usbnet_dynamic_check.txt
if ! grep -q "There is no dynamic section" /tmp/a90_usbnet_dynamic_check.txt; then
  echo "warning: dynamic section found; binary may not be static" >&2
  exit 1
fi
