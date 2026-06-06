#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT_DIR/stage3/linux_init/helpers/a90_nl80211_ro.c"
OUT="${1:-$ROOT_DIR/stage3/linux_init/helpers/a90_nl80211_ro}"

aarch64-linux-gnu-gcc -static -Os -Wall -Wextra -o "$OUT" "$SRC"
file "$OUT"
sha256sum "$OUT"
