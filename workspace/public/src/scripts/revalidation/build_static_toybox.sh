#!/usr/bin/env bash
set -euo pipefail

TOYBOX_VERSION="${TOYBOX_VERSION:-0.8.13}"
TOYBOX_SHA256="${TOYBOX_SHA256:-9d4c124d7d731a2db399f6278baa2b42c2e3511f610c6ad30cc3f1a52581334b}"
TOYBOX_URL="${TOYBOX_URL:-https://landley.net/toybox/downloads/toybox-${TOYBOX_VERSION}.tar.gz}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}" && while [ "${PWD}" != "/" ]; do if [ -d .git ]; then pwd; exit 0; fi; cd ..; done; exit 1)"
WORK_DIR="${WORK_DIR:-${A90_EXTERNAL_TOOLS_ROOT:-${ROOT_DIR}/workspace/private/inputs/external_tools}/userland}"
DOWNLOAD_DIR="${WORK_DIR}/downloads"
SRC_DIR="${WORK_DIR}/src"
BIN_DIR="${WORK_DIR}/bin"
BUILD_DIR="${WORK_DIR}/build"
TARBALL="${DOWNLOAD_DIR}/toybox-${TOYBOX_VERSION}.tar.gz"
SOURCE_DIR="${SRC_DIR}/toybox-${TOYBOX_VERSION}"
OUT_BIN="${BIN_DIR}/toybox-aarch64-static-${TOYBOX_VERSION}"
BUILD_LOG="${BUILD_DIR}/toybox-${TOYBOX_VERSION}-aarch64-static.log"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

need_cmd curl
need_cmd tar
need_cmd sha256sum
need_cmd make
need_cmd gcc
need_cmd python3
need_cmd aarch64-linux-gnu-gcc
need_cmd aarch64-linux-gnu-strip
need_cmd aarch64-linux-gnu-readelf
need_cmd file

mkdir -p "${DOWNLOAD_DIR}" "${SRC_DIR}" "${BIN_DIR}" "${BUILD_DIR}"

if [ ! -f "${TARBALL}" ]; then
  curl -L --fail --retry 3 -o "${TARBALL}" "${TOYBOX_URL}"
fi

actual_sha="$(sha256sum "${TARBALL}" | awk '{print $1}')"
if [ "${actual_sha}" != "${TOYBOX_SHA256}" ]; then
  echo "sha256 mismatch for ${TARBALL}" >&2
  echo "expected: ${TOYBOX_SHA256}" >&2
  echo "actual:   ${actual_sha}" >&2
  exit 1
fi

rm -rf "${SOURCE_DIR}"
tar -xzf "${TARBALL}" -C "${SRC_DIR}"

cd "${SOURCE_DIR}"

make distclean >/dev/null 2>&1 || true

{
  echo "toybox ${TOYBOX_VERSION} static aarch64 build"
  date -Is
  echo "source: ${TOYBOX_URL}"
  echo "source_sha256: ${TOYBOX_SHA256}"
  echo

  CC=aarch64-linux-gnu-gcc \
  HOSTCC=gcc \
  STRIP=aarch64-linux-gnu-strip \
  LDFLAGS=--static \
  make defconfig
} >"${BUILD_LOG}" 2>&1

python3 - <<'PY'
from pathlib import Path

path = Path(".config")
text = path.read_text()

enable = [
    "HEXDUMP",
    "IP",
    "ROUTE",
]

disable = [
    "GETTY",
    "LOGIN",
    "MKPASSWD",
    "PASSWD",
    "SU",
    "SULOGIN",
]

for key in enable:
    text = text.replace(f"# CONFIG_{key} is not set\n", f"CONFIG_{key}=y\n")
    if f"CONFIG_{key}=y\n" not in text:
        text += f"CONFIG_{key}=y\n"

for key in disable:
    text = text.replace(f"CONFIG_{key}=y\n", f"# CONFIG_{key} is not set\n")

path.write_text(text)
PY

if ! CC=aarch64-linux-gnu-gcc \
     HOSTCC=gcc \
     STRIP=aarch64-linux-gnu-strip \
     LDFLAGS=--static \
     make toybox >>"${BUILD_LOG}" 2>&1; then
  echo "toybox build failed; tail of ${BUILD_LOG}:" >&2
  tail -80 "${BUILD_LOG}" >&2
  exit 1
fi

rm -f "${OUT_BIN}"
cp toybox "${OUT_BIN}"
chmod u+w "${OUT_BIN}"
aarch64-linux-gnu-strip "${OUT_BIN}"
ln -sfn "$(basename "${OUT_BIN}")" "${BIN_DIR}/toybox-aarch64-static"

echo
echo "artifact: ${OUT_BIN}"
echo "build log: ${BUILD_LOG}"
ls -lh "${OUT_BIN}"
file "${OUT_BIN}"
sha256sum "${OUT_BIN}"

if aarch64-linux-gnu-readelf -l "${OUT_BIN}" | grep -q INTERP; then
  echo "warning: INTERP segment found; binary may not be static" >&2
  exit 1
fi

aarch64-linux-gnu-readelf -d "${OUT_BIN}" >/tmp/a90_toybox_dynamic_check.txt 2>&1 || true
cat /tmp/a90_toybox_dynamic_check.txt
if ! grep -q "There is no dynamic section" /tmp/a90_toybox_dynamic_check.txt; then
  echo "warning: dynamic section found; binary may not be static" >&2
  exit 1
fi
