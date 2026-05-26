#!/usr/bin/env python3
"""V990 classifier for wificond service-manager registration failure."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v990-wificond-service-registration-gap")
LATEST_POINTER = Path("tmp/wifi/latest-v990-wificond-service-registration-gap.txt")
DEFAULT_V988_TRANSCRIPT = Path("tmp/wifi/v988-android-service-window-live-v167/native/mdm-helper-cnss-before-esoc.txt")
DEFAULT_V989_MANIFEST = Path("tmp/wifi/v989-wificond-offset-classifier/manifest.json")
DEFAULT_WIFICOND_BINARY = Path("tmp/wifi/v989-wificond-offset-classifier/wificond")
SERVICE_CONTEXT_COMMAND = [
    "python3",
    "scripts/revalidation/a90ctl.py",
    "--timeout",
    "20",
    "run",
    "/cache/bin/busybox",
    "sh",
    "-c",
    (
        "for p in "
        "/mnt/system/system/etc/selinux/plat_service_contexts "
        "/mnt/system/system/system_ext/etc/selinux/system_ext_service_contexts "
        "/mnt/system/system/product/etc/selinux/product_service_contexts "
        "/mnt/system/system/vendor/etc/selinux/vendor_service_contexts; "
        "do if [ -e $p ]; then echo ===$p===; /cache/bin/toybox grep -n -E 'wificond|wifinl80211' $p; fi; done"
    ),
]


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v988-transcript", type=Path, default=DEFAULT_V988_TRANSCRIPT)
    parser.add_argument("--v989-manifest", type=Path, default=DEFAULT_V989_MANIFEST)
    parser.add_argument("--wificond-binary", type=Path, default=DEFAULT_WIFICOND_BINARY)
    parser.add_argument("--skip-device", action="store_true")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def read_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    return json.loads(text)


def run_host(command: list[str], timeout: int = 45) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path("."),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
    )
    return result.returncode, result.stdout


def binary_contains(binary: Path, needle: bytes) -> bool:
    resolved = repo_path(binary)
    return resolved.exists() and needle in resolved.read_bytes()


def classify(v988: str, v989: dict[str, Any], context_output: str, binary: Path) -> dict[str, Any]:
    checks = {
        "v989_classified_addservice_check": v989.get("decision") == "v989-wificond-addservice-check-failed",
        "binary_contains_wifinl80211_service_name": binary_contains(binary, b"wifinl80211\0"),
        "service_context_maps_wifinl80211": "wifinl80211" in context_output and "u:object_r:wifinl80211_service:s0" in context_output,
        "service_context_lacks_literal_wificond": " wificond" not in context_output and "\twificond" not in context_output,
        "wificond_requested_target_domain": "wifi_hal_composite_child.wificond.selinux_exec.target_context=u:r:wificond:s0" in v988,
        "wificond_setexeccon_accepted": "wifi_hal_composite_child.wificond.selinux_exec.ok=1" in v988,
        "wificond_still_running_as_kernel": (
            "wificond.identity.after.selinux.current=kernel" in v988
            and "wifi_hal_composite_child.wificond.selinux.current=kernel" in v988
            and "wifi_hal_composite_child.wificond.selinux.exec=kernel" in v988
        ),
        "servicemanager_still_running_as_kernel": (
            "wifi_hal_composite_child.servicemanager.selinux.current=kernel" in v988
            and "wifi_hal_composite_child.servicemanager.selinux.exec=kernel" in v988
        ),
        "binder_devices_present": all(
            token in v988
            for token in (
                "context.dev_binder.exists=1",
                "context.dev_hwbinder.exists=1",
                "context.dev_vndbinder.exists=1",
            )
        ),
        "property_shim_running": "wifi_hal_composite_start.property_service_shim.started=1" in v988,
    }
    passed = all(checks.values())
    return {
        "decision": "v990-wificond-addservice-selinux-transition-gap"
        if passed
        else "v990-wificond-service-registration-gap-incomplete",
        "pass": passed,
        "reason": (
            "wificond registers service name wifinl80211, the service_context exists, but wificond and servicemanager still execute as kernel"
            if passed
            else "missing checks: " + ", ".join(name for name, ok in checks.items() if not ok)
        ),
        "next_step": (
            "repair SELinux domain transition/service-manager caller context before another service-window retry"
            if passed
            else "collect service contexts or V988/V989 inputs before selecting a repair"
        ),
        "checks": checks,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    rows = [(name, "PASS" if ok else "FAIL") for name, ok in manifest["checks"].items()]
    return "\n".join(
        [
            "# V990 Wificond Service Registration Gap",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- next: {manifest['next_step']}",
            "",
            markdown_table(["check", "result"], rows),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    v988 = read_text(args.v988_transcript)
    v989 = read_json(args.v989_manifest)
    if args.skip_device:
        context_rc = 0
        context_output = read_text(args.out_dir / "service-context-grep.txt")
    else:
        context_rc, context_output = run_host(SERVICE_CONTEXT_COMMAND)
        write_private_text(store.run_dir / "service-context-grep.txt", context_output)
    classification = classify(v988, v989, context_output, args.wificond_binary)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "host": collect_host_metadata(),
        "v988_transcript": str(repo_path(args.v988_transcript)),
        "v989_manifest": str(repo_path(args.v989_manifest)),
        "wificond_binary": str(repo_path(args.wificond_binary)),
        "service_context_command": SERVICE_CONTEXT_COMMAND,
        "service_context_rc": context_rc,
        "device_commands_executed": not args.skip_device,
        "device_mutations": False,
        "actor_start_executed": False,
        "wifi_bringup_executed": False,
        **classification,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {store.run_dir / 'manifest.json'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
