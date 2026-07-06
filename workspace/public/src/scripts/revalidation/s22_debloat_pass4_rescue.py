#!/usr/bin/env python3
"""Restore S22+ pass4 user-0 package state from TWRP/ADB.

This is a host-side recovery helper for the 2026-07-06 S22+ debloat pass4
experiment. It edits only `/data/system/users/0/package-restrictions.xml` after
pulling a backup. It does not write partitions.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET


PASS4_PACKAGES = [
    "com.android.bluetooth",
    "com.android.cameraextensions",
    "com.android.mtp",
    "com.android.uwb.resources",
    "com.google.android.documentsui",
    "com.qualcomm.location",
    "com.samsung.android.app.telephonyui.esimclient",
    "com.samsung.android.nfc.resources.korea",
    "com.samsung.android.providers.factory",
    "com.samsung.android.wallpaper.res",
    "com.skms.android.agent",
    "com.skp.seio",
    "com.skt.prod.dialer",
]


REMOTE = "/data/system/users/0/package-restrictions.xml"


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        cmd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if check and proc.returncode != 0:
        raise SystemExit(f"command failed rc={proc.returncode}: {' '.join(cmd)}\n{proc.stdout}")
    return proc


def adb(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["adb", *args], check=check)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="push the edited XML back to the device")
    ap.add_argument("--workdir", default="/tmp/s22_pass4_rescue")
    ns = ap.parse_args()

    workdir = pathlib.Path(ns.workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    stamp = _dt.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    pulled = workdir / f"package-restrictions.{stamp}.xml"
    edited = workdir / f"package-restrictions.{stamp}.edited.xml"

    state = adb(["get-state"], check=False).stdout.strip()
    if state != "device":
        raise SystemExit(f"adb state is {state!r}; need a TWRP/recovery shell with /data mounted")

    test = adb(["shell", "test", "-f", REMOTE], check=False)
    if test.returncode != 0:
        raise SystemExit(f"{REMOTE} not readable; mount/decrypt /data in TWRP first")

    adb(["pull", REMOTE, str(pulled)])
    root = ET.parse(pulled)
    changed: list[str] = []
    seen: set[str] = set()

    for pkg in root.findall(".//pkg"):
        name = pkg.get("name")
        if name not in PASS4_PACKAGES:
            continue
        seen.add(name)
        before = dict(pkg.attrib)
        pkg.set("installed", "true")
        pkg.attrib.pop("hidden", None)
        if dict(pkg.attrib) != before:
            changed.append(name)

    root.write(edited, encoding="utf-8", xml_declaration=True)

    print(f"backup={pulled}")
    print(f"edited={edited}")
    print(f"seen={len(seen)} changed={len(changed)}")
    for name in PASS4_PACKAGES:
        marker = "changed" if name in changed else ("seen" if name in seen else "not-in-xml")
        print(f"{marker}: {name}")

    if not ns.apply:
        print("dry-run only; rerun with --apply to push")
        return 0

    remote_backup = f"{REMOTE}.codex-pass4-rescue-{stamp}.bak"
    adb(["shell", "cp", "-p", REMOTE, remote_backup])
    adb(["push", str(edited), REMOTE])
    adb(["shell", "chown", "1000:1000", REMOTE], check=False)
    adb(["shell", "chmod", "0600", REMOTE], check=False)
    print(f"remote_backup={remote_backup}")
    print("pushed edited package restrictions; reboot system now")
    return 0


if __name__ == "__main__":
    sys.exit(main())
