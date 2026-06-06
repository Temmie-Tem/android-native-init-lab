#!/usr/bin/env python3
"""V673 same-helper service74 replay matrix.

This runner replays two bounded live arms with the same helper v111:

1. V668-compatible service74 CNSS retry path.
2. V671 service74-gated Android userspace-order path.

Each arm gets a fresh V641 clean-DSP boot, V401 SELinuxfs surface, and V490
policy-load proof before the live arm. It does not start supplicant, scan,
connect, run DHCP, change routes, use credentials, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore
from a90ctl import run_cmdv1_command


DEFAULT_OUT_DIR = Path("tmp/wifi/v673-same-helper-replay")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.67 (v641)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
HELPER_MARKER = "a90_android_execns_probe v111"
HELPER_SHA256 = "1c65e1b766b85fda7629d9d7067047d8e0322d412447cf731ccab65a70655d88"
V641_FLAG = "/cache/native-init-sibling-fwssctl-v641"

V401_APPROVAL = "approve v401 toybox mount selinuxfs runtime surface only; no daemon start and no Wi-Fi bring-up"
V490_APPROVAL = "approve v490 native SELinux policy-load proof only; no init reexec, no daemon start and no Wi-Fi bring-up"
V668_APPROVAL = "approve v668 service74 cnss2 focused capture proof only; no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
V671_APPROVAL = "approve v671 service74 Android userspace-order start-only proof only; no supplicant, no scan/connect/link-up, no DHCP and no external ping"

FORBIDDEN_ACTIONS = (
    "supplicant or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "boot image or partition write",
)
ALLOWED_LIVE_ACTIONS = (
    "V641 one-shot clean-DSP reboot",
    "V401 SELinuxfs mount surface",
    "V490 Android SELinux policy-load proof",
    "bounded V668-compatible companion start-only proof",
    "bounded V671 Android-userspace-order start-only proof",
    "runner-owned reboot cleanup",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=HELPER_SHA256)
    parser.add_argument("--helper-marker", default=HELPER_MARKER)
    parser.add_argument("--wait-sec", type=float, default=75.0)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def run_host(command: list[str], *, timeout: float) -> tuple[int, str]:
    proc = subprocess.run(
        command,
        cwd=repo_path(Path(".")),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return proc.returncode, proc.stdout


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8"))


def write_host_output(store: EvidenceStore, name: str, command: list[str], rc: int, output: str) -> str:
    rel = f"host/{name}.txt"
    body = "$ " + " ".join(command) + "\nrc=" + str(rc) + "\n" + output.rstrip() + "\n"
    store.write_text(rel, body)
    return rel


def send_menu_quit(host: str, port: int) -> None:
    try:
        with socket.create_connection((host, port), timeout=2.0) as sock:
            sock.sendall(b"hide\n")
    except OSError:
        pass


def hide_menu(args: argparse.Namespace) -> None:
    send_menu_quit(args.host, args.port)
    try:
        run_cmdv1_command(args.host, args.port, 5.0, ["hide"], retry_unsafe=False)
    except Exception:
        pass
    time.sleep(0.4)


def cmdv1(args: argparse.Namespace, command: list[str], timeout: float) -> dict[str, Any]:
    try:
        result = run_cmdv1_command(args.host, args.port, timeout, command, retry_unsafe=False)
        return {
            "ok": result.status == "ok" and result.rc == 0,
            "status": result.status,
            "rc": result.rc,
            "text": result.text,
            "error": "",
        }
    except Exception as exc:  # noqa: BLE001 - live replay records failures
        return {
            "ok": False,
            "status": "error",
            "rc": None,
            "text": "",
            "error": str(exc),
        }


def reboot_initiated(result: dict[str, Any]) -> bool:
    if result.get("ok"):
        return True
    error = str(result.get("error") or "")
    return "reboot: syncing" in error or "A90P1 BEGIN" in error


def wait_for_native(args: argparse.Namespace) -> dict[str, Any]:
    started = time.monotonic()
    version_seen = False
    status_healthy = False
    attempts = 0
    while time.monotonic() - started < args.wait_sec:
        attempts += 1
        try:
            version = run_cmdv1_command(args.host, args.port, 5.0, ["version"], retry_unsafe=False)
            version_seen = args.expect_version in version.text
            status = run_cmdv1_command(args.host, args.port, 5.0, ["status"], retry_unsafe=False)
            status_healthy = "fail=0" in status.text
            if version_seen and status_healthy:
                break
        except Exception:
            time.sleep(2.0)
    return {
        "attempts": attempts,
        "wait_sec": round(time.monotonic() - started, 3),
        "version_seen": version_seen,
        "status_healthy": status_healthy,
    }


def run_v641_clean_boot(args: argparse.Namespace) -> dict[str, Any]:
    hide_menu(args)
    arm = cmdv1(
        args,
        ["run", "/cache/bin/busybox", "sh", "-c", f"printf run > {V641_FLAG}"],
        10.0,
    )
    stat = cmdv1(args, ["stat", V641_FLAG], 10.0)
    if not (arm.get("ok") and stat.get("ok")):
        return {
            "arm_ok": bool(arm.get("ok")),
            "stat_ok": bool(stat.get("ok")),
            "reboot_initiated": False,
            "wait": {},
            "ready": False,
        }
    reboot = cmdv1(args, ["reboot"], 8.0)
    wait = wait_for_native(args)
    hide_menu(args)
    return {
        "arm_ok": bool(arm.get("ok")),
        "stat_ok": bool(stat.get("ok")),
        "reboot_initiated": reboot_initiated(reboot),
        "wait": wait,
        "ready": bool(arm.get("ok") and stat.get("ok") and reboot_initiated(reboot) and wait.get("version_seen") and wait.get("status_healthy")),
    }


def mount_system(args: argparse.Namespace) -> dict[str, Any]:
    hide_menu(args)
    result = cmdv1(args, ["mountsystem", "ro"], 20.0)
    stat = cmdv1(args, ["stat", "/mnt/system/system/bin"], 10.0)
    return {
        "mount_ok": bool(result.get("ok")),
        "stat_ok": bool(stat.get("ok")),
        "ready": bool(result.get("ok") and stat.get("ok")),
    }


def cleanup_global_firmware_mounts(args: argparse.Namespace) -> dict[str, Any]:
    hide_menu(args)
    modem = cmdv1(args, ["umount", "/vendor/firmware-modem"], 15.0)
    mnt = cmdv1(args, ["umount", "/vendor/firmware_mnt"], 15.0)
    mounts = cmdv1(args, ["cat", "/proc/mounts"], 15.0)
    text = str(mounts.get("text") or "")
    still_mounted = [
        target
        for target in ("/vendor/firmware-modem", "/vendor/firmware_mnt")
        if f" {target} " in text
    ]
    return {
        "umount_firmware_modem_ok": bool(modem.get("ok")),
        "umount_firmware_mnt_ok": bool(mnt.get("ok")),
        "mounts_read_ok": bool(mounts.get("ok")),
        "still_mounted": still_mounted,
        "ready": bool(mounts.get("ok") and not still_mounted),
    }


def run_script(store: EvidenceStore, name: str, command: list[str], timeout: float) -> dict[str, Any]:
    rc, output = run_host(command, timeout=timeout)
    file = write_host_output(store, name, command, rc, output)
    return {"rc": rc, "ok": rc == 0, "file": file, "output_tail": output.splitlines()[-12:]}


def prep_current_boot(args: argparse.Namespace, store: EvidenceStore, label: str, arm_dir: Path) -> dict[str, Any]:
    prep_dir = arm_dir / "prep"
    v401_dir = prep_dir / "v401"
    v490_dir = prep_dir / "v490"
    clean = run_v641_clean_boot(args)
    system = mount_system(args)
    if not (clean.get("ready") and system.get("ready")):
        return {
            "label": label,
            "clean_boot": clean,
            "system_mount": system,
            "v401": {},
            "v490": {},
            "ready": False,
        }
    hide_menu(args)
    v401_command = [
        sys.executable,
        "scripts/revalidation/wifi_selinuxfs_toybox_mount_live_executor.py",
        "--out-dir",
        str(v401_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--approval-phrase",
        V401_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    v401 = run_script(store, f"{label}-v401", v401_command, 120.0)
    v490_command = [
        sys.executable,
        "scripts/revalidation/native_selinux_policy_load_proof_v490.py",
        "--out-dir",
        str(v490_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--approval-phrase",
        V490_APPROVAL,
        "--apply",
        "--assume-yes",
        "run",
    ]
    hide_menu(args)
    v490 = run_script(store, f"{label}-v490", v490_command, 240.0)
    firmware_cleanup = cleanup_global_firmware_mounts(args)
    v401_manifest = load_json(v401_dir / "manifest.json")
    v490_manifest = load_json(v490_dir / "manifest.json")
    ready = bool(
        clean.get("ready")
        and system.get("ready")
        and v401_manifest.get("decision") == "toybox-selinuxfs-mount-live-executor-run-pass"
        and v490_manifest.get("decision") == "v490-selinux-policy-load-proof-pass"
        and firmware_cleanup.get("ready")
    )
    return {
        "label": label,
        "clean_boot": clean,
        "system_mount": system,
        "v401": {**v401, "decision": v401_manifest.get("decision", ""), "pass": v401_manifest.get("pass")},
        "v490": {**v490, "decision": v490_manifest.get("decision", ""), "pass": v490_manifest.get("pass"), "manifest": str(v490_dir / "manifest.json")},
        "firmware_cleanup": firmware_cleanup,
        "ready": ready,
    }


def run_arm(args: argparse.Namespace, store: EvidenceStore, label: str, script: str, approval: str, out_dir: Path, v490_manifest: Path) -> dict[str, Any]:
    command = [
        sys.executable,
        script,
        "--out-dir",
        str(out_dir),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--expect-version",
        args.expect_version,
        "--helper",
        args.helper,
        "--helper-sha256",
        args.helper_sha256,
        "--helper-marker",
        args.helper_marker,
        "--v490-manifest",
        str(v490_manifest),
        "--approval-phrase",
        approval,
        "--apply",
        "--assume-yes",
        "run",
    ]
    arm_companion_runtime_sec = getattr(args, "arm_companion_runtime_sec", None)
    if arm_companion_runtime_sec is not None:
        command[-1:-1] = ["--companion-runtime-sec", str(arm_companion_runtime_sec)]
    result = run_script(store, f"{label}-live", command, 300.0)
    manifest_path = out_dir / "manifest.json"
    manifest = load_json(manifest_path)
    return {
        **result,
        "manifest": str(manifest_path),
        "decision": manifest.get("decision", ""),
        "pass": manifest.get("pass"),
        "reason": manifest.get("reason", ""),
        "next_step": manifest.get("next_step", ""),
        "live": manifest.get("live") or {},
    }


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def surface_for(arm: dict[str, Any], key: str) -> dict[str, Any]:
    live = arm.get("live") or {}
    value = live.get(key)
    return value if isinstance(value, dict) else {}


def service74_gate(arm: dict[str, Any]) -> dict[str, Any]:
    for key in ("v671_android_userspace_surface", "v668_surface", "v655_surface"):
        surface = surface_for(arm, key)
        gate = surface.get("service74_gate")
        if isinstance(gate, dict):
            return gate
    return {}


def counts_for(arm: dict[str, Any]) -> dict[str, int]:
    live = arm.get("live") or {}
    counts = live.get("v655_counts") or live.get("v668_counts") or {}
    keys = (
        "service_notifier_180",
        "service_notifier_74",
        "cnss_binder_transaction_failed",
        "binder_transaction_failed",
        "kernel_warning",
        "wlfw_start",
        "wlfw_service_request",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
    )
    return {key: int_value(counts.get(key)) for key in keys}


def markers_for(arm: dict[str, Any]) -> dict[str, int]:
    live = arm.get("live") or {}
    counts = ((live.get("markers") or {}).get("counts") or {})
    return {key: int_value(counts.get(key)) for key in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "kernel_warning", "wlfw", "bdf", "wlan0")}


def android_children_started(arm: dict[str, Any]) -> bool:
    return bool((arm.get("live") or {}).get("v671_android_userspace_children_started"))


def wifi_advanced(counts: dict[str, int], markers: dict[str, int]) -> bool:
    return any(counts.get(key, 0) > 0 for key in ("wlfw_start", "wlfw_service_request", "bdf_regdb", "bdf_bdwlan", "wlan_fw_ready", "wlan0")) or any(markers.get(key, 0) > 0 for key in ("wlfw", "bdf", "wlan0"))


def decide(command: str, prep_v668: dict[str, Any] | None, arm_v668: dict[str, Any] | None, prep_v671: dict[str, Any] | None, arm_v671: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v673-same-helper-replay-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V673 live matrix with helper v111",
        )
    if not prep_v668 or not prep_v668.get("ready"):
        return "v673-v668-prep-blocked", False, f"prep_v668={prep_v668}", "restore V641/V401/V490 current-boot prerequisites"
    if not arm_v668 or not arm_v668.get("decision"):
        return "v673-v668-arm-missing", False, "V668-compatible arm did not produce a manifest", "inspect V668 arm output"
    if "blocked" in str(arm_v668.get("decision")):
        return "v673-v668-arm-blocked", False, f"arm_v668={summarize_arm(arm_v668)}", "resolve V668-compatible arm blockers before comparing modes"
    if not prep_v671 or not prep_v671.get("ready"):
        return "v673-v671-prep-blocked", False, f"prep_v671={prep_v671}", "restore V641/V401/V490 current-boot prerequisites"
    if not arm_v671 or not arm_v671.get("decision"):
        return "v673-v671-arm-missing", False, "V671 arm did not produce a manifest", "inspect V671 arm output"
    if "blocked" in str(arm_v671.get("decision")):
        return "v673-v671-arm-blocked", False, f"arm_v671={summarize_arm(arm_v671)}", "resolve V671 arm blockers before comparing modes"

    v668_counts = counts_for(arm_v668)
    v671_counts = counts_for(arm_v671)
    v668_gate = service74_gate(arm_v668)
    v671_gate = service74_gate(arm_v671)
    v671_markers = markers_for(arm_v671)
    v668_positive = v668_gate.get("open") == "1" and v668_counts.get("service_notifier_180", 0) > 0 and v668_counts.get("service_notifier_74", 0) > 0
    v671_positive = v671_gate.get("open") == "1" and v671_counts.get("service_notifier_180", 0) > 0 and v671_counts.get("service_notifier_74", 0) > 0
    if not v668_positive:
        return (
            "v673-service74-not-reproducible-on-current-boot",
            True,
            f"helper v111 V668-compatible arm did not reproduce service74 positive path; gate={v668_gate} counts={v668_counts}",
            "rerun lower service-notifier restoration before changing Android userspace order",
        )
    if v668_positive and not v671_positive:
        return (
            "v673-same-helper-mode-regression-classified",
            True,
            f"helper v111 reproduces V668-compatible service74, but V671 mode still times out; v671_gate={v671_gate} v671_counts={v671_counts}",
            "plan V674 to isolate V671 pre-gate deltas: allow-wifi-hal flag, wlan device materialization, Android-userspace request flags, and helper mode setup before service74 gate",
        )
    if v671_positive and wifi_advanced(v671_counts, v671_markers):
        return (
            "v673-android-userspace-wifi-surface-advanced",
            True,
            f"V671 mode reached service74 and advanced Wi-Fi markers; counts={v671_counts} markers={v671_markers}",
            "classify WLFW/BDF/wlan0 state before supplicant or scan/connect",
        )
    if v671_positive and android_children_started(arm_v671):
        return (
            "v673-android-userspace-no-wlfw-advance",
            True,
            f"V671 mode started Android userspace children but WLFW/BDF/wlan0 remain absent; counts={v671_counts}",
            "inspect HAL/wificond output and binder/property registration before connection attempt",
        )
    return (
        "v673-android-userspace-gate-positive-but-children-withheld",
        True,
        f"service74 positive state is ambiguous; v671_gate={v671_gate} children_started={android_children_started(arm_v671)}",
        "inspect V671 helper transcript before another live mutation",
    )


def build_manifest(args: argparse.Namespace,
                   prep_v668: dict[str, Any] | None,
                   arm_v668: dict[str, Any] | None,
                   prep_v671: dict[str, Any] | None,
                   arm_v671: dict[str, Any] | None) -> dict[str, Any]:
    decision, pass_ok, reason, next_step = decide(args.command, prep_v668, arm_v668, prep_v671, arm_v671)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v673",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper_marker": args.helper_marker,
        "helper_sha256": args.helper_sha256,
        "allowed_live_actions": ALLOWED_LIVE_ACTIONS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "prep_v668": prep_v668 or {},
        "arm_v668": summarize_arm(arm_v668),
        "prep_v671": prep_v671 or {},
        "arm_v671": summarize_arm(arm_v671),
        "comparison": {
            "v668_gate": service74_gate(arm_v668 or {}),
            "v671_gate": service74_gate(arm_v671 or {}),
            "v668_counts": counts_for(arm_v668 or {}),
            "v671_counts": counts_for(arm_v671 or {}),
            "v668_markers": markers_for(arm_v668 or {}),
            "v671_markers": markers_for(arm_v671 or {}),
            "v671_android_children_started": android_children_started(arm_v671 or {}),
        },
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "daemon_start_executed": args.command == "run",
        "wifi_hal_start_executed": bool(args.command == "run" and android_children_started(arm_v671 or {})),
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def summarize_arm(arm: dict[str, Any] | None) -> dict[str, Any]:
    if not arm:
        return {}
    reboot = (arm.get("live") or {}).get("reboot_cleanup") or {}
    return {
        "decision": arm.get("decision", ""),
        "pass": arm.get("pass"),
        "reason": arm.get("reason", ""),
        "next_step": arm.get("next_step", ""),
        "manifest": arm.get("manifest", ""),
        "rc": arm.get("rc"),
        "ok": arm.get("ok"),
        "gate": service74_gate(arm),
        "counts": counts_for(arm),
        "markers": markers_for(arm),
        "reboot_cleanup": {
            "version_seen": reboot.get("version_seen"),
            "status_healthy": reboot.get("status_healthy"),
            "wait_sec": reboot.get("wait_sec"),
        },
        "android_children_started": android_children_started(arm),
    }


def rows_from_dict(prefix: str, values: dict[str, Any]) -> list[list[str]]:
    return [[prefix, key, json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else str(value)] for key, value in values.items()]


def render_summary(manifest: dict[str, Any]) -> str:
    comparison = manifest["comparison"]
    rows: list[list[str]] = []
    rows.extend(rows_from_dict("v668_gate", comparison["v668_gate"]))
    rows.extend(rows_from_dict("v671_gate", comparison["v671_gate"]))
    rows.extend(rows_from_dict("v668_counts", comparison["v668_counts"]))
    rows.extend(rows_from_dict("v671_counts", comparison["v671_counts"]))
    rows.extend(rows_from_dict("v668_markers", comparison["v668_markers"]))
    rows.extend(rows_from_dict("v671_markers", comparison["v671_markers"]))
    return "\n".join([
        "# V673 Same-helper Service74 Replay Matrix",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker: `{manifest['helper_marker']}`",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Arms",
        "",
        markdown_table(
            ["arm", "decision", "pass", "manifest"],
            [
                ["v668-compatible", str(manifest["arm_v668"].get("decision", "")), str(manifest["arm_v668"].get("pass", "")), str(manifest["arm_v668"].get("manifest", ""))],
                ["v671-android-userspace", str(manifest["arm_v671"].get("decision", "")), str(manifest["arm_v671"].get("pass", "")), str(manifest["arm_v671"].get("manifest", ""))],
            ],
        ),
        "",
        "## Comparison",
        "",
        markdown_table(["surface", "key", "value"], rows),
        "",
        "## Guardrails",
        "",
        "- Supplicant, scan/connect, DHCP, route change, credentials, and external ping remain blocked.",
        "- Each live arm uses bounded cleanup and reboots before the next current-boot prep.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    prep_v668: dict[str, Any] | None = None
    arm_v668: dict[str, Any] | None = None
    prep_v671: dict[str, Any] | None = None
    arm_v671: dict[str, Any] | None = None
    if args.command == "run":
        root = store.run_dir
        v668_dir = root / "arm-v668-v111"
        prep_v668 = prep_current_boot(args, store, "v668", v668_dir)
        if prep_v668.get("ready"):
            arm_v668 = run_arm(
                args,
                store,
                "v668",
                "scripts/revalidation/native_wifi_cnss2_focused_capture_v668.py",
                V668_APPROVAL,
                v668_dir / "live",
                Path(str(prep_v668["v490"]["manifest"])),
            )
        prep_v671 = prep_current_boot(args, store, "v671", root / "arm-v671-v111")
        if prep_v671.get("ready"):
            arm_v671 = run_arm(
                args,
                store,
                "v671",
                "scripts/revalidation/native_wifi_service74_android_order_v671.py",
                V671_APPROVAL,
                root / "arm-v671-v111" / "live",
                Path(str(prep_v671["v490"]["manifest"])),
            )
    manifest = build_manifest(args, prep_v668, arm_v668, prep_v671, arm_v671)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
