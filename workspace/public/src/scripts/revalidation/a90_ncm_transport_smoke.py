#!/usr/bin/env python3
"""Run bounded USB NCM transport smoke tests against native init.

This is transport-only: it does not touch Wi-Fi scan/connect, credentials,
DHCP, routes, or external network access.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import sys
import time
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

from _workspace_bootstrap import add_legacy_revalidation_path, repo_root

add_legacy_revalidation_path(repo_root())

import a90_ncm_transport as ncm
import a90_transport as transport
from a90harness.evidence import EvidenceStore, safe_artifact_label, wifi_artifact_dir


def run_command(command: list[object], *, timeout: float) -> dict[str, Any]:
    return transport.run_host_command(command, timeout=timeout)


def write_step(store: EvidenceStore,
               steps: list[dict[str, Any]],
               name: str,
               result: dict[str, Any]) -> None:
    transport.write_step(store, steps, name, result)


def run_step(store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
    *,
    timeout: float = 60.0,
    bridge_timeout: float = 45.0) -> dict[str, Any]:
    return transport.run_serial_step(
        store,
        steps,
        name,
        command,
        timeout=timeout,
        bridge_timeout=bridge_timeout,
    )


def write_pattern_file(path: Path, size_bytes: int) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    block = bytearray(1024 * 1024)
    written = 0
    with path.open("wb") as handle:
        while written < size_bytes:
            for offset in range(0, len(block), 32):
                value = (written + offset).to_bytes(8, "little", signed=False)
                block[offset:offset + 8] = value
                block[offset + 8:offset + 32] = b"A90-NCM-BENCHMARK-PATTERN"[:24]
            chunk = bytes(block[:min(len(block), size_bytes - written)])
            handle.write(chunk)
            digest.update(chunk)
            written += len(chunk)
    return digest.hexdigest()


def stream_remote_to_host(transfer: ncm.FastTransferSession,
                          store: EvidenceStore,
                          steps: list[dict[str, Any]],
                          *,
                          label: str,
                          remote_path: str,
                          expected_sha256: str,
                          timeout: float) -> dict[str, Any]:
    started = time.monotonic()
    if not transfer.ensure_device_reachable():
        return {
            "ok": False,
            "reason": transfer.reason,
            "method": "ncm-cat-nc",
            "elapsed_sec": 0.0,
        }
    receive_path = store.path(f"{label}-upload.bin")
    with ncm.TcpArchiveReceiver(receive_path, timeout=timeout) as receiver:
        remote_host = shlex.quote(transfer.host_link_local + "%" + transfer.device_ifname)
        script = (
            f"/cache/bin/busybox cat {shlex.quote(remote_path)} | "
            f"/cache/bin/busybox nc -w 1 {remote_host} {receiver.port}; "
            "echo fast_upload_raw.nc_rc=$?"
        )
        step = run_step(
            store,
            steps,
            f"{label}-raw-upload-stream",
            ["run", "/cache/bin/busybox", "sh", "-c", script],
            timeout=timeout + 30,
            bridge_timeout=timeout + 5,
        )
    output = "\n".join([str(step.get("stdout") or ""), str(step.get("stderr") or "")])
    fields = ncm.parse_key_values(output)
    ok = (
        bool(step.get("ok"))
        and fields.get("fast_upload_raw.nc_rc") == "0"
        and bool(receiver.result.get("ok"))
        and receiver.result.get("sha256") == expected_sha256
    )
    result = {
        "ok": ok,
        "reason": "ok" if ok else "upload-or-sha-failed",
        "method": "ncm-cat-nc",
        "elapsed_sec": round(time.monotonic() - started, 3),
        "device_nc_rc": fields.get("fast_upload_raw.nc_rc", ""),
        "receiver": receiver.result,
        "host_ifname": transfer.ifname,
        "host_link_local": transfer.host_link_local,
    }
    ncm.write_compact_step(
        store,
        steps,
        f"{label}-raw-upload-result",
        command=["ncm-raw-upload-result", remote_path],
        ok=ok,
        rc=0 if ok else 1,
        stdout=json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n",
    )
    return result


def maybe_force_nm_repair(profile: str, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    if not shutil_which("nmcli"):
        return
    for command in (
        ["nmcli", "con", "down", profile],
        ["nmcli", "con", "delete", profile],
    ):
        result = run_command(command, timeout=15)
        write_step(store, steps, "force-nm-repair-" + command[2], result)


def shutil_which(name: str) -> str:
    for item in os.environ.get("PATH", "").split(os.pathsep):
        candidate = Path(item) / name
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return ""


def parse_sizes(raw: str) -> list[int]:
    sizes: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        sizes.append(int(item, 0))
    return sizes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="default")
    parser.add_argument("--sizes-mib", default="1,32")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--upload", action="store_true", help="also stream each staged file back to host")
    parser.add_argument("--force-nm-repair", action="store_true", help="delete/down the temporary NM profile before readiness")
    parser.add_argument("--keep-remote", action="store_true")
    parser.add_argument("--download-retries", type=int, default=1, help="bounded retries after a failed host-to-device transfer")
    parser.add_argument("--retry-sleep-sec", type=float, default=2.0)
    parser.add_argument("--bridge-device", default=transport.DEFAULT_BRIDGE_DEVICE)
    parser.add_argument("--no-bridge-ensure", action="store_true")
    args = parser.parse_args()

    safe_label = safe_artifact_label(args.label)
    out_dir = args.out_dir or wifi_artifact_dir("bench", f"a90-ncm-transport-smoke-{safe_label}", timestamp=True)
    store = EvidenceStore(out_dir)
    steps: list[dict[str, Any]] = []
    sizes = parse_sizes(args.sizes_mib)
    manifest: dict[str, Any] = {
        "label": safe_label,
        "out_dir": str(out_dir),
        "phase_timer_contract": transport.PHASE_TIMER_CONTRACT,
        "phase_timers": [],
    }
    with transport.phase(manifest, "preflight"):
        transport_selection = transport.select_transport(
            store,
            steps,
            bridge_device=args.bridge_device,
            ensure=not args.no_bridge_ensure,
            prefer_fast=True,
        )

        run_step(store, steps, "pre-smoke-hide", ["hide"], timeout=15, bridge_timeout=8)

        if args.force_nm_repair:
            maybe_force_nm_repair(ncm.DEFAULT_NM_PROFILE, store, steps)

    transfer = ncm.FastTransferSession(store, steps, run_step=run_step)
    tests: list[dict[str, Any]] = []
    try:
        with transport.phase(manifest, "helper_stage"):
            for size_mib in sizes:
                size_bytes = size_mib * 1024 * 1024
                label = f"{safe_label}-{size_mib}mib"
                local_path = store.path(f"{label}.bin")
                expected_sha256 = write_pattern_file(local_path, size_bytes)
                remote_path = f"/cache/a90-ncm-smoke-{label}.bin"
                download_attempts: list[dict[str, Any]] = []
                download: dict[str, Any] = {}
                for attempt in range(max(0, args.download_retries) + 1):
                    attempt_label = label if attempt == 0 else f"{label}-retry{attempt}"
                    download = transfer.transfer_file(
                        label=attempt_label,
                        local_path=local_path,
                        remote_path=remote_path,
                        expected_sha256=expected_sha256,
                        mode="600",
                    )
                    download_attempts.append(download)
                    if download.get("ok"):
                        break
                    if attempt < max(0, args.download_retries):
                        time.sleep(max(0.0, args.retry_sleep_sec))
                upload: dict[str, Any] = {}
                if args.upload and download.get("ok"):
                    upload = stream_remote_to_host(
                        transfer,
                        store,
                        steps,
                        label=label,
                        remote_path=remote_path,
                        expected_sha256=expected_sha256,
                        timeout=max(45.0, float(size_mib) * 3.0),
                    )
                if not args.keep_remote:
                    run_step(
                        store,
                        steps,
                        f"{label}-cleanup",
                        ["run", "/cache/bin/busybox", "rm", "-f", remote_path],
                        timeout=30,
                        bridge_timeout=15,
                    )
                tests.append({
                    "size_mib": size_mib,
                    "size_bytes": size_bytes,
                    "sha256": expected_sha256,
                    "download": download,
                    "download_attempts": download_attempts,
                    "upload": upload,
                })
    finally:
        transfer.close()

    with transport.phase(manifest, "selftest"):
        status = run_step(store, steps, "post-smoke-status", ["status"], timeout=45, bridge_timeout=20)
    manifest.update({
        "sizes_mib": sizes,
        "force_nm_repair": args.force_nm_repair,
        "download_retries": args.download_retries,
        "retry_sleep_sec": args.retry_sleep_sec,
        "transport": transport_selection,
        "host_ifname": transfer.ifname,
        "host_link_local": transfer.host_link_local,
        "reason": transfer.reason,
        "tests": tests,
        "post_status_ok": status.get("ok"),
        "steps": steps,
    })
    with transport.phase(manifest, "artifact_upload"):
        pass
    store.write_text("manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")

    ok = all(test["download"].get("ok") and (not args.upload or test["upload"].get("ok")) for test in tests)
    print(json.dumps({
        "ok": ok,
        "out_dir": str(out_dir),
        "host_ifname": transfer.ifname,
        "host_link_local": transfer.host_link_local,
        "transport_selected": transport_selection.get("selected"),
        "transport_ncm_host": transport_selection.get("ncm_host"),
        "tests": [
            {
                "size_mib": test["size_mib"],
                "download_ok": test["download"].get("ok"),
                "download_elapsed_sec": test["download"].get("elapsed_sec"),
                "download_attempts": len(test.get("download_attempts") or []),
                "upload_ok": test["upload"].get("ok") if args.upload else None,
                "upload_elapsed_sec": test["upload"].get("elapsed_sec") if args.upload else None,
            }
            for test in tests
        ],
    }, indent=2, sort_keys=True))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
