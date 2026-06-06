#!/usr/bin/env python3
"""Capture stock Android /linkerconfig evidence over ADB.

This tool is intentionally read-only on the Android device.  It writes local
evidence with private file handling so the captured linker namespace config can
later be copied into native init's private v232 helper root.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v233-android-linkerconfig-source")
CAPTURE_FILES = (
    "/linkerconfig/ld.config.txt",
    "/linkerconfig/apex.libraries.config.txt",
)
CAPTURE_COMMANDS = {
    "adb-devices": ["adb", "devices", "-l"],
    "id": ["shell", "id"],
    "uname": ["shell", "uname", "-a"],
    "getprop": ["shell", "getprop"],
    "mount": ["shell", "mount"],
    "linkerconfig-ls": ["shell", "ls", "-la", "/linkerconfig"],
    "linkerconfig-find": ["shell", "find", "/linkerconfig", "-maxdepth", "2", "-print"],
    "apex-ls": ["shell", "ls", "-la", "/apex"],
    "runtime-apex-ls": ["shell", "ls", "-la", "/apex/com.android.runtime"],
    "vendor-lib64-ls": ["shell", "ls", "-la", "/vendor/lib64"],
    "system-lib64-ls": ["shell", "ls", "-la", "/system/lib64"],
    "bionic-ls": ["shell", "ls", "-la", "/apex/com.android.runtime/lib64/bionic"],
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def adb_base(serial: str | None) -> list[str]:
    command = ["adb"]
    if serial:
        command.extend(["-s", serial])
    return command


def run_adb(args: argparse.Namespace, adb_args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        adb_base(args.serial) + adb_args,
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout if timeout is not None else args.timeout,
    )


def wait_for_device(args: argparse.Namespace) -> dict[str, Any]:
    deadline = time.monotonic() + args.wait_timeout
    last_output = b""
    last_error = b""

    while time.monotonic() < deadline:
        result = run_adb(args, ["devices", "-l"], timeout=min(5.0, args.timeout))
        last_output = result.stdout
        last_error = result.stderr
        lines = result.stdout.decode("utf-8", errors="replace").splitlines()
        for line in lines:
            parts = line.split()
            if len(parts) >= 2 and parts[0] != "List" and parts[1] == "device":
                if args.serial is None or parts[0] == args.serial:
                    return {
                        "ok": True,
                        "serial": parts[0],
                        "devices_text": result.stdout.decode("utf-8", errors="replace"),
                    }
        time.sleep(1.0)

    return {
        "ok": False,
        "serial": args.serial,
        "devices_text": last_output.decode("utf-8", errors="replace"),
        "stderr": last_error.decode("utf-8", errors="replace"),
    }


def capture_command(store: EvidenceStore, args: argparse.Namespace, name: str, adb_args: list[str]) -> dict[str, Any]:
    started = time.monotonic()
    result = run_adb(args, adb_args)
    duration = time.monotonic() - started
    output = result.stdout
    if result.stderr:
        output += b"\n--- stderr ---\n" + result.stderr
    path = store.write_text(f"commands/{name}.txt", output.decode("utf-8", errors="replace"))
    return {
        "name": name,
        "adb_args": adb_args,
        "rc": result.returncode,
        "ok": result.returncode == 0,
        "duration_sec": duration,
        "file": str(path.relative_to(store.run_dir)),
    }


def capture_file(store: EvidenceStore, args: argparse.Namespace, source: str) -> dict[str, Any]:
    rel_name = source.strip("/").replace("/", "__")
    started = time.monotonic()
    result = run_adb(args, ["exec-out", "cat", source], timeout=args.file_timeout)
    duration = time.monotonic() - started
    if result.returncode != 0:
        text = result.stdout + b"\n--- stderr ---\n" + result.stderr
        path = store.write_text(f"files/{rel_name}.error.txt", text.decode("utf-8", errors="replace"))
        return {
            "source": source,
            "ok": False,
            "rc": result.returncode,
            "duration_sec": duration,
            "file": str(path.relative_to(store.run_dir)),
            "size": 0,
            "sha256": None,
        }
    data = result.stdout
    path = store.path("files", rel_name)
    store.write_text(str(Path("files") / rel_name), data.decode("utf-8", errors="replace"))
    return {
        "source": source,
        "ok": True,
        "rc": result.returncode,
        "duration_sec": duration,
        "file": str(path.relative_to(store.run_dir)),
        "size": len(data),
        "sha256": sha256_bytes(data),
    }


def build_summary(manifest: dict[str, Any]) -> str:
    lines = [
        "# Android Linkerconfig Capture",
        "",
        f"- generated: `{manifest['created']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: `{manifest['reason']}`",
        f"- out_dir: `{manifest['out_dir']}`",
        "",
        "## Captured Files",
        "",
    ]
    for item in manifest["files"]:
        lines.append(
            f"- {'OK' if item['ok'] else 'FAIL'} `{item['source']}` "
            f"size={item['size']} sha256=`{item['sha256']}` file=`{item['file']}`"
        )
    lines.extend(["", "## Commands", ""])
    for item in manifest["commands"]:
        lines.append(f"- {'OK' if item['ok'] else 'FAIL'} `{item['name']}` rc={item['rc']} file=`{item['file']}`")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / DEFAULT_OUT_DIR)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--file-timeout", type=float, default=15.0)
    parser.add_argument("--wait-timeout", type=float, default=120.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    device = wait_for_device(args)
    commands: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []

    if device["ok"]:
        for name, adb_args in CAPTURE_COMMANDS.items():
            commands.append(capture_command(store, args, name, adb_args))
        for source in CAPTURE_FILES:
            files.append(capture_file(store, args, source))

    ld_config = next((item for item in files if item["source"] == "/linkerconfig/ld.config.txt"), None)
    pass_ok = bool(device["ok"] and ld_config and ld_config["ok"] and ld_config["size"] > 0)
    if pass_ok:
        decision = "android-linkerconfig-source-ready"
        reason = "captured real Android /linkerconfig/ld.config.txt"
    elif not device["ok"]:
        decision = "android-linkerconfig-capture-blocked"
        reason = "ADB device state is not device"
    else:
        decision = "android-linkerconfig-source-missing"
        reason = "Android booted but /linkerconfig/ld.config.txt was not captured"

    manifest = {
        "created": now_iso(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "out_dir": str(store.run_dir),
        "device": device,
        "commands": commands,
        "files": files,
        "host_metadata": collect_host_metadata(),
        "guardrails": [
            "ADB read-only shell/exec-out only",
            "no adb push",
            "no su writes",
            "no Wi-Fi scan/connect/link-up",
        ],
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", build_summary(manifest))
    print(f"decision={decision} pass={pass_ok} out_dir={store.run_dir}")
    print(f"reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
