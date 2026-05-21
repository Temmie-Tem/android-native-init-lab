#!/usr/bin/env python3
"""V584 bounded firmware/modem mount parity proof.

This tool resolves Android `apnhlos` and `modem` block partitions from sysfs,
then optionally performs a bounded read-only mount proof for:

- `/vendor/firmware_mnt`
- `/vendor/firmware-modem`

It does not start daemons, write qcwlanstate, start Wi-Fi HAL, scan, connect,
run DHCP, change routes, or ping external targets.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v584-firmware-modem-mount-proof")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_V583_MANIFEST = Path("tmp/wifi/v583-firmware-mount-parity/manifest.json")

MOUNT_OPTIONS = "ro,shortname=lower,uid=0,gid=1000,dmask=227,fmask=337"
PROOF_BASE_PREFIX = "/tmp/a90-v584-"
PARTITION_TARGETS = {
    "apnhlos": "/vendor/firmware_mnt",
    "modem": "/vendor/firmware-modem",
}
TARGET_DIRS = ("/vendor", "/vendor/firmware_mnt", "/vendor/firmware-modem")
OBSERVE_MARKERS = {
    "qrtr_modem_readiness_rx": re.compile(r"qrtr: Modem QMI Readiness RX", re.I),
    "qrtr_modem_readiness_tx": re.compile(r"qrtr: Modem QMI Readiness TX", re.I),
    "sysmon_qmi": re.compile(r"sysmon-qmi", re.I),
    "service_notifier": re.compile(r"service-notifier", re.I),
    "wlan_pd": re.compile(r"wlan[_-]pd|msm/modem/wlan_pd", re.I),
    "qmi_server_connected": re.compile(r"qmi_server_connected", re.I),
    "wlfw": re.compile(r"\bWLFW\b|wlfw", re.I),
}
FORBIDDEN_COMMAND_TERMS = (
    "qcwlanstate",
    "IWifi",
    "iw ",
    "wpa_supplicant",
    "dhcp",
    "ping",
)


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


@dataclass(frozen=True)
class BlockPartition:
    partname: str
    devname: str
    major: str
    minor: str
    size_blocks: int | None


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v583-manifest", type=Path, default=DEFAULT_V583_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "preflight", "mount-proof"))
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             steps: list[dict[str, Any]],
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    validate_device_command(command)
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


def validate_device_command(command: list[str]) -> None:
    joined = " ".join(command)
    for term in FORBIDDEN_COMMAND_TERMS:
        if term in joined:
            raise RuntimeError(f"forbidden Wi-Fi bring-up command term in V584: {joined}")
    if command[:2] == ["run", "/cache/bin/toybox"] and len(command) >= 3:
        subcmd = command[2]
        if subcmd in {"mount", "rmdir", "rm", "dmesg", "find", "ls", "ln"}:
            return
        raise RuntimeError(f"unexpected toybox subcommand in V584: {joined}")
    if command[0] in {"version", "status", "selftest", "cat", "ls", "stat", "mkdir", "mknodb", "umount"}:
        return
    raise RuntimeError(f"unexpected command in V584: {joined}")


def parse_proc_partitions(text: str) -> dict[str, int]:
    partitions: dict[str, int] = {}
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) != 4 or not parts[0].isdigit() or not parts[1].isdigit() or not parts[2].isdigit():
            continue
        partitions[parts[3]] = int(parts[2])
    return partitions


def parse_key_values(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for raw in text.splitlines():
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def parse_block_uevents(steps: list[dict[str, Any]], partitions: dict[str, int]) -> dict[str, BlockPartition]:
    found: dict[str, BlockPartition] = {}
    for step in steps:
        name = str(step.get("name") or "")
        if not name.startswith("block-uevent-"):
            continue
        payload = str(step.get("payload") or "")
        values = parse_key_values(payload)
        partname = values.get("PARTNAME")
        devname = values.get("DEVNAME")
        major = values.get("MAJOR")
        minor = values.get("MINOR")
        if not partname or not devname or not major or not minor:
            continue
        found[partname] = BlockPartition(
            partname=partname,
            devname=devname,
            major=major,
            minor=minor,
            size_blocks=partitions.get(devname),
        )
    return found


def parse_mounts(text: str) -> dict[str, list[str]]:
    mounts: dict[str, list[str]] = {}
    for raw in text.splitlines():
        parts = raw.split()
        if len(parts) < 3:
            continue
        mounts.setdefault(parts[1], []).append(raw)
    return mounts


def parse_ls_symlink_target(text: str, path: str) -> str | None:
    pattern = re.compile(rf"(?:^|\s){re.escape(path)}\s+->\s+(\S+)")
    for raw in text.splitlines():
        match = pattern.search(raw)
        if match:
            return match.group(1)
    return None


def marker_counts(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in OBSERVE_MARKERS.items()}


def marker_delta(before: dict[str, int], after: dict[str, int]) -> dict[str, int]:
    return {name: max(0, after.get(name, 0) - before.get(name, 0)) for name in OBSERVE_MARKERS}


def capture_preflight(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    store.mkdir("native")
    run_step(args, store, steps, "version", ["version"], 15.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "selftest", ["selftest"], 25.0)
    run_step(args, store, steps, "proc-filesystems", ["cat", "/proc/filesystems"], 20.0)
    run_step(args, store, steps, "pre-proc-mounts", ["cat", "/proc/mounts"], 20.0)
    run_step(args, store, steps, "proc-partitions", ["cat", "/proc/partitions"], 20.0)
    run_step(args, store, steps, "pre-ls-root", ["run", args.toybox, "ls", "-l", "/"], 20.0)
    run_step(
        args,
        store,
        steps,
        "pre-ls-vendor-links",
        ["run", args.toybox, "ls", "-ld", "/vendor", "/mnt/system/vendor", "/system/vendor"],
        20.0,
    )
    for target in TARGET_DIRS + ("/firmware", "/bt_firmware"):
        run_step(args, store, steps, f"pre-stat-{safe_name(target)}", ["stat", target], 10.0)
    partitions = parse_proc_partitions(step_payload(steps, "proc-partitions"))
    for devname in sorted(partitions):
        if not re.match(r"^(sd[a-z][0-9]+|mmcblk[0-9]+p[0-9]+)$", devname):
            continue
        run_step(
            args,
            store,
            steps,
            f"block-uevent-{safe_name(devname)}",
            ["cat", f"/sys/class/block/{devname}/uevent"],
            8.0,
        )
    return summarize_preflight(steps)


def summarize_preflight(steps: list[dict[str, Any]]) -> dict[str, Any]:
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    filesystems = step_payload(steps, "proc-filesystems")
    pre_mounts_text = step_payload(steps, "pre-proc-mounts")
    pre_ls_vendor = step_payload(steps, "pre-ls-vendor-links")
    partitions = parse_proc_partitions(step_payload(steps, "proc-partitions"))
    found = parse_block_uevents(steps, partitions)
    pre_mounts = parse_mounts(pre_mounts_text)
    vendor_symlink_target = parse_ls_symlink_target(pre_ls_vendor, "/vendor")
    return {
        "native_healthy": "fail=0" in status and "fail=0" in selftest,
        "version_text": step_payload(steps, "version"),
        "vfat_supported": bool(re.search(r"(^|\s)vfat($|\s)", filesystems, re.M)),
        "pre_mount_hits": {target: target in pre_mounts for target in TARGET_DIRS + ("/firmware", "/bt_firmware")},
        "pre_mount_lines": {target: pre_mounts.get(target, []) for target in TARGET_DIRS + ("/firmware", "/bt_firmware")},
        "vendor_symlink_target": vendor_symlink_target,
        "vendor_rootfs_shim_required": vendor_symlink_target is not None,
        "vendor_rootfs_shim_allowed_target": vendor_symlink_target in {"/mnt/system/vendor", "/system/vendor"},
        "partitions": {name: asdict(found[name]) for name in sorted(found) if name in PARTITION_TARGETS},
        "partition_count": len(partitions),
    }


def proof_id(args: argparse.Namespace) -> str:
    if args.proof_id:
        return safe_name(args.proof_id)
    return "run-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")


def proof_node(base: str, partname: str) -> str:
    return f"{base}/{partname}"


def build_mount_commands(preflight: dict[str, Any], base: str) -> list[tuple[str, list[str], float]]:
    commands: list[tuple[str, list[str], float]] = []
    vendor_symlink_target = preflight.get("vendor_symlink_target")
    commands.append(("mkdir-proof-base", ["mkdir", base], 20.0))
    if vendor_symlink_target:
        commands.append(("replace-vendor-symlink", ["run", DEFAULT_TOYBOX, "rm", "-f", "/vendor"], 20.0))
    for dirname in TARGET_DIRS:
        commands.append((f"mkdir-{safe_name(dirname)}", ["mkdir", dirname], 20.0))
    for partname, target in PARTITION_TARGETS.items():
        partition = preflight.get("partitions", {}).get(partname)
        if not partition:
            continue
        node = proof_node(base, partname)
        commands.append((f"mknodb-{partname}", ["mknodb", node, str(partition["major"]), str(partition["minor"])], 20.0))
        commands.append((f"stat-node-{partname}", ["stat", node], 20.0))
        commands.append((
            f"mount-{partname}",
            ["run", DEFAULT_TOYBOX, "mount", "-t", "vfat", "-o", MOUNT_OPTIONS, node, target],
            45.0,
        ))
    return commands


def build_cleanup_commands(base: str, vendor_symlink_target: str | None) -> list[tuple[str, list[str], float]]:
    commands: list[tuple[str, list[str], float]] = []
    for target in reversed(tuple(PARTITION_TARGETS.values())):
        commands.append((f"cleanup-umount-{safe_name(target)}", ["umount", target], 25.0))
    commands.extend([
        ("cleanup-rmdir-vendor-firmware-modem", ["run", DEFAULT_TOYBOX, "rmdir", "/vendor/firmware-modem"], 20.0),
        ("cleanup-rmdir-vendor-firmware-mnt", ["run", DEFAULT_TOYBOX, "rmdir", "/vendor/firmware_mnt"], 20.0),
        ("cleanup-rmdir-vendor", ["run", DEFAULT_TOYBOX, "rmdir", "/vendor"], 20.0),
        ("cleanup-rm-proof-nodes", ["run", DEFAULT_TOYBOX, "rm", "-f", f"{base}/apnhlos", f"{base}/modem"], 20.0),
        ("cleanup-rmdir-proof-base", ["run", DEFAULT_TOYBOX, "rmdir", base], 20.0),
    ])
    if vendor_symlink_target:
        commands.append(("restore-vendor-symlink", ["run", DEFAULT_TOYBOX, "ln", "-s", vendor_symlink_target, "/vendor"], 20.0))
    return commands


def run_mount_proof(args: argparse.Namespace,
                    store: EvidenceStore,
                    steps: list[dict[str, Any]],
                    preflight: dict[str, Any]) -> dict[str, Any]:
    base = PROOF_BASE_PREFIX + proof_id(args)
    vendor_symlink_target = preflight.get("vendor_symlink_target")
    run_step(args, store, steps, "dmesg-before-proof", ["run", args.toybox, "dmesg"], 45.0)
    mount_results: list[str] = []
    cleanup_results: list[str] = []
    try:
        for name, command, timeout in build_mount_commands(preflight, base):
            item = run_step(args, store, steps, name, command, timeout)
            mount_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "mounted-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        run_step(args, store, steps, "mounted-firmware-mnt-root", ["ls", "/vendor/firmware_mnt"], 20.0)
        run_step(args, store, steps, "mounted-firmware-mnt-image", ["ls", "/vendor/firmware_mnt/image"], 20.0)
        run_step(args, store, steps, "mounted-firmware-modem-root", ["ls", "/vendor/firmware-modem"], 20.0)
        run_step(args, store, steps, "mounted-firmware-modem-image", ["ls", "/vendor/firmware-modem/image"], 20.0)
        run_step(args, store, steps, "dmesg-during-proof", ["run", args.toybox, "dmesg"], 45.0)
    finally:
        for name, command, timeout in build_cleanup_commands(base, vendor_symlink_target):
            item = run_step(args, store, steps, name, command, timeout)
            cleanup_results.append(f"{name}:{item.get('status')}:{item.get('rc')}")
        run_step(args, store, steps, "post-proc-mounts", ["cat", "/proc/mounts"], 20.0)
        run_step(
            args,
            store,
            steps,
            "post-ls-vendor-links",
            ["run", args.toybox, "ls", "-ld", "/vendor", "/mnt/system/vendor", "/system/vendor"],
            20.0,
        )
        run_step(args, store, steps, "post-status", ["status"], 25.0)
    return summarize_proof(steps, mount_results, cleanup_results, base)


def summarize_proof(steps: list[dict[str, Any]],
                    mount_results: list[str],
                    cleanup_results: list[str],
                    base: str) -> dict[str, Any]:
    mounted_mounts = parse_mounts(step_payload(steps, "mounted-proc-mounts"))
    post_mounts = parse_mounts(step_payload(steps, "post-proc-mounts"))
    post_vendor_symlink_target = parse_ls_symlink_target(step_payload(steps, "post-ls-vendor-links"), "/vendor")
    before_markers = marker_counts(step_payload(steps, "dmesg-before-proof"))
    during_markers = marker_counts(step_payload(steps, "dmesg-during-proof"))
    return {
        "base": base,
        "mount_results": mount_results,
        "cleanup_results": cleanup_results,
        "mounted_hits": {target: target in mounted_mounts for target in PARTITION_TARGETS.values()},
        "mounted_lines": {target: mounted_mounts.get(target, []) for target in PARTITION_TARGETS.values()},
        "post_mount_hits": {target: target in post_mounts for target in TARGET_DIRS},
        "post_vendor_symlink_target": post_vendor_symlink_target,
        "marker_before": before_markers,
        "marker_during": during_markers,
        "marker_delta": marker_delta(before_markers, during_markers),
        "post_healthy": "fail=0" in step_payload(steps, "post-status"),
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(command: str,
                 v583: dict[str, Any],
                 preflight: dict[str, Any],
                 proof: dict[str, Any] | None) -> list[Check]:
    checks: list[Check] = []
    if command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run V584 preflight")
        return checks
    add_check(
        checks,
        "v583-reference-ready",
        "pass" if v583.get("decision") == "v583-native-firmware-modem-mount-parity-gap-classified" else "blocked",
        "blocker",
        f"decision={v583.get('decision')} pass={v583.get('pass')}",
        [str(v583.get("path"))],
        "run V583 before V584",
    )
    add_check(
        checks,
        "native-current-health",
        "pass" if preflight.get("native_healthy") else "blocked",
        "blocker",
        f"native_healthy={preflight.get('native_healthy')}",
        [],
        "restore native baseline before mount proof",
    )
    add_check(
        checks,
        "vfat-supported",
        "pass" if preflight.get("vfat_supported") else "blocked",
        "blocker",
        f"vfat_supported={preflight.get('vfat_supported')}",
        [],
        "kernel must support vfat to mirror Android firmware mounts",
    )
    parts = preflight.get("partitions") or {}
    add_check(
        checks,
        "apnhlos-modem-partitions-resolved",
        "pass" if "apnhlos" in parts and "modem" in parts else "blocked",
        "blocker",
        f"apnhlos={parts.get('apnhlos')} modem={parts.get('modem')}",
        [],
        "resolve PARTNAME through /sys/class/block/*/uevent",
    )
    pre_hits = preflight.get("pre_mount_hits") or {}
    already_mounted = [target for target in PARTITION_TARGETS.values() if pre_hits.get(target)]
    add_check(
        checks,
        "firmware-targets-not-already-mounted",
        "pass" if not already_mounted else "blocked",
        "blocker",
        f"already_mounted={already_mounted}",
        sum((preflight.get("pre_mount_lines") or {}).values(), []),
        "inspect existing mount state before changing it",
    )
    shim_required = bool(preflight.get("vendor_rootfs_shim_required"))
    shim_allowed = bool(preflight.get("vendor_rootfs_shim_allowed_target"))
    add_check(
        checks,
        "vendor-rootfs-shim-safe",
        "pass" if not shim_required or shim_allowed else "blocked",
        "blocker",
        f"required={shim_required} target={preflight.get('vendor_symlink_target')} allowed={shim_allowed}",
        [],
        "only replace /vendor symlink when it points at the known native system vendor alias",
    )
    if proof is None:
        return checks
    mounted_hits = proof.get("mounted_hits") or {}
    post_hits = proof.get("post_mount_hits") or {}
    expected_vendor_symlink = preflight.get("vendor_symlink_target")
    delta = proof.get("marker_delta") or {}
    add_check(
        checks,
        "readonly-mounts-established",
        "pass" if all(mounted_hits.get(target) for target in PARTITION_TARGETS.values()) else "blocked",
        "blocker",
        f"mounted_hits={mounted_hits}",
        sum((proof.get("mounted_lines") or {}).values(), []),
        "fix read-only mount parity before companion retry",
    )
    add_check(
        checks,
        "cleanup-complete",
        "pass" if not any(post_hits.get(target) for target in PARTITION_TARGETS.values()) else "blocked",
        "blocker",
        f"post_mount_hits={post_hits}",
        proof.get("cleanup_results", []),
        "reboot or manually unmount before continuing",
    )
    add_check(
        checks,
        "vendor-symlink-restored",
        "pass" if not expected_vendor_symlink or proof.get("post_vendor_symlink_target") == expected_vendor_symlink else "blocked",
        "blocker",
        f"expected={expected_vendor_symlink} actual={proof.get('post_vendor_symlink_target')}",
        [],
        "restore /vendor symlink or reboot before continuing",
    )
    add_check(
        checks,
        "post-health",
        "pass" if proof.get("post_healthy") else "blocked",
        "blocker",
        f"post_healthy={proof.get('post_healthy')}",
        [],
        "restore native baseline before continuing",
    )
    add_check(
        checks,
        "qrtr-readiness-delta",
        "pass" if any(value > 0 for value in delta.values()) else "warn",
        "warning",
        f"marker_delta={delta}",
        [],
        "if no delta, combine mount parity with next bounded companion start-only gate",
    )
    return checks


def blocking_checks(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check], proof: dict[str, Any] | None) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v584-firmware-modem-mount-proof-plan-ready", True, "plan-only; no device command executed", "run V584 preflight"
    blockers = blocking_checks(checks)
    if blockers:
        return "v584-firmware-modem-mount-proof-blocked", False, "blocked by " + ", ".join(blockers), "clear blockers before live mount proof"
    if command == "preflight":
        return "v584-firmware-modem-mount-proof-preflight-ready", True, "apnhlos/modem read-only mount proof prerequisites are present", "run V584 mount-proof; still no daemon start or Wi-Fi bring-up"
    delta = (proof or {}).get("marker_delta") or {}
    if any(value > 0 for value in delta.values()):
        return "v584-firmware-modem-mount-proof-readiness-delta", True, "read-only firmware/modem mount parity completed and QRTR/modem marker delta appeared", "plan next gate around bounded companion start after mount parity"
    return "v584-firmware-modem-mount-proof-no-readiness-delta", True, "read-only firmware/modem mount parity completed and cleaned up, but no QRTR/modem marker delta appeared without companion activity", "plan next gate to combine mount parity with bounded companion start-only; keep qcwlanstate/IWifi/scan/connect blocked"


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    preflight = manifest.get("preflight") or {}
    proof = manifest.get("proof") or {}
    preflight_rows = [
        ["native_healthy", preflight.get("native_healthy", "")],
        ["vfat_supported", preflight.get("vfat_supported", "")],
        ["partitions", preflight.get("partitions", {})],
        ["pre_mount_hits", preflight.get("pre_mount_hits", {})],
        ["vendor_symlink_target", preflight.get("vendor_symlink_target", "")],
        ["vendor_rootfs_shim_required", preflight.get("vendor_rootfs_shim_required", "")],
    ]
    proof_rows = [
        ["base", proof.get("base", "")],
        ["mounted_hits", proof.get("mounted_hits", {})],
        ["post_mount_hits", proof.get("post_mount_hits", {})],
        ["post_vendor_symlink_target", proof.get("post_vendor_symlink_target", "")],
        ["marker_delta", proof.get("marker_delta", {})],
        ["post_healthy", proof.get("post_healthy", "")],
    ]
    return "\n".join([
        "# V584 Firmware/Modem Mount Parity Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## Preflight",
        "",
        markdown_table(["key", "value"], preflight_rows),
        "",
        "## Proof",
        "",
        markdown_table(["key", "value"], proof_rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v583 = load_json_if_exists(args.v583_manifest)
    steps: list[dict[str, Any]] = []
    preflight: dict[str, Any] = {}
    proof: dict[str, Any] | None = None
    if args.command in {"preflight", "mount-proof"}:
        preflight = capture_preflight(args, store, steps)
    pre_checks = build_checks(args.command, v583, preflight, None)
    if args.command == "mount-proof" and not blocking_checks(pre_checks):
        proof = run_mount_proof(args, store, steps, preflight)
    checks = build_checks(args.command, v583, preflight, proof)
    decision, pass_ok, reason, next_step = decide(args.command, checks, proof)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "v583_manifest": {
            "exists": v583.get("exists"),
            "path": v583.get("path"),
            "decision": v583.get("decision"),
            "pass": v583.get("pass"),
            "reason": v583.get("reason"),
        },
        "preflight": preflight,
        "proof": proof or {},
        "device_commands_executed": args.command in {"preflight", "mount-proof"},
        "device_mutations": args.command == "mount-proof" and proof is not None,
        "mount_unmount_executed": args.command == "mount-proof" and proof is not None,
        "partition_write_executed": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
