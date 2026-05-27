#!/usr/bin/env bash
set -euo pipefail

STRACE_VERSION="${STRACE_VERSION:-7.0}"
STRACE_SHA256="${STRACE_SHA256:-6c92419be3f2ec560b31728a4652217c59864c8642ba7b1b3771b1b013ad074b}"
STRACE_URL="${STRACE_URL:-https://github.com/strace/strace/releases/download/v${STRACE_VERSION}/strace-${STRACE_VERSION}.tar.xz}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
WORK_DIR="${WORK_DIR:-${ROOT_DIR}/external_tools/userland}"
DOWNLOAD_DIR="${WORK_DIR}/downloads"
SRC_DIR="${WORK_DIR}/src"
BIN_DIR="${WORK_DIR}/bin"
BUILD_DIR="${WORK_DIR}/build"
PKG_DIR="${WORK_DIR}/pkg"
TARBALL="${DOWNLOAD_DIR}/strace-${STRACE_VERSION}.tar.xz"
SOURCE_DIR="${SRC_DIR}/strace-${STRACE_VERSION}"
OUT_BIN="${BIN_DIR}/strace-aarch64-static-${STRACE_VERSION}"
BUILD_LOG="${BUILD_DIR}/strace-${STRACE_VERSION}-aarch64-static.log"
SHA_OUT="${PKG_DIR}/strace-${STRACE_VERSION}-sha256.txt"
CHECK_FILE="$(mktemp -t a90_strace_dynamic_check.XXXXXX)"
trap 'rm -f "${CHECK_FILE}"' EXIT

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
need_cmd aarch64-linux-gnu-gcc
need_cmd aarch64-linux-gnu-strip
need_cmd aarch64-linux-gnu-readelf
need_cmd file

mkdir -p "${DOWNLOAD_DIR}" "${SRC_DIR}" "${BIN_DIR}" "${BUILD_DIR}" "${PKG_DIR}"

if [ ! -f "${TARBALL}" ]; then
  curl -L --fail --retry 3 -o "${TARBALL}" "${STRACE_URL}"
fi

actual_sha="$(sha256sum "${TARBALL}" | awk '{print $1}')"
if [ "${actual_sha}" != "${STRACE_SHA256}" ]; then
  echo "sha256 mismatch for ${TARBALL}" >&2
  echo "expected: ${STRACE_SHA256}" >&2
  echo "actual:   ${actual_sha}" >&2
  exit 1
fi

rm -rf "${SOURCE_DIR}"
tar -xJf "${TARBALL}" -C "${SRC_DIR}"

cd "${SOURCE_DIR}"

{
  echo "strace ${STRACE_VERSION} static aarch64 build"
  date -Is
  echo "source: ${STRACE_URL}"
  echo "source_sha256: ${STRACE_SHA256}"
  echo

  CC=aarch64-linux-gnu-gcc \
  CFLAGS="-Os" \
  LDFLAGS="-static" \
  ./configure \
    --host=aarch64-linux-gnu \
    --build="$(gcc -dumpmachine)" \
    --enable-mpers=no \
    --disable-gcc-Werror
} >"${BUILD_LOG}" 2>&1

if ! make -j"$(nproc)" >>"${BUILD_LOG}" 2>&1; then
  echo "strace build failed; tail of ${BUILD_LOG}:" >&2
  tail -120 "${BUILD_LOG}" >&2
  exit 1
fi

BUILT_BIN=""
for candidate in src/strace strace; do
  if [ -x "${candidate}" ]; then
    BUILT_BIN="${candidate}"
    break
  fi
done

if [ -z "${BUILT_BIN}" ]; then
  echo "built strace binary not found" >&2
  tail -120 "${BUILD_LOG}" >&2
  exit 1
fi

rm -f "${OUT_BIN}"
cp "${BUILT_BIN}" "${OUT_BIN}"
chmod u+w "${OUT_BIN}"
aarch64-linux-gnu-strip "${OUT_BIN}"
ln -sfn "$(basename "${OUT_BIN}")" "${BIN_DIR}/strace-aarch64-static"
sha256sum "${OUT_BIN}" "${TARBALL}" >"${SHA_OUT}"

echo
echo "artifact: ${OUT_BIN}"
echo "build log: ${BUILD_LOG}"
echo "sha256: ${SHA_OUT}"
ls -lh "${OUT_BIN}"
file "${OUT_BIN}"
sha256sum "${OUT_BIN}"

if aarch64-linux-gnu-readelf -l "${OUT_BIN}" | grep -q INTERP; then
  echo "warning: INTERP segment found; binary may not be static" >&2
  exit 1
fi

aarch64-linux-gnu-readelf -d "${OUT_BIN}" >"${CHECK_FILE}" 2>&1 || true
cat "${CHECK_FILE}"
if ! grep -q "There is no dynamic section" "${CHECK_FILE}"; then
  echo "warning: dynamic section found; binary may not be static" >&2
  exit 1
fi
