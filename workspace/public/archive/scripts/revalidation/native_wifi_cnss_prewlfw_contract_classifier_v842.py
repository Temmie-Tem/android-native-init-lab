#!/usr/bin/env python3
"""V842 host-only CNSS daemon pre-WLFW contract classifier.

V841 selected the gap where native `cnss-daemon` reaches netlink/CLD80211 but
never emits `wlfw_start`, while Android emits `wlfw_start` before WLAN-PD UP.
This classifier checks whether the remaining blocker is still a coarse launch
contract gap or a narrower live pre-WLFW stall inside the already-launched
daemon.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v842-cnss-prewlfw-contract-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v842-cnss-prewlfw-contract-classifier.txt")

DEFAULT_V841_MANIFEST = Path("tmp/wifi/v841-post-v840-trigger-gap-classifier/manifest.json")
DEFAULT_V840_MANIFEST = Path("tmp/wifi/v840-provider-first-prearmed-listener-live/manifest.json")
DEFAULT_V704_MANIFEST = Path("tmp/wifi/v704-cnss-retry-stall-snapshot/manifest.json")
DEFAULT_V697_MANIFEST = Path("tmp/wifi/v697-cnss-binder-runtime-target-classifier-rerun/manifest.json")
DEFAULT_V525_ROOT = Path("tmp/wifi/v526-android-companion-identity-handoff-run/v525-android-companion-identity-run")
DEFAULT_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)

EXPECTED = {
    "v841": "v841-cnss-wlfw-start-gap-selected",
    "v840": "v840-provider-first-prearmed-no-indication",
    "v704": "v704-cnss-daemon-alive-pre-wlfw-stall-classified",
    "v697": "v697-cnss-vndbinder-transaction-framing-targeted",
    "v525": "v525-companion-identity-captured",
    "v622": "v622-mdm-helper-post-notifier-not-root-trigger",
}

CNSS_SERVICE_RE = re.compile(
    r"service\s+cnss-daemon\s+(?P<cmd>/system/vendor/bin/cnss-daemon\s+-n\s+-l)"
    r"(?P<body>.*?)(?:\n### |\Z)",
    re.S,
)
STATUS_RE = re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_]*):\s*(?P<value>.*)$")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v841-manifest", type=Path, default=DEFAULT_V841_MANIFEST)
    parser.add_argument("--v840-manifest", type=Path, default=DEFAULT_V840_MANIFEST)
    parser.add_argument("--v704-manifest", type=Path, default=DEFAULT_V704_MANIFEST)
    parser.add_argument("--v697-manifest", type=Path, default=DEFAULT_V697_MANIFEST)
    parser.add_argument("--v525-root", type=Path, default=DEFAULT_V525_ROOT)
    parser.add_argument("--v622-manifest", type=Path, default=DEFAULT_V622_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().replace(b"\0", b"\n").decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    text = read_text(path)
    if not text:
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def nested(data: dict[str, Any], *keys: str) -> Any:
    value: Any = data
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def int_value(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(str(value), 0)
    except (TypeError, ValueError):
        return default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    return str(value).strip().lower() in {"1", "true", "yes", "pass"}


def input_item(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "path": data.get("path"),
        "exists": data.get("exists", False),
        "decision": data.get("decision", ""),
        "pass": bool_value(data.get("pass")),
        "reason": data.get("reason", ""),
        "next_step": data.get("next_step", ""),
    }


def parse_status_block(text: str, process_name: str) -> dict[str, str]:
    marker = f"### process={process_name} "
    start = text.find(marker)
    if start < 0:
        return {}
    next_marker = text.find("### process=", start + len(marker))
    block = text[start:] if next_marker < 0 else text[start:next_marker]
    parsed: dict[str, str] = {}
    for line in block.splitlines():
        if line.startswith("cmdline="):
            parsed["cmdline"] = line.removeprefix("cmdline=").strip()
        elif line.startswith("exe="):
            parsed["exe"] = line.removeprefix("exe=").strip()
        elif line.startswith("attr_current="):
            parsed["attr_current"] = line.removeprefix("attr_current=").strip()
        else:
            match = STATUS_RE.match(line)
            if match:
                parsed[match.group("key")] = match.group("value").strip()
    return parsed


def android_contract(v525_root: Path, v622: dict[str, Any]) -> dict[str, Any]:
    root = repo_path(v525_root)
    service_blocks = read_text(v525_root / "android/commands/service-blocks.txt")
    target_identity = read_text(v525_root / "android/commands/target-proc-identity.txt")
    service_props = read_text(v525_root / "android/commands/service-props.txt")
    dmesg = read_text(v525_root / "android/commands/companion-dmesg-identity.txt")
    match = CNSS_SERVICE_RE.search(service_blocks)
    body = match.group("body") if match else ""
    status = parse_status_block(target_identity, "cnss-daemon")
    v622_summary = v622.get("android_summary") if isinstance(v622.get("android_summary"), dict) else {}
    counts = v622_summary.get("counts") if isinstance(v622_summary.get("counts"), dict) else {}
    deltas = v622_summary.get("deltas_ms") if isinstance(v622_summary.get("deltas_ms"), dict) else {}
    timing = v622_summary.get("timing") if isinstance(v622_summary.get("timing"), dict) else {}
    return {
        "root": str(root),
        "service_block_found": bool(match),
        "service_command": match.group("cmd") if match else "",
        "service_body_has_system_user": "user system" in body,
        "service_body_has_expected_groups": "group system inet net_admin wifi" in body,
        "service_body_has_net_admin": "capabilities NET_ADMIN" in body,
        "props_running": "[init.svc.cnss-daemon]: [running]" in service_props,
        "boottime_present": "[ro.boottime.cnss-daemon]:" in service_props,
        "identity": {
            "cmdline": status.get("cmdline", ""),
            "exe": status.get("exe", ""),
            "attr_current": status.get("attr_current", ""),
            "uid": status.get("Uid", ""),
            "gid": status.get("Gid", ""),
            "groups": status.get("Groups", ""),
            "cap_eff": status.get("CapEff", ""),
            "cap_prm": status.get("CapPrm", ""),
            "cap_amb": status.get("CapAmb", ""),
        },
        "dmesg_counts": {
            "init_starting_service": len(re.findall(r"init: starting service 'cnss-daemon'", dmesg)),
            "netlink_create": len(re.findall(r"netlink_create\\(694\\).*comm:\\s*cnss-daemon", dmesg)),
            "cld80211": len(re.findall(r"cld80211", dmesg)),
            "wlfw_start": len(re.findall(r"wlfw_start", dmesg)),
            "wlfw_service_request": len(re.findall(r"wlfw_service_request", dmesg)),
            "bdf": len(re.findall(r"BDF file", dmesg)),
        },
        "v622_counts": {
            key: int_value(counts.get(key))
            for key in (
                "cnss_daemon_netlink",
                "wlfw_start",
                "wlfw_thread",
                "wlan_pd",
                "qmi_server_connected",
                "bdf_regdb",
                "bdf_bdwlan",
                "wlan_fw_ready",
                "wlan0",
            )
        },
        "v622_timing": {
            "service180_to_wlfw_start_ms": deltas.get("service_notifier_180_to_wlfw_start"),
            "service180_to_wlan_pd_ms": deltas.get("service_notifier_180_to_wlan_pd"),
            "cnss_daemon_boottime_ms": timing.get("cnss_daemon_boottime_ms"),
            "cnss_diag_boottime_ms": timing.get("cnss_diag_boottime_ms"),
        },
    }


def native_contract(v840: dict[str, Any], v704: dict[str, Any], v697: dict[str, Any]) -> dict[str, Any]:
    v840_provider = nested(v840, "provider_first_prearmed", "provider_manifest") or {}
    v840_live = v840_provider.get("live") if isinstance(v840_provider.get("live"), dict) else {}
    v840_counts = v840_live.get("v655_counts") if isinstance(v840_live.get("v655_counts"), dict) else {}
    v704_surface = v704.get("surface") if isinstance(v704.get("surface"), dict) else {}
    v704_proc = v704_surface.get("proc") if isinstance(v704_surface.get("proc"), dict) else {}
    v704_fd = v704_surface.get("fd") if isinstance(v704_surface.get("fd"), dict) else {}
    v704_helper = v704_surface.get("helper") if isinstance(v704_surface.get("helper"), dict) else {}
    v697_surface = v697.get("surface") if isinstance(v697.get("surface"), dict) else {}
    v697_provider = v697_surface.get("provider") if isinstance(v697_surface.get("provider"), dict) else {}
    v697_dmesg = v697_surface.get("dmesg") if isinstance(v697_surface.get("dmesg"), dict) else {}
    return {
        "v840_counts": {
            key: int_value(v840_counts.get(key))
            for key in (
                "service_notifier_180",
                "service_notifier_74",
                "cnss_daemon_netlink",
                "cnss_daemon_cld80211",
                "cnss_binder_transaction_failed",
                "binder_transaction_failed",
                "wlfw_start",
                "wlfw_service_request",
                "wlan_pd",
                "qmi_server_connected",
                "bdf_regdb",
                "bdf_bdwlan",
                "wlan_fw_ready",
                "wlan0",
            )
        },
        "v840_surface": {
            "order": nested(v840_live, "v655_surface", "order") or "",
            "helper_result": v840_live.get("helper_result", ""),
            "mss_after_companion": v840_live.get("mss_after_companion", ""),
            "mdm3_after_companion": v840_live.get("mdm3_after_companion", ""),
        },
        "v704_proc": {
            "state": v704_proc.get("state", ""),
            "threads": int_value(v704_proc.get("threads")),
            "uid": v704_proc.get("uid", ""),
            "gid": v704_proc.get("gid", ""),
            "groups": v704_proc.get("groups", ""),
            "attr_current": v704_proc.get("attr_current", ""),
            "cap_eff": v704_proc.get("cap_eff", ""),
            "cap_prm": v704_proc.get("cap_prm", ""),
            "cap_amb": v704_proc.get("cap_amb", ""),
        },
        "v704_fd": {
            "count": int_value(v704_fd.get("count")),
            "socket_count": int_value(v704_fd.get("socket_count")),
            "pipe_count": int_value(v704_fd.get("pipe_count")),
            "vndbinder_present": bool_value(v704_fd.get("vndbinder_present")),
            "tty_present": bool_value(v704_fd.get("tty_present")),
        },
        "v704_helper": {
            "retry_pid": v704_helper.get("retry_pid", ""),
            "result": v704_helper.get("result", ""),
            "reason": v704_helper.get("reason", ""),
            "timed_out": bool_value(v704_helper.get("timed_out")),
            "preexec_status": v704_helper.get("preexec_status", ""),
            "selinux_exec": v704_helper.get("selinux_exec", ""),
        },
        "v697_provider": {
            "literal_count": int_value(v697_provider.get("literal_count")),
        },
        "v697_dmesg": {
            "cnss_binder_29189_minus_22": int_value(v697_dmesg.get("cnss_binder_29189_minus_22")),
            "generic_context_manager_ioctl_minus_22": int_value(v697_dmesg.get("generic_context_manager_ioctl_minus_22")),
            "wlfw_start": int_value(v697_dmesg.get("wlfw_start")),
        },
    }


def candidate(name: str, classification: str, reason: str, next_step: str) -> dict[str, str]:
    return {
        "candidate": name,
        "classification": classification,
        "reason": reason,
        "next_step": next_step,
    }


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v841 = load_json(args.v841_manifest)
    v840 = load_json(args.v840_manifest)
    v704 = load_json(args.v704_manifest)
    v697 = load_json(args.v697_manifest)
    v525 = load_json(args.v525_root / "manifest.json")
    v622 = load_json(args.v622_manifest)

    android = android_contract(args.v525_root, v622)
    native = native_contract(v840, v704, v697)

    android_contract_positive = (
        android["service_block_found"]
        and android["service_command"] == "/system/vendor/bin/cnss-daemon -n -l"
        and android["service_body_has_system_user"]
        and android["service_body_has_expected_groups"]
        and android["service_body_has_net_admin"]
        and android["identity"]["attr_current"].startswith("u:r:vendor_wcnss_service:s0")
        and android["identity"]["cap_eff"] == "0000000000001000"
        and android["v622_counts"]["wlfw_start"] > 0
        and android["v622_counts"]["wlan0"] > 0
    )
    native_launch_contract_positive = (
        native["v840_counts"]["cnss_daemon_netlink"] > 0
        and native["v840_counts"]["cnss_daemon_cld80211"] > 0
        and native["v704_proc"]["attr_current"].startswith("u:r:vendor_wcnss_service:s0")
        and native["v704_proc"]["cap_eff"] == "0000000000001000"
        and "1010" in native["v704_proc"]["groups"]
        and "3003" in native["v704_proc"]["groups"]
        and "3005" in native["v704_proc"]["groups"]
        and native["v704_fd"]["vndbinder_present"]
        and native["v704_fd"]["socket_count"] > 0
        and native["v704_proc"]["state"].startswith("S ")
        and native["v704_proc"]["threads"] >= 4
    )
    native_prewlfw_stall = (
        native_launch_contract_positive
        and native["v840_counts"]["wlfw_start"] == 0
        and native["v840_counts"]["wlfw_service_request"] == 0
        and native["v840_counts"]["wlan_pd"] == 0
        and native["v840_counts"]["qmi_server_connected"] == 0
        and native["v840_counts"]["wlan0"] == 0
    )
    provider_binder_not_primary = (
        native["v697_provider"]["literal_count"] > 0
        and native["v840_counts"]["cnss_binder_transaction_failed"] == 0
        and native["v840_counts"]["binder_transaction_failed"] == 0
    )

    return {
        "inputs": {
            "v841": input_item(v841),
            "v840": input_item(v840),
            "v704": input_item(v704),
            "v697": input_item(v697),
            "v525": input_item(v525),
            "v622": input_item(v622),
        },
        "signals": {
            "android": android,
            "native": native,
        },
        "derived": {
            "android_contract_positive": android_contract_positive,
            "native_launch_contract_positive": native_launch_contract_positive,
            "native_prewlfw_stall": native_prewlfw_stall,
            "provider_binder_not_primary_after_v840": provider_binder_not_primary,
            "selected_next_gate": "v843-current-window-cnss-stall-snapshot",
        },
        "candidate_matrix": [
            candidate(
                "coarse cnss-daemon launch contract",
                "closed",
                "Android contract and native identity/capability/SELinux/fd evidence match the required start-only surface",
                "do not redesign launcher identity before collecting the live stall point",
            ),
            candidate(
                "provider registration / vndbinder availability",
                "deprioritize",
                "V697 targeted PeripheralManager/vndbinder and V840 has no current Binder transaction failure",
                "keep provider-first ordering, but do not make it the next root blocker",
            ),
            candidate(
                "service-notifier listener timing",
                "reject",
                "V838/V840 had prearmed listener timing and still saw no indication",
                "return only if a new lower trigger appears",
            ),
            candidate(
                "Wi-Fi HAL / scan / connect / DHCP / external ping",
                "blocked",
                "native still lacks wlfw_start, WLAN-PD UP, BDF, wiphy, and wlan0",
                "keep final bring-up blocked until lower state advances",
            ),
            candidate(
                "current-window cnss-daemon stall snapshot",
                "select-next",
                "native cnss-daemon is launched with the expected contract and remains alive/sleeping with fds, but never emits wlfw_start",
                "V843 should capture wchan/syscall/task stack/fds/socket inodes around the current provider-first retry before cleanup",
            ),
        ],
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def build_checks(analysis: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    inputs = analysis["inputs"]
    for name, expected in EXPECTED.items():
        item = inputs[name]
        add_check(
            checks,
            f"{name}-input",
            "pass" if item.get("exists") and item.get("pass") and item.get("decision") == expected else "blocked",
            "blocker",
            f"decision={item.get('decision')} pass={item.get('pass')} expected={expected}",
            f"refresh {name} evidence before using V842",
        )
    derived = analysis["derived"]
    add_check(
        checks,
        "android-contract-positive",
        "pass" if derived["android_contract_positive"] else "blocked",
        "blocker",
        str(analysis["signals"]["android"]["identity"]),
        "refresh Android CNSS identity/runtime reference",
    )
    add_check(
        checks,
        "native-launch-contract-positive",
        "pass" if derived["native_launch_contract_positive"] else "blocked",
        "blocker",
        str(analysis["signals"]["native"]["v704_proc"]),
        "refresh native CNSS retry stall snapshot before selecting V843",
    )
    add_check(
        checks,
        "native-prewlfw-stall",
        "pass" if derived["native_prewlfw_stall"] else "blocked",
        "blocker",
        str(analysis["signals"]["native"]["v840_counts"]),
        "complete V840-style provider-first retry before selecting a stall snapshot",
    )
    add_check(
        checks,
        "host-only-boundary",
        "pass",
        "blocker",
        "V842 reads local evidence only",
        "keep V842 non-mutating",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v842-cnss-prewlfw-contract-plan-ready",
            True,
            "plan-only; no device command, daemon start, Wi-Fi action, credential, route, ping, or flash executed",
            "run V842 host-only classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v842-cnss-prewlfw-contract-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh prerequisite evidence before selecting V843",
        )
    return (
        "v842-current-window-cnss-stall-snapshot-selected",
        True,
        "coarse CNSS launch contract is satisfied and current native evidence is an alive pre-WLFW stall, not a launcher identity failure",
        "V843 should capture current-window cnss-daemon wchan/syscall/task stack/fds/socket inodes around the provider-first retry before cleanup",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V842 CNSS Pre-WLFW Contract Classifier",
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
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Derived",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["derived"].items()]),
        "",
        "## Android Contract",
        "",
        markdown_table(["signal", "value"], [
            ["service_command", analysis["signals"]["android"]["service_command"]],
            ["identity", analysis["signals"]["android"]["identity"]],
            ["v622_counts", analysis["signals"]["android"]["v622_counts"]],
            ["v622_timing", analysis["signals"]["android"]["v622_timing"]],
        ]),
        "",
        "## Native Contract",
        "",
        markdown_table(["signal", "value"], [
            ["v840_counts", analysis["signals"]["native"]["v840_counts"]],
            ["v704_proc", analysis["signals"]["native"]["v704_proc"]],
            ["v704_fd", analysis["signals"]["native"]["v704_fd"]],
            ["v704_helper", analysis["signals"]["native"]["v704_helper"]],
        ]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason", "next"], [
            [row["candidate"], row["classification"], row["reason"], row["next_step"]]
            for row in analysis["candidate_matrix"]
        ]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = classify(args)
    checks = build_checks(analysis)
    decision, passed, reason, next_step = decide(args.command, checks)
    manifest: dict[str, Any] = {
        "cycle": "v842",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "qmi_payload_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
