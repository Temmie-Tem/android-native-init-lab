#!/usr/bin/env python3
"""V741 service74-gated mdm_helper start-only proof.

This runner reuses the V735 firmware-mounted modem holder window, but requires
helper v122 and its `wifi-companion-service74-gated-mdm-helper-start-only` mode.
It remains below service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP,
routes, and external ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

import native_wifi_current_cnss_only_observer_v735 as observer
from a90harness.evidence import EvidenceStore, write_private_text


_ORIG_ACTIVE_PROCESS_HITS = observer.active_process_hits
DEFAULT_OUT_DIR = Path("tmp/wifi/v741-mdm-helper-gated-live")
DEFAULT_V740_MANIFEST = Path("tmp/wifi/v740-mdm-helper-baseband-contract/manifest.json")
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v738-v490-current-run/manifest.json")
DEFAULT_HELPER_SHA256 = "032fe43041b908577bb1a2e4b3ff7a7dfea24958169723907df5d403f811e989"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v122"
MODE = "wifi-companion-service74-gated-mdm-helper-start-only"
EXPECTED_ORDER = "qrtr_ns,rmt_storage,tftp_server,pd_mapper,cnss_diag,cnss_daemon,service74_gate,mdm_helper"
PROOF_PREFIX = "/tmp/a90-v741-"
LATEST_POINTER = Path("tmp/wifi/latest-v741-mdm-helper-gated-live.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=observer.base.DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=observer.base.DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=observer.base.DEFAULT_TIMEOUT)
    parser.add_argument("--toybox", default=observer.base.DEFAULT_TOYBOX)
    parser.add_argument("--busybox", default=observer.base.DEFAULT_BUSYBOX_PATH)
    parser.add_argument("--helper", default=observer.base.DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--expect-version", default=observer.base.DEFAULT_EXPECT_VERSION)
    parser.add_argument("--hold-sec", type=int, default=observer.base.DEFAULT_HOLD_SEC)
    parser.add_argument("--companion-runtime-sec", type=int, default=observer.DEFAULT_COMPANION_RUNTIME_SEC)
    parser.add_argument("--qrtr-rx-timeout-sec", type=float, default=observer.base.DEFAULT_QRTR_RX_TIMEOUT_SEC)
    parser.add_argument("--qrtr-rx-poll-sec", type=float, default=observer.base.DEFAULT_QRTR_RX_POLL_SEC)
    parser.add_argument("--v731-manifest", type=Path, default=observer.base.DEFAULT_V731_MANIFEST)
    parser.add_argument("--v732-manifest", type=Path, default=observer.base.DEFAULT_V732_MANIFEST)
    parser.add_argument("--v734-manifest", type=Path, default=observer.DEFAULT_V734_MANIFEST)
    parser.add_argument("--v740-manifest", type=Path, default=DEFAULT_V740_MANIFEST)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--proof-id", default=None)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def configure_observer() -> None:
    observer.DEFAULT_OUT_DIR = DEFAULT_OUT_DIR
    observer.DEFAULT_V490_MANIFEST = DEFAULT_V490_MANIFEST
    observer.PROOF_PREFIX = PROOF_PREFIX
    observer.MODE = MODE
    observer.EXPECTED_ORDER = EXPECTED_ORDER
    observer.active_process_hits = active_process_hits
    observer.configure_base()


def load_json_if_exists(path: Path) -> dict[str, Any]:
    resolved = observer.base.repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data.setdefault("exists", True)
        data.setdefault("path", str(resolved))
        return data
    return {"exists": True, "path": str(resolved), "invalid": "not-object"}


def int_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return 0


def check_detail(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in manifest.get("checks", []):
        if check.get("name") == name:
            detail = check.get("detail")
            return detail if isinstance(detail, dict) else {}
    return {}


def helper_keys(base_manifest: dict[str, Any]) -> dict[str, Any]:
    helper = ((base_manifest.get("live") or {}).get("helper_result") or {})
    keys = helper.get("keys") or {}
    return keys if isinstance(keys, dict) else {}


def helper_child_started(keys: dict[str, Any], name: str) -> int:
    return int_value(keys.get(f"wifi_hal_composite_start.child.{name}.child_started"))


def helper_child_observable(keys: dict[str, Any], name: str) -> int:
    return int_value(keys.get(f"wifi_companion_start.child.{name}.observable"))


def helper_child_safe(keys: dict[str, Any], name: str) -> int:
    return int_value(keys.get(f"wifi_companion_start.child.{name}.postflight_safe"))


def active_process_hits(ps_text: str) -> list[str]:
    base_hits = _ORIG_ACTIVE_PROCESS_HITS(ps_text)
    extra_patterns = (
        "a90-v741-",
        "mdm_helper",
        "/vendor/bin/mdm_helper",
    )
    extra_hits = [
        line.strip()
        for line in ps_text.splitlines()
        if any(pattern in line for pattern in extra_patterns)
    ]
    return sorted({*base_hits, *extra_hits})


def lower_state(base_manifest: dict[str, Any]) -> dict[str, Any]:
    live = base_manifest.get("live") or {}
    return {
        "mss": [live.get("mss_before"), live.get("mss_after_holder"), live.get("mss_after_companion")],
        "mdm3": [live.get("mdm3_before"), live.get("mdm3_after_holder"), live.get("mdm3_after_companion")],
        "qrtr_services": live.get("qrtr_services_after_companion") or {},
        "qrtr_readback": live.get("qrtr_readback") or {},
    }


def marker_counts(base_manifest: dict[str, Any]) -> dict[str, int]:
    counts = (((base_manifest.get("live") or {}).get("markers") or {}).get("counts") or {})
    return {
        name: int_value(counts.get(name))
        for name in ("qrtr_rx", "qrtr_tx", "sysmon_qmi", "service_notifier", "wlan_pd", "mhi", "qca6390", "wlfw", "bdf", "wlan0", "kernel_warning")
    }


def build_checks(args: argparse.Namespace,
                 v740: dict[str, Any],
                 base_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "bounded live runner plan; no device command executed",
            "next_step": "deploy helper v122, refresh V401/V490 if needed, then run V741",
        }]
    live = base_manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    keys = helper_keys(base_manifest)
    counts = marker_counts(base_manifest)
    lower = lower_state(base_manifest)
    forbidden = check_detail(base_manifest, "forbidden-helper-actions")
    gate_open = int_value(keys.get("wifi_companion_start.service74_gate.open"))
    mdm_enabled = int_value(keys.get("wifi_companion_start.mdm_helper"))
    mdm_started = helper_child_started(keys, "mdm_helper")
    mdm_observable = helper_child_observable(keys, "mdm_helper")
    mdm_safe = helper_child_safe(keys, "mdm_helper")
    return [
        {
            "name": "v740-reference",
            "status": "pass" if v740.get("decision") == "v740-mdm-helper-post-notifier-gated-proof-selected" and v740.get("pass") is True else "blocked",
            "detail": {"decision": v740.get("decision"), "pass": v740.get("pass"), "path": v740.get("path")},
            "next_step": "rerun V740 if mdm_helper contract selection is missing",
        },
        {
            "name": "base-run-completed",
            "status": "pass" if base_manifest.get("device_commands_executed") else "blocked",
            "detail": {"decision": base_manifest.get("decision"), "pass": base_manifest.get("pass"), "reason": base_manifest.get("reason")},
            "next_step": "inspect V735-compatible base manifest if no live window ran",
        },
        {
            "name": "mode-and-helper-contract",
            "status": "pass" if helper.get("mode") == MODE and helper.get("order") == EXPECTED_ORDER and mdm_enabled == 1 else "blocked",
            "detail": {
                "mode": helper.get("mode"),
                "order": helper.get("order"),
                "mdm_helper": mdm_enabled,
                "child_started": helper.get("child_started"),
                "all_observable": helper.get("all_observable"),
                "all_postflight_safe": helper.get("all_postflight_safe"),
                "result": helper.get("result"),
            },
            "next_step": "deploy helper v122 if the mode token or mdm_helper field is absent",
        },
        {
            "name": "below-hal-connect-boundary",
            "status": "pass"
            if all(int_value(value) == 0 for value in forbidden.values())
            and not base_manifest.get("service_manager_start_executed")
            and not base_manifest.get("wifi_hal_start_executed")
            and not base_manifest.get("scan_connect_executed")
            and not base_manifest.get("external_ping_executed")
            else "blocked",
            "detail": {
                "forbidden": forbidden,
                "service_manager_start_executed": base_manifest.get("service_manager_start_executed"),
                "wifi_hal_start_executed": base_manifest.get("wifi_hal_start_executed"),
                "scan_connect_executed": base_manifest.get("scan_connect_executed"),
                "external_ping_executed": base_manifest.get("external_ping_executed"),
            },
            "next_step": "discard run if it crossed HAL/connect boundary",
        },
        {
            "name": "service74-gate",
            "status": "pass" if gate_open else "finding",
            "detail": {
                "gate_open": gate_open,
                "mdm_helper_child_started": mdm_started,
                "mdm_helper_observable": mdm_observable,
                "mdm_helper_postflight_safe": mdm_safe,
            },
            "next_step": "if gate stays closed, stabilize service publication before retrying mdm_helper",
        },
        {
            "name": "mdm-helper-lifecycle",
            "status": "pass" if mdm_started and mdm_safe else ("finding" if not mdm_started else "blocked"),
            "detail": {
                "started": mdm_started,
                "observable": mdm_observable,
                "postflight_safe": mdm_safe,
                "exit_code": keys.get("wifi_companion_start.child.mdm_helper.exit_code"),
                "signal": keys.get("wifi_companion_start.child.mdm_helper.signal"),
            },
            "next_step": "if mdm_helper starts cleanly, evaluate mdm3/WLAN-PD/MHI markers",
        },
        {
            "name": "mdm3-wlanpd-mhi-progression",
            "status": "pass" if counts.get("wlan_pd") or counts.get("mhi") or counts.get("wlfw") or counts.get("bdf") or counts.get("wlan0") else "finding",
            "detail": {"lower": lower, "markers": counts},
            "next_step": "if absent after clean mdm_helper start, mdm_helper is not sufficient for current lower blocker",
        },
        {
            "name": "kernel-warning-review",
            "status": "blocked" if counts.get("kernel_warning") else "pass",
            "detail": {"kernel_warning": counts.get("kernel_warning")},
            "next_step": "stop widening the proof if kernel warning appears",
        },
        {
            "name": "postflight-reboot-cleanup",
            "status": "pass" if (live.get("reboot_cleanup") or {}).get("status_healthy") else "blocked",
            "detail": live.get("reboot_cleanup") or {},
            "next_step": "manually verify native health if cleanup proof is missing",
        },
    ]


def decide(args: argparse.Namespace,
           checks: list[dict[str, Any]],
           base_manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v741-mdm-helper-gated-live-plan-ready",
            True,
            "plan-only; no device command executed",
            "deploy helper v122, then run V741 bounded live proof",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v741-mdm-helper-gated-live-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear blocker before retry",
        )
    keys = helper_keys(base_manifest)
    counts = marker_counts(base_manifest)
    mdm_started = helper_child_started(keys, "mdm_helper")
    gate_open = int_value(keys.get("wifi_companion_start.service74_gate.open"))
    if counts.get("wlan0") or counts.get("wlfw") or counts.get("bdf"):
        return (
            "v741-mdm-helper-wlfw-advance",
            True,
            "gated mdm_helper run produced WLFW/BDF/wlan0 evidence below HAL/connect",
            "capture interface state before any scan/connect attempt",
        )
    if counts.get("wlan_pd") or counts.get("mhi") or counts.get("qca6390"):
        return (
            "v741-mdm-helper-lower-progress",
            True,
            "gated mdm_helper run produced lower WLAN-PD/MHI/QCA progress below HAL/connect",
            "classify new lower marker before HAL/connect",
        )
    if mdm_started:
        return (
            "v741-mdm-helper-started-no-lower-progress",
            True,
            "mdm_helper started under service74 gate but mdm3/WLAN-PD/MHI/WLFW did not advance",
            "route away from mdm_helper and classify remaining lower trigger",
        )
    if not gate_open:
        return (
            "v741-service74-gate-not-open",
            True,
            "service74 gate did not open, so mdm_helper was not started",
            "stabilize native service publication before mdm_helper retry",
        )
    return (
        "v741-mdm-helper-gated-live-review",
        True,
        "run stayed inside safety boundary but lifecycle/progression needs manual review",
        "inspect helper transcript before choosing next gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    base_manifest = manifest.get("base_manifest") or {}
    live = base_manifest.get("live") or {}
    helper = live.get("helper_result") or {}
    keys = helper.get("keys") or {}
    counts = marker_counts(base_manifest)
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    state_rows = [
        ["helper", json.dumps({key: helper.get(key) for key in ("mode", "order", "child_started", "all_observable", "all_postflight_safe", "result")}, sort_keys=True)],
        ["service74_gate_open", keys.get("wifi_companion_start.service74_gate.open", "")],
        ["mdm_helper_started", helper_child_started(keys, "mdm_helper")],
        ["mdm_helper_observable", helper_child_observable(keys, "mdm_helper")],
        ["mdm_helper_safe", helper_child_safe(keys, "mdm_helper")],
        ["lower", json.dumps(lower_state(base_manifest), sort_keys=True)],
    ]
    marker_rows = [[name, str(counts.get(name, 0))] for name in counts]
    return "\n".join([
        "# V741 Gated MDM Helper Live Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- mdm_helper_start_executed: `{manifest['mdm_helper_start_executed']}`",
        f"- service_manager_start_executed: `{manifest['service_manager_start_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        observer.base.markdown_table(["name", "status", "detail", "next"], check_rows),
        "",
        "## State Summary",
        "",
        observer.base.markdown_table(["key", "value"], state_rows),
        "",
        "## Marker Counts",
        "",
        observer.base.markdown_table(["marker", "count"], marker_rows),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v740 = load_json_if_exists(args.v740_manifest)
    if args.command == "run":
        base_manifest = observer.build_manifest(args, store)
    else:
        base_manifest = {}
    checks = build_checks(args, v740, base_manifest)
    decision, pass_ok, reason, next_step = decide(args, checks, base_manifest)
    keys = helper_keys(base_manifest)
    mdm_started = helper_child_started(keys, "mdm_helper")
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v741",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": observer.base.collect_host_metadata(),
        "v740": {"decision": v740.get("decision"), "pass": v740.get("pass"), "path": v740.get("path", str(observer.base.repo_path(args.v740_manifest)))},
        "checks": checks,
        "base_manifest": base_manifest,
        "device_commands_executed": args.command == "run",
        "firmware_mounts_executed": bool(base_manifest.get("firmware_mounts_executed")),
        "subsys_modem_opened": bool(base_manifest.get("subsys_modem_opened")),
        "lower_companion_start_executed": bool(base_manifest.get("lower_companion_start_executed")),
        "cnss_diag_start_executed": bool(base_manifest.get("cnss_diag_start_executed")),
        "cnss_daemon_start_executed": bool(base_manifest.get("cnss_daemon_start_executed")),
        "mdm_helper_start_executed": bool(mdm_started),
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
        "reboot_cleanup_executed": bool(base_manifest.get("reboot_cleanup_executed")),
    }


def main() -> int:
    configure_observer()
    args = parse_args()
    store = EvidenceStore(observer.base.repo_path(args.out_dir))
    store.mkdir("native")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(observer.base.repo_path(LATEST_POINTER), str(store.run_dir.relative_to(observer.base.repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"mdm_helper_start_executed: {manifest['mdm_helper_start_executed']}")
    print(f"service_manager_start_executed: {manifest['service_manager_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
