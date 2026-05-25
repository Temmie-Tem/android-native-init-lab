#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "$0")/../.." && pwd)"
src="$repo_root/stage3/linux_init/helpers/a90_servnotif_listener_probe.c"
out="${1:-$repo_root/tmp/wifi/v833-servnotif-helper-build/a90_servnotif_listener_probe}"

mkdir -p "$(dirname "$out")"

aarch64-linux-gnu-gcc -static -Os -Wall -Wextra \
  -o "$out" "$src"

aarch64-linux-gnu-strip "$out"

file "$out"
aarch64-linux-gnu-readelf -d "$out" | grep 'There is no dynamic section'
sha256sum "$out"
