#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="${ROOT_DIR}/stage3/linux_init/helpers/a90_mdm_helper_strace_wrapper.c"
BIN_DIR="${A90_EXTERNAL_TOOLS_ROOT:-${ROOT_DIR}/workspace/private/inputs/external_tools}/userland/bin"
OUT="${1:-${BIN_DIR}/a90_mdm_helper_strace_wrapper-aarch64-static}"
CHECK_FILE="$(mktemp -t a90_mdm_wrapper_dynamic_check.XXXXXX)"
trap 'rm -f "${CHECK_FILE}"' EXIT

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

mkdir -p "${BIN_DIR}" "$(dirname "${OUT}")"

aarch64-linux-gnu-gcc \
  -static \
  -Os \
  -Wall \
  -Wextra \
  -o "${OUT}" \
  "${SRC}"

aarch64-linux-gnu-strip "${OUT}"
ln -sfn "$(basename "${OUT}")" "${BIN_DIR}/a90_mdm_helper_strace_wrapper"

echo
echo "artifact: ${OUT}"
ls -lh "${OUT}"
file "${OUT}"
sha256sum "${OUT}"

if aarch64-linux-gnu-readelf -l "${OUT}" | grep -q INTERP; then
  echo "warning: INTERP segment found; binary may not be static" >&2
  exit 1
fi

aarch64-linux-gnu-readelf -d "${OUT}" >"${CHECK_FILE}" 2>&1 || true
cat "${CHECK_FILE}"
if ! grep -q "There is no dynamic section" "${CHECK_FILE}"; then
  echo "warning: dynamic section found; binary may not be static" >&2
  exit 1
fi
