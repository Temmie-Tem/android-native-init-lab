#!/usr/bin/env bash
set -euo pipefail

BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
BUSYBOX_SHA256="${BUSYBOX_SHA256:-b8cc24c9574d809e7279c3be349795c5d5ceb6fdf19ca709f80cde50e47de314}"
BUSYBOX_URL="${BUSYBOX_URL:-https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${WORK_DIR:-${A90_EXTERNAL_TOOLS_ROOT:-${ROOT_DIR}/workspace/private/inputs/external_tools}/userland}"
DOWNLOAD_DIR="${WORK_DIR}/downloads"
SRC_DIR="${WORK_DIR}/src"
BIN_DIR="${WORK_DIR}/bin"
BUILD_DIR="${WORK_DIR}/build"
PKG_DIR="${WORK_DIR}/pkg"
TARBALL="${DOWNLOAD_DIR}/busybox-${BUSYBOX_VERSION}.tar.bz2"
SOURCE_DIR="${SRC_DIR}/busybox-${BUSYBOX_VERSION}"
OUT_BIN="${BIN_DIR}/busybox-aarch64-static-${BUSYBOX_VERSION}"
BUILD_LOG="${BUILD_DIR}/busybox-${BUSYBOX_VERSION}-aarch64-static.log"
CONFIG_OUT="${PKG_DIR}/busybox-${BUSYBOX_VERSION}-config"
SHA_OUT="${PKG_DIR}/busybox-${BUSYBOX_VERSION}-sha256.txt"

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
need_cmd mktemp
need_cmd aarch64-linux-gnu-gcc
need_cmd aarch64-linux-gnu-strip
need_cmd aarch64-linux-gnu-readelf

DYNAMIC_CHECK="$(mktemp -t a90_busybox_dynamic_check.XXXXXX)"
trap 'rm -f "$DYNAMIC_CHECK"' EXIT
need_cmd file

mkdir -p "${DOWNLOAD_DIR}" "${SRC_DIR}" "${BIN_DIR}" "${BUILD_DIR}" "${PKG_DIR}"

if [ ! -f "${TARBALL}" ]; then
  curl -L --fail --retry 3 -o "${TARBALL}" "${BUSYBOX_URL}"
fi

actual_sha="$(sha256sum "${TARBALL}" | awk '{print $1}')"
if [ "${actual_sha}" != "${BUSYBOX_SHA256}" ]; then
  echo "sha256 mismatch for ${TARBALL}" >&2
  echo "expected: ${BUSYBOX_SHA256}" >&2
  echo "actual:   ${actual_sha}" >&2
  exit 1
fi

rm -rf "${SOURCE_DIR}"
tar -xjf "${TARBALL}" -C "${SRC_DIR}"

cd "${SOURCE_DIR}"

make distclean >/dev/null 2>&1 || true

{
  echo "busybox ${BUSYBOX_VERSION} static aarch64 build"
  date -Is
  echo "source: ${BUSYBOX_URL}"
  echo "source_sha256: ${BUSYBOX_SHA256}"
  echo

  make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
} >"${BUILD_LOG}" 2>&1

python3 - <<'PY'
from pathlib import Path

path = Path(".config")
text = path.read_text()

enable = [
    "STATIC",
    "ASH",
    "SH_IS_ASH",
    "LS",
    "CAT",
    "MOUNT",
    "PS",
    "KILL",
    "DMESG",
    "UNAME",
    "ECHO",
    "IFCONFIG",
    "IP",
]

disable = [
    "FEATURE_SH_STANDALONE",
    "LOGIN",
    "PASSWD",
    "SU",
    "SULOGIN",
    "ADDUSER",
    "ADDGROUP",
    "DELUSER",
    "DELGROUP",
    "GETTY",
    "TC",
]

for key in enable:
    text = text.replace(f"# CONFIG_{key} is not set\n", f"CONFIG_{key}=y\n")
    if f"CONFIG_{key}=y\n" not in text:
        text += f"CONFIG_{key}=y\n"

for key in disable:
    text = text.replace(f"CONFIG_{key}=y\n", f"# CONFIG_{key} is not set\n")

path.write_text(text)
PY

if ! make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- oldconfig >>"${BUILD_LOG}" 2>&1; then
  echo "busybox oldconfig failed; tail of ${BUILD_LOG}:" >&2
  tail -80 "${BUILD_LOG}" >&2
  exit 1
fi

if ! make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- busybox >>"${BUILD_LOG}" 2>&1; then
  echo "busybox build failed; tail of ${BUILD_LOG}:" >&2
  tail -80 "${BUILD_LOG}" >&2
  exit 1
fi

rm -f "${OUT_BIN}"
cp busybox "${OUT_BIN}"
chmod u+w "${OUT_BIN}"
aarch64-linux-gnu-strip "${OUT_BIN}"
ln -sfn "$(basename "${OUT_BIN}")" "${BIN_DIR}/busybox-aarch64-static"
cp .config "${CONFIG_OUT}"
sha256sum "${OUT_BIN}" "${TARBALL}" >"${SHA_OUT}"

echo
echo "artifact: ${OUT_BIN}"
echo "build log: ${BUILD_LOG}"
echo "config: ${CONFIG_OUT}"
echo "sha256: ${SHA_OUT}"
ls -lh "${OUT_BIN}"
file "${OUT_BIN}"
sha256sum "${OUT_BIN}"

if aarch64-linux-gnu-readelf -l "${OUT_BIN}" | grep -q INTERP; then
  echo "warning: INTERP segment found; binary may not be static" >&2
  exit 1
fi

aarch64-linux-gnu-readelf -d "${OUT_BIN}" >"${DYNAMIC_CHECK}" 2>&1 || true
cat "${DYNAMIC_CHECK}"
if ! grep -q "There is no dynamic section" "${DYNAMIC_CHECK}"; then
  echo "warning: dynamic section found; binary may not be static" >&2
  exit 1
fi
