#!/usr/bin/env python3
"""V728 private vendor root layout proof.

This proof uses the already-deployed `a90_android_execns_probe` in
`identity-probe` mode to verify that the helper can create its private mount
namespace and mount the real `sda29` vendor partition as `/vendor`, without
starting CNSS daemon, service-manager, Wi-Fi HAL, scan/connect, DHCP, routes, or
external ping.

It also mounts the same `sda29` partition under an isolated `/tmp/a90-v728-*`
proof path with `ext4 ro,noload` to verify the Wi-Fi firmware files that the
next modem/WLFW gate will need.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v728-private-vendor-root")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.68 (v724)"
DEFAULT_EXPECT_HELPER = "a90_android_execns_probe v121"
PROBE_PREFIX = "/tmp/a90-v728-"

REQUIRED_VENDOR_FIRMWARE = (
    "firmware/wlanmdsp.mbn",
    "firmware/wlan/qca_cld/bdwlan.bin",
    "firmware/wlan/qca_cld/regdb.bin",
    "firmware/wlan/qca_cld/WCNSS_qcom_cfg.ini",
)
CURRENT_VENDOR_FIRMWARE = tuple(f"/vendor/{path}" for path in REQUIRED_VENDOR_FIRMWARE)
FORBIDDEN_TERMS = (
    "qcwlanstate",
    "svc wifi",
    "cmd wifi",
    "iw ",
    "wpa_supplicant",
    "hostapd",
    "dhcp",
    "rfkill",
    "insmod",
    "rmmod",
    "modprobe",
    "ip link",
)


@dataclass(frozen=True)
class ProbePaths:
    run_id: str
    base: str
    node: str
    mountpoint: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--expect-helper", default=DEFAULT_EXPECT_HELPER)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def make_probe_paths() -> ProbePaths:
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    base = f"{PROBE_PREFIX}{run_id}"
    return ProbePaths(run_id=run_id, base=base, node=f"{base}/sda29", mountpoint=f"{base}/vendor")


def is_under_probe(path: str, probe: ProbePaths) -> bool:
    return path == probe.base or path.startswith(probe.base + "/")


def validate_device_command(command: list[str], probe: ProbePaths | None = None, helper: str = DEFAULT_HELPER) -> None:
    joined = " ".join(command)
    lowered = joined.lower()
    for term in FORBIDDEN_TERMS:
        if term in lowered:
            raise RuntimeError(f"forbidden Wi-Fi bring-up term in V728 command: {joined}")
    if command[0] in {"version", "status", "selftest", "cat", "stat", "ls", "umount"}:
        return
    if command[0] == "mkdir" and probe and len(command) == 2 and is_under_probe(command[1], probe):
        return
    if command[0] == "mknodb" and probe and len(command) == 4 and command[1] == probe.node:
        return
    if command[:2] == ["run", helper]:
        if command == ["run", helper, "--help"]:
            return
        allowed = [
            "run",
            helper,
            "--system-root",
            "/mnt/system/system",
            "--vendor-block",
            "/dev/block/sda29",
            "--vendor-fstype",
            "ext4",
            "--target-profile",
            "cnss-daemon",
            "--mode",
            "identity-probe",
            "--timeout-sec",
            "5",
        ]
        if command == allowed:
            return
        raise RuntimeError(f"unexpected V728 helper command: {joined}")
    if command[:2] == ["run", DEFAULT_TOYBOX]:
        subcmd = command[2] if len(command) > 2 else ""
        if subcmd in {"ls", "find", "rm", "rmdir"}:
            return
        if subcmd == "mount" and probe:
            expected = ["run", DEFAULT_TOYBOX, "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint]
            if command == expected:
                return
        raise RuntimeError(f"unexpected V728 toybox command: {joined}")
    raise RuntimeError(f"unexpected V728 command: {joined}")


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None,
             probe: ProbePaths | None = None) -> dict[str, Any]:
    validate_device_command(command, probe, args.helper)
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    steps.append(item)
    return item


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def step_ok(steps: list[dict[str, Any]], name: str) -> bool:
    for step in steps:
        if step.get("name") == name:
            return bool(step.get("ok")) and step.get("status") == "ok"
    return False


def path_exists_payload(text: str) -> bool:
    lowered = text.lower()
    return bool(text.strip()) and all(token not in lowered for token in ("no such file", "not found", "cannot stat"))


def parse_dev(text: str) -> tuple[str, str] | None:
    match = re.search(r"(?m)^(\d+):(\d+)\s*$", text.strip())
    if not match:
        return None
    return match.group(1), match.group(2)


def parse_key_values(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip().strip('"')
    return parsed


def collect_live(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], 15.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "selftest", ["selftest"], 25.0)
    run_step(args, store, steps, "helper-help", ["run", args.helper, "--help"], 20.0)
    run_step(args, store, steps, "current-vendor-links", ["run", args.toybox, "ls", "-ld", "/vendor", "/mnt/system/vendor", "/system/vendor"], 15.0)
    for path in CURRENT_VENDOR_FIRMWARE:
        run_step(args, store, steps, f"current-stat-{safe_name(path)}", ["stat", path], 10.0)
    run_step(args, store, steps, "execns-identity-probe", [
        "run",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--target-profile",
        "cnss-daemon",
        "--mode",
        "identity-probe",
        "--timeout-sec",
        "5",
    ], 35.0)
    run_step(args, store, steps, "post-helper-proc-mounts", ["cat", "/proc/mounts"], 10.0)
    run_step(args, store, steps, "sda29-dev", ["cat", "/sys/class/block/sda29/dev"], 10.0)

    probe = make_probe_paths()
    dev = parse_dev(step_payload(steps, "sda29-dev"))
    isolated_mount_ok = False
    if dev:
        major, minor = dev
        run_step(args, store, steps, "probe-mkdir-base", ["mkdir", probe.base], 10.0, probe)
        run_step(args, store, steps, "probe-mkdir-vendor", ["mkdir", probe.mountpoint], 10.0, probe)
        run_step(args, store, steps, "probe-mknodb-sda29", ["mknodb", probe.node, major, minor], 10.0, probe)
        run_step(args, store, steps, "probe-mount-vendor-ro-noload", ["run", args.toybox, "mount", "-t", "ext4", "-o", "ro,noload", probe.node, probe.mountpoint], 45.0, probe)
        isolated_mount_ok = step_ok(steps, "probe-mount-vendor-ro-noload")
        run_step(args, store, steps, "probe-mounted-proc-mounts", ["cat", "/proc/mounts"], 10.0)
        for rel_path in REQUIRED_VENDOR_FIRMWARE:
            run_step(args, store, steps, f"probe-stat-{safe_name(rel_path)}", ["stat", f"{probe.mountpoint}/{rel_path}"], 10.0)
        run_step(args, store, steps, "probe-find-firmware", ["run", args.toybox, "find", f"{probe.mountpoint}/firmware", "-maxdepth", "4"], 30.0, probe)
        if isolated_mount_ok:
            run_step(args, store, steps, "cleanup-umount-vendor", ["umount", probe.mountpoint], 20.0, probe)
        run_step(args, store, steps, "cleanup-post-proc-mounts", ["cat", "/proc/mounts"], 10.0)
        run_step(args, store, steps, "cleanup-rm-node", ["run", args.toybox, "rm", "-f", probe.node], 10.0, probe)
        run_step(args, store, steps, "cleanup-rmdir-vendor", ["run", args.toybox, "rmdir", probe.mountpoint], 10.0, probe)
        run_step(args, store, steps, "cleanup-rmdir-base", ["run", args.toybox, "rmdir", probe.base], 10.0, probe)

    helper_text = step_payload(steps, "execns-identity-probe")
    helper_values = parse_key_values(helper_text)
    current_firmware_hits = [
        path for path in CURRENT_VENDOR_FIRMWARE
        if path_exists_payload(step_payload(steps, f"current-stat-{safe_name(path)}"))
    ]
    isolated_firmware_hits = [
        f"/vendor/{rel_path}" for rel_path in REQUIRED_VENDOR_FIRMWARE
        if path_exists_payload(step_payload(steps, f"probe-stat-{safe_name(rel_path)}"))
    ]
    firmware_tree_hits = [
        line.strip()
        for line in step_payload(steps, "probe-find-firmware").splitlines()
        if any(token in line.lower() for token in ("wlanmdsp", "bdwlan", "regdb", "wcnss"))
    ][:120]
    post_helper_mounts = step_payload(steps, "post-helper-proc-mounts")
    cleanup_mounts = step_payload(steps, "cleanup-post-proc-mounts")
    helper_cleanup_ok = "/tmp/a90-v231-" not in post_helper_mounts
    isolated_cleanup_ok = (not isolated_mount_ok or step_ok(steps, "cleanup-umount-vendor")) and probe.mountpoint not in cleanup_mounts and step_ok(steps, "cleanup-rmdir-base")
    live = {
        "probe": probe.__dict__,
        "sda29_dev": dev,
        "helper_version_seen": args.expect_helper in step_payload(steps, "helper-help") or args.expect_helper in helper_text,
        "helper_status": helper_values.get("helper_status", ""),
        "helper_version": args.expect_helper,
        "helper_vendor_mount_source": helper_values.get("vendor_mount_source", ""),
        "helper_firmware_mnt_mount_source": helper_values.get("firmware_mnt_mount_source", ""),
        "helper_firmware_modem_mount_source": helper_values.get("firmware_modem_mount_source", ""),
        "helper_target_path": helper_values.get("context.target.path", ""),
        "helper_target_host_path": helper_values.get("context.target.host_path", ""),
        "helper_target_exists": helper_values.get("context.target.exists", "") == "1",
        "helper_target_access_x": helper_values.get("context.target.access_x", "") == "1",
        "helper_child_exit_code": helper_values.get("child_exit_code", ""),
        "helper_child_signal": helper_values.get("child_signal", ""),
        "helper_cleanup_ok": helper_cleanup_ok,
        "current_vendor_firmware_hits": current_firmware_hits,
        "isolated_vendor_mount_ok": isolated_mount_ok,
        "isolated_vendor_firmware_hits": isolated_firmware_hits,
        "isolated_firmware_tree_hits": firmware_tree_hits,
        "isolated_cleanup_ok": isolated_cleanup_ok,
        "current_vendor_links": step_payload(steps, "current-vendor-links").strip().splitlines(),
    }
    return steps, live


def build_checks(args: argparse.Namespace, steps: list[dict[str, Any]], live: dict[str, Any]) -> list[dict[str, Any]]:
    if not live:
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "no device command executed",
            "next_step": "run V728 private vendor root proof",
        }]
    required_hits = {f"/vendor/{path}" for path in REQUIRED_VENDOR_FIRMWARE}
    return [
        {
            "name": "native-v724-clean",
            "status": "pass" if args.expect_version in step_payload(steps, "version") and "fail=0" in step_payload(steps, "status") and "fail=0" in step_payload(steps, "selftest") else "blocked",
            "detail": {"expect_version": args.expect_version},
            "next_step": "restore expected native baseline before private vendor root proof",
        },
        {
            "name": "helper-v121-present",
            "status": "pass" if live.get("helper_version_seen") else "blocked",
            "detail": {"expect_helper": args.expect_helper},
            "next_step": "deploy expected helper before private namespace proof",
        },
        {
            "name": "execns-private-vendor-ready",
            "status": "pass" if live.get("helper_status") == "namespace-ready" and live.get("helper_target_exists") and live.get("helper_target_access_x") else "blocked",
            "detail": {
                "helper_status": live.get("helper_status"),
                "vendor_mount_source": live.get("helper_vendor_mount_source"),
                "target": live.get("helper_target_path"),
                "target_exists": live.get("helper_target_exists"),
                "target_access_x": live.get("helper_target_access_x"),
            },
            "next_step": "fix helper private vendor mount before lower companion retry",
        },
        {
            "name": "helper-cleanup",
            "status": "pass" if live.get("helper_cleanup_ok") else "blocked",
            "detail": {"helper_cleanup_ok": live.get("helper_cleanup_ok")},
            "next_step": "cleanup helper private namespace leftovers before continuing",
        },
        {
            "name": "identity-child-runtime",
            "status": "pass" if live.get("helper_child_signal") in {"", "0"} else "review",
            "detail": {"child_exit_code": live.get("helper_child_exit_code"), "child_signal": live.get("helper_child_signal")},
            "next_step": "not a V728 blocker; later runtime gates must not infer daemon readiness from identity child runtime",
        },
        {
            "name": "current-vendor-firmware-absent",
            "status": "pass" if not live.get("current_vendor_firmware_hits") else "review",
            "detail": {"hits": live.get("current_vendor_firmware_hits"), "links": live.get("current_vendor_links")},
            "next_step": "if this changes, reassess whether global /vendor already exposes real vendor firmware",
        },
        {
            "name": "isolated-sda29-firmware-complete",
            "status": "pass" if required_hits.issubset(set(live.get("isolated_vendor_firmware_hits") or [])) else "blocked",
            "detail": {"hits": live.get("isolated_vendor_firmware_hits")},
            "next_step": "do not attempt modem ONLINE until required Wi-Fi firmware is mapped",
        },
        {
            "name": "isolated-cleanup",
            "status": "pass" if live.get("isolated_cleanup_ok") else "blocked",
            "detail": {"isolated_cleanup_ok": live.get("isolated_cleanup_ok"), "sda29_dev": live.get("sda29_dev")},
            "next_step": "cleanup isolated proof mount before further live work",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]], live: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v728-private-vendor-root-proof-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V728 private vendor root proof",
        )
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v728-private-vendor-root-proof-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "clear private vendor root proof blockers before modem ONLINE",
        )
    return (
        "v728-private-execns-vendor-root-layout-proof-pass",
        True,
        "helper private namespace mounts sda29 as /vendor and the same sda29 vendor contains required Wi-Fi firmware while global /vendor remains incomplete",
        "plan V729 smallest safe modem ONLINE trigger proof using this vendor layout; keep daemon/HAL/scan/connect blocked",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    live = manifest.get("live") or {}
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["helper_status", live.get("helper_status", "")],
        ["helper_vendor_mount_source", live.get("helper_vendor_mount_source", "")],
        ["helper_target_path", live.get("helper_target_path", "")],
        ["helper_target_exists", live.get("helper_target_exists", "")],
        ["helper_child_exit_code", live.get("helper_child_exit_code", "")],
        ["helper_child_signal", live.get("helper_child_signal", "")],
        ["helper_cleanup_ok", live.get("helper_cleanup_ok", "")],
        ["current_vendor_firmware_hits", len(live.get("current_vendor_firmware_hits") or [])],
        ["isolated_vendor_firmware_hits", len(live.get("isolated_vendor_firmware_hits") or [])],
        ["isolated_cleanup_ok", live.get("isolated_cleanup_ok", "")],
    ]
    return "\n".join([
        "# V728 Private Vendor Root Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- helper_identity_probe_executed: `{manifest['helper_identity_probe_executed']}`",
        f"- isolated_read_only_vendor_mount_executed: `{manifest['isolated_read_only_vendor_mount_executed']}`",
        f"- subsystem_writes_executed: `{manifest['subsystem_writes_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], check_rows),
        "",
        "## State Summary",
        "",
        markdown_table(["key", "value"], state_rows),
        "",
        "## Firmware Hits",
        "",
        "- current `/vendor`:",
        "\n".join(f"  - `{path}`" for path in (live.get("current_vendor_firmware_hits") or [])) or "  - none",
        "- isolated `sda29` vendor:",
        "\n".join(f"  - `{path}`" for path in (live.get("isolated_vendor_firmware_hits") or [])) or "  - none",
        "- isolated firmware tree sample:",
        "\n".join(f"  - `{path}`" for path in (live.get("isolated_firmware_tree_hits") or [])) or "  - none",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    live: dict[str, Any] = {}
    if args.command == "run":
        steps, live = collect_live(args, store)
    checks = build_checks(args, steps, live)
    decision, pass_ok, reason, next_step = decide(args.command, checks, live)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v728",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": checks,
        "live": live,
        "device_commands_executed": args.command == "run",
        "device_mutations": bool(live),
        "helper_identity_probe_executed": bool(live),
        "isolated_read_only_vendor_mount_executed": bool(live.get("isolated_vendor_mount_ok")),
        "subsystem_writes_executed": False,
        "subsys_modem_holder_executed": False,
        "esoc0_open_executed": False,
        "module_load_unload_executed": False,
        "cnss_daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    latest = repo_path("tmp/wifi/latest-v728-private-vendor-root.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"helper_identity_probe_executed: {manifest['helper_identity_probe_executed']}")
    print(f"isolated_read_only_vendor_mount_executed: {manifest['isolated_read_only_vendor_mount_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
