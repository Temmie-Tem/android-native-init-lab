#!/usr/bin/env python3
"""V674 post-HAL/wificond runtime classifier.

This host-only classifier inspects the V673 V671-arm evidence after Wi-Fi HAL
legacy/ext, wificond, and fresh cnss-daemon have started. It does not contact
the device, start services, scan, connect, run DHCP, change routes, use
credentials, or ping externally.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v674-post-hal-wificond-classifier")
DEFAULT_V673_MANIFEST = Path("tmp/wifi/v673-same-helper-replay-live-retry2/manifest.json")
DEFAULT_V671_ARM_MANIFEST = Path("tmp/wifi/v673-same-helper-replay-live-retry2/arm-v671-v111/live/manifest.json")

CHILDREN = ("wifi_hal_legacy", "wifi_hal_ext", "wificond", "cnss_daemon_retry")
PREEXEC_KEYS = (
    "preexec_status",
    "selinux_exec.ok",
    "setresuid.ok",
    "setresgid.ok",
    "setgroups.ok",
    "pr_set_keepcaps.ok",
)
FORBIDDEN_ACTIONS = (
    "device command",
    "service start",
    "supplicant or hostapd start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "boot image or partition write",
)
PROPERTY_DENIAL_RE = re.compile(
    r'(?:Could not find context for property|Access denied finding property) "([^"]+)"',
    re.I,
)
PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("property_context_missing_or_denied", re.compile(r"Could not find context for property|Access denied finding property", re.I)),
    ("binder_failure", re.compile(r"binder:.*transaction failed|transaction failed .*?-22|ioctl .* returned -22", re.I)),
    ("hwbinder_path", re.compile(r"/dev/hwbinder")),
    ("binder_path", re.compile(r"/dev/binder")),
    ("vndbinder_path", re.compile(r"/dev/vndbinder")),
    ("wlfw", re.compile(r"wlfw|WLFW|service 69|QMI Server Connected", re.I)),
    ("bdf", re.compile(r"BDF|bdwlan|regdb", re.I)),
    ("wlan0", re.compile(r"\bwlan0\b", re.I)),
    ("selinux_denied", re.compile(r"avc:|SELinux.*denied", re.I)),
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v673-manifest", type=Path, default=DEFAULT_V673_MANIFEST)
    parser.add_argument("--v671-arm-manifest", type=Path, default=DEFAULT_V671_ARM_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def int_value(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw in text.replace("\0", "\n").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)=(.*)$", raw.strip())
        if match:
            keys[match.group(1)] = match.group(2).strip()
    return keys


def helper_text(arm: dict[str, Any]) -> str:
    return str((arm.get("live") or {}).get("helper_stdout_stderr") or "")


def evidence_dir(path: Path, manifest: dict[str, Any]) -> Path:
    evidence = manifest.get("evidence") or manifest.get("out_dir")
    if evidence:
        return repo_path(Path(str(evidence)))
    return repo_path(path).parent


def dmesg_text(arm_path: Path, arm: dict[str, Any]) -> str:
    return read_text(evidence_dir(arm_path, arm) / "native" / "dmesg-delta.txt")


def pattern_counts(text: str) -> dict[str, int]:
    return {name: len(pattern.findall(text)) for name, pattern in PATTERNS}


def property_denials(text: str) -> dict[str, Any]:
    names = [match.group(1) for match in PROPERTY_DENIAL_RE.finditer(text)]
    counts = collections.Counter(names)
    return {
        "total": len(names),
        "unique": len(counts),
        "top": [[name, count] for name, count in counts.most_common(16)],
    }


def child_surface(arm: dict[str, Any], keys: dict[str, str]) -> dict[str, Any]:
    surface = ((arm.get("live") or {}).get("v671_android_userspace_surface") or {})
    children = surface.get("children") or {}
    result: dict[str, Any] = {}
    for child in CHILDREN:
        prefix = f"wifi_hal_composite_child.{child}."
        fd_prefix = f"capture.wifi_hal_composite_{child}.fd_links."
        child_info = children.get(child) or {}
        result[child] = {
            "start_order": child_info.get("start_order", ""),
            "observable": child_info.get("observable", ""),
            "postflight_safe": child_info.get("postflight_safe", ""),
            "signal": child_info.get("signal", ""),
            "preexec_status": keys.get(prefix + "preexec_status", ""),
            "selinux_current": keys.get(prefix + "selinux.current", ""),
            "selinux_exec": keys.get(prefix + "selinux.exec", ""),
            "uid": keys.get(prefix + "expected.uid", ""),
            "gid": keys.get(prefix + "expected.gid", ""),
            "groups": keys.get(prefix + "expected.groups", ""),
            "cap": keys.get(prefix + "expected.cap", ""),
            "fd_count": keys.get(fd_prefix + "count", ""),
            "socket_count": keys.get(fd_prefix + "socket_count", ""),
            "hwbinder_fd": any(
                value.endswith("/dev/hwbinder")
                for key, value in keys.items()
                if key.startswith(fd_prefix) and key.endswith(".target")
            ),
            "binder_fd": any(
                value.endswith("/dev/binder")
                for key, value in keys.items()
                if key.startswith(fd_prefix) and key.endswith(".target")
            ),
            "vndbinder_fd": any(
                value.endswith("/dev/vndbinder")
                for key, value in keys.items()
                if key.startswith(fd_prefix) and key.endswith(".target")
            ),
            "preexec_ready": all(
                keys.get(prefix + key) in {"pass", "1"}
                for key in PREEXEC_KEYS
            ),
        }
    return result


def counts_from_arm(arm: dict[str, Any]) -> dict[str, int]:
    live = arm.get("live") or {}
    counts = live.get("v655_counts") or live.get("v668_counts") or {}
    markers = ((live.get("markers") or {}).get("counts") or {})
    return {
        "service_notifier_180": int_value(counts.get("service_notifier_180")),
        "service_notifier_74": int_value(counts.get("service_notifier_74")),
        "cnss_binder_transaction_failed": int_value(counts.get("cnss_binder_transaction_failed")),
        "binder_transaction_failed": int_value(counts.get("binder_transaction_failed")),
        "kernel_warning": int_value(counts.get("kernel_warning")),
        "wlfw_start": int_value(counts.get("wlfw_start")),
        "wlfw_service_request": int_value(counts.get("wlfw_service_request")),
        "bdf_regdb": int_value(counts.get("bdf_regdb")),
        "bdf_bdwlan": int_value(counts.get("bdf_bdwlan")),
        "wlan_fw_ready": int_value(counts.get("wlan_fw_ready")),
        "wlan0": int_value(counts.get("wlan0")),
        "marker_wlfw": int_value(markers.get("wlfw")),
        "marker_bdf": int_value(markers.get("bdf")),
        "marker_wlan0": int_value(markers.get("wlan0")),
    }


def property_shim(keys: dict[str, str]) -> dict[str, Any]:
    prefix = "wifi_hal_composite_start.property_service_shim."
    request_count = int_value(keys.get(prefix + "request_count"))
    requests = []
    for idx in range(1, request_count + 1):
        requests.append({
            "name": keys.get(f"{prefix}request.{idx}.name", ""),
            "allowed": keys.get(f"{prefix}request.{idx}.allowed", ""),
            "result": keys.get(f"{prefix}request.{idx}.result", ""),
        })
    return {
        "started": keys.get(prefix + "started", ""),
        "socket": keys.get(prefix + "socket", ""),
        "postflight_safe": keys.get(prefix + "postflight_safe", ""),
        "allowlist": keys.get(prefix + "allowlist", ""),
        "request_count": request_count,
        "requests": requests,
    }


def build_checks(v673: dict[str, Any],
                 arm: dict[str, Any],
                 children: dict[str, Any],
                 counts: dict[str, int],
                 shim: dict[str, Any],
                 helper_counts: dict[str, int],
                 dmesg_counts: dict[str, int],
                 prop_denials: dict[str, Any]) -> list[dict[str, Any]]:
    child_started = all((children.get(child) or {}).get("start_order") for child in CHILDREN)
    child_preexec_ready = all((children.get(child) or {}).get("preexec_ready") for child in CHILDREN)
    binder_surface_ready = (
        children.get("wifi_hal_legacy", {}).get("hwbinder_fd")
        and children.get("wifi_hal_ext", {}).get("hwbinder_fd")
        and children.get("wificond", {}).get("binder_fd")
        and children.get("wificond", {}).get("hwbinder_fd")
    )
    no_wifi_advance = all(counts.get(key, 0) == 0 for key in (
        "wlfw_start",
        "wlfw_service_request",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0",
        "marker_wlfw",
        "marker_bdf",
        "marker_wlan0",
    ))
    return [
        {
            "name": "v673-post-hal-input-ready",
            "status": "pass" if v673.get("decision") == "v673-android-userspace-no-wlfw-advance" and arm.get("decision") == "v671-android-userspace-no-wlfw-advance" else "blocked",
            "detail": {"v673": v673.get("decision"), "arm": arm.get("decision")},
            "next_step": "run V673 before V674",
        },
        {
            "name": "android-userspace-children-started",
            "status": "pass" if child_started else "blocked",
            "detail": {name: (children.get(name) or {}).get("start_order", "") for name in CHILDREN},
            "next_step": "do not classify post-HAL gap until all intended children start",
        },
        {
            "name": "child-preexec-identity-ready",
            "status": "pass" if child_preexec_ready else "blocked",
            "detail": {name: {key: (children.get(name) or {}).get(key) for key in ("preexec_status", "selinux_exec", "uid", "gid", "cap")} for name in CHILDREN},
            "next_step": "fix UID/GID/capability/SELinux transition before retrying HAL",
        },
        {
            "name": "binder-fd-surface-present",
            "status": "pass" if binder_surface_ready else "blocked",
            "detail": {name: {key: (children.get(name) or {}).get(key) for key in ("binder_fd", "hwbinder_fd", "vndbinder_fd", "socket_count")} for name in CHILDREN},
            "next_step": "fix binder/hwbinder device materialization before retrying HAL",
        },
        {
            "name": "property-service-shim-observed",
            "status": "pass" if shim.get("started") == "1" and shim.get("postflight_safe") == "1" else "blocked",
            "detail": shim,
            "next_step": "restore property service shim before retrying HAL",
        },
        {
            "name": "wifi-lower-markers-absent",
            "status": "pass" if no_wifi_advance else "review",
            "detail": counts,
            "next_step": "if WLFW/BDF/wlan0 advanced, move to scan/connect gate",
        },
        {
            "name": "property-context-runtime-gap",
            "status": "finding" if prop_denials["total"] > 0 else "pass",
            "detail": {"denials": prop_denials, "helper_property_denial_lines": helper_counts.get("property_context_missing_or_denied", 0)},
            "next_step": "materialize Android property_contexts/property area more completely before another HAL runtime attempt",
        },
        {
            "name": "binder-transaction-runtime-gap",
            "status": "finding" if dmesg_counts.get("binder_failure", 0) > 0 else "pass",
            "detail": {"dmesg_binder_failures": dmesg_counts.get("binder_failure", 0), "counts": counts},
            "next_step": "capture service-manager registration and binder transaction target state",
        },
    ]


def blockers(checks: list[dict[str, Any]]) -> list[str]:
    return [check["name"] for check in checks if check["status"] == "blocked"]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v674-post-hal-wificond-plan-ready",
            True,
            "plan-only; no evidence classification or device command executed",
            "run V674 host-only classifier",
        )
    blocked = blockers(checks)
    if blocked:
        return (
            "v674-post-hal-wificond-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh V673 post-HAL evidence before selecting the next live gate",
        )
    finding_names = [check["name"] for check in checks if check["status"] == "finding"]
    if "property-context-runtime-gap" in finding_names or "binder-transaction-runtime-gap" in finding_names:
        return (
            "v674-post-hal-property-binder-gap-classified",
            True,
            "HAL/wificond children start with expected identity and binder fds, but WLFW/BDF/wlan0 stay absent while property-context denials and binder failures remain",
            "plan V675 targeted property/binder runtime repair or capture before any supplicant/scan/connect attempt",
        )
    return (
        "v674-post-hal-wificond-unclassified",
        False,
        "post-HAL children started and lower Wi-Fi markers stayed absent, but no property/binder finding was identified",
        "inspect full helper transcript and add a narrower classifier",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v673 = load_json(args.v673_manifest)
    arm = load_json(args.v671_arm_manifest)
    text = helper_text(arm)
    keys = parse_keys(text)
    dmesg = dmesg_text(args.v671_arm_manifest, arm)
    children = child_surface(arm, keys)
    counts = counts_from_arm(arm)
    shim = property_shim(keys)
    helper_counts = pattern_counts(text)
    dmesg_counts = pattern_counts(dmesg)
    prop_denials = property_denials(text)
    checks = build_checks(v673, arm, children, counts, shim, helper_counts, dmesg_counts, prop_denials)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v674",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v673_manifest": str(repo_path(args.v673_manifest)),
            "v671_arm_manifest": str(repo_path(args.v671_arm_manifest)),
        },
        "checks": checks,
        "children": children,
        "counts": counts,
        "property_service_shim": shim,
        "helper_pattern_counts": helper_counts,
        "dmesg_pattern_counts": dmesg_counts,
        "property_denials": prop_denials,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def check_rows(checks: list[dict[str, Any]]) -> list[list[str]]:
    return [[check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]] for check in checks]


def child_rows(children: dict[str, Any]) -> list[list[str]]:
    return [
        [
            name,
            str(data.get("start_order", "")),
            str(data.get("observable", "")),
            str(data.get("preexec_ready", "")),
            str(data.get("selinux_exec", "")),
            str(data.get("binder_fd", "")),
            str(data.get("hwbinder_fd", "")),
            str(data.get("socket_count", "")),
            str(data.get("postflight_safe", "")),
        ]
        for name, data in sorted(children.items())
    ]


def count_rows(title: str, counts: dict[str, int]) -> list[list[str]]:
    return [[title, key, str(value)] for key, value in sorted(counts.items())]


def render_summary(manifest: dict[str, Any]) -> str:
    return "\n".join([
        "# V674 Post-HAL/wificond Runtime Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows(manifest["checks"])),
        "",
        "## Children",
        "",
        markdown_table(["child", "start", "observable", "preexec", "SELinux exec", "binder", "hwbinder", "sockets", "postflight"], child_rows(manifest["children"])),
        "",
        "## Counts",
        "",
        markdown_table(["surface", "name", "count"], count_rows("wifi", manifest["counts"]) + count_rows("helper", manifest["helper_pattern_counts"]) + count_rows("dmesg", manifest["dmesg_pattern_counts"])),
        "",
        "## Property Denials",
        "",
        f"- total: `{manifest['property_denials']['total']}`",
        f"- unique: `{manifest['property_denials']['unique']}`",
        "",
        markdown_table(["property", "count"], [[name, str(count)] for name, count in manifest["property_denials"]["top"]]),
        "",
        "## Interpretation",
        "",
        "- HAL legacy/ext, `wificond`, and retry `cnss-daemon` start with expected UID/GID/capability/SELinux setup.",
        "- Binder/hwbinder file descriptors are present for the relevant children.",
        "- WLFW/BDF/firmware-ready/`wlan0` remain absent.",
        "- The strongest next blocker is property-context/property-area completeness plus binder registration behavior, not Wi-Fi scan/connect.",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
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
