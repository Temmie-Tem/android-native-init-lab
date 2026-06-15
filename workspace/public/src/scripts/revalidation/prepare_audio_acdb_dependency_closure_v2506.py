#!/usr/bin/env python3
"""Prepare the V2506 private ACDB dependency closure from the stock vendor ext4 image.

This is a host-only helper.  It extracts proprietary vendor libraries into
workspace/private so the own-process ACDB GET runner can stage them beside the
ARM32 helper.  It never commits or writes vendor binaries to public paths.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[5]
VENDOR_IMAGE = ROOT / "workspace/private/tmp/vendor-spl-check-20260612/vendor.raw.ext4"
DEFAULT_OUT_DIR = ROOT / "workspace/private/inputs/audio/acdb-deps-v2506/vendor-lib"
DEFAULT_MANIFEST = ROOT / "workspace/private/inputs/audio/acdb-deps-v2506/manifest.json"
VENDOR_LIBS = (
    "libaudcal.so",
    "libdiag.so",
    "libacdb-fts.so",
    "libacdbrtac.so",
    "libadiertac.so",
    "libacdbloader.so",
)
EXPECTED_SYSTEM_RUNTIME_LIBS = (
    "libtinyalsa.so",
    "libion.so",
    "libcutils.so",
    "libutils.so",
    "liblog.so",
    "libc++.so",
)


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def run(command: list[str], *, timeout: float = 30.0, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(
            f"command failed rc={completed.returncode}: {' '.join(command)}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def readelf_needed(path: Path, readelf: str) -> list[str]:
    completed = run([readelf, "-d", str(path)], timeout=30.0, check=False)
    deps: list[str] = []
    for line in completed.stdout.splitlines():
        if "NEEDED" in line and "[" in line and "]" in line:
            deps.append(line.split("[", 1)[1].split("]", 1)[0])
    return sorted(set(deps))


def debugfs_dump(image: Path, source: str, destination: Path, debugfs: str) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        destination.unlink()
    completed = run([debugfs, "-R", f"dump -p {source} {destination}", str(image)], timeout=60.0, check=False)
    state: dict[str, Any] = {
        "source": source,
        "destination": rel(destination),
        "rc": completed.returncode,
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
        "exists": destination.exists(),
    }
    if destination.exists():
        st = destination.stat()
        state.update({
            "size": st.st_size,
            "mode": oct(st.st_mode & 0o777),
            "sha256": sha256_file(destination),
        })
    state["ok"] = bool(completed.returncode == 0 and destination.exists() and destination.stat().st_size > 0)
    return state


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    image = args.vendor_image
    out_dir = args.out_dir
    debugfs_path = shutil.which(args.debugfs) or args.debugfs
    readelf_path = shutil.which(args.readelf) or args.readelf
    payload: dict[str, Any] = {
        "run_id": "V2506",
        "decision": "v2506-acdb-dependency-closure-host-only",
        "created_at": now_iso(),
        "host_only": True,
        "device_action": "none",
        "vendor_image": {"path": rel(image), "exists": image.exists()},
        "out_dir": rel(out_dir),
        "manifest_path": rel(args.manifest_path),
        "vendor_libs": list(VENDOR_LIBS),
        "expected_system_runtime_libs": list(EXPECTED_SYSTEM_RUNTIME_LIBS),
        "tools": {"debugfs": debugfs_path, "readelf": readelf_path},
        "extract": [],
        "ok": False,
    }
    if image.exists():
        payload["vendor_image"].update({"size": image.stat().st_size, "sha256": sha256_file(image)})
    if args.extract:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name in VENDOR_LIBS:
            state = debugfs_dump(image, f"/lib/{name}", out_dir / name, debugfs_path)
            if state.get("ok"):
                state["needed"] = readelf_needed(out_dir / name, readelf_path)
            payload["extract"].append({"name": name, **state})
    else:
        for name in VENDOR_LIBS:
            path = out_dir / name
            state: dict[str, Any] = {"name": name, "destination": rel(path), "exists": path.exists()}
            if path.exists():
                state.update({"size": path.stat().st_size, "sha256": sha256_file(path), "needed": readelf_needed(path, readelf_path)})
            state["ok"] = bool(path.exists() and path.stat().st_size > 0) if path.exists() else False
            payload["extract"].append(state)
    extracted = {item["name"] for item in payload["extract"] if item.get("ok")}
    all_needed = sorted({dep for item in payload["extract"] for dep in item.get("needed", [])})
    payload["needed_union"] = all_needed
    payload["needed_satisfied_by_closure"] = sorted(set(all_needed) & extracted)
    payload["needed_external_runtime"] = sorted(set(all_needed) - extracted)
    payload["missing_vendor_libs"] = [name for name in VENDOR_LIBS if name not in extracted]
    payload["ok"] = bool(image.exists() and not payload["missing_vendor_libs"])
    return payload


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vendor-image", type=Path, default=VENDOR_IMAGE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest-path", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--debugfs", default="debugfs")
    parser.add_argument("--readelf", default="readelf")
    parser.add_argument("--extract", action="store_true", help="Extract libraries into the private output directory")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_manifest(args)
    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload.get("ok") or not args.extract else 1


if __name__ == "__main__":
    raise SystemExit(main())
