#!/bin/sh
set -eu
root=$1
test -n "$LAB_OUTPUT"
mkdir -p "$LAB_OUTPUT/debs" "$LAB_OUTPUT/apt-lists"
for package in "$root"/var/cache/apt/archives/*.deb; do
 test ! -f "$package" || cp "$package" "$LAB_OUTPUT/debs/"
done
cp "$root"/var/lib/apt/lists/*InRelease "$root"/var/lib/apt/lists/*Packages* "$LAB_OUTPUT/apt-lists/"
