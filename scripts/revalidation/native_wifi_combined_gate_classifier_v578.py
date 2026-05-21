#!/usr/bin/env python3
"""V578 host-only classifier for the next native Wi-Fi live gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v578-combined-gate-classifier")
DEFAULT_V519 = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/manifest.json")
DEFAULT_V513 = Path("tmp/wifi/v513-dual-hal-driver-state-on/manifest.json")
DEFAULT_V576 = Path("tmp/wifi/v576-qrtr-namespace-surface/manifest.json")
DEFAULT_V577 = Path("tmp/wifi/v577-v95-broader-iwifi-retry/manifest.json")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v519-manifest", type=Path, default=DEFAULT_V519)
    parser.add_argument("--v513-manifest", type=Path, default=DEFAULT_V513)
    parser.add_argument("--v576-manifest", type=Path, default=DEFAULT_V576)
    parser.add_argument("--v577-manifest", type=Path, default=DEFAULT_V577)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def load_manifest(path: Path) -> dict[str, Any]:
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


def key(manifest: dict[str, Any], name: str, default: str = "") -> str:
    live = manifest.get("live_result") if isinstance(manifest.get("live_result"), dict) else {}
    keys = live.get("keys") if isinstance(live.get("keys"), dict) else {}
    value = keys.get(name)
    return str(value) if value is not None else default


def count(manifest: dict[str, Any], name: str) -> int:
    summary = manifest.get("android_summary") if isinstance(manifest.get("android_summary"), dict) else {}
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    value = counts.get(name)
    return value if isinstance(value, int) else 0


def live_value(manifest: dict[str, Any], name: str, default: Any = None) -> Any:
    live = manifest.get("live_result") if isinstance(manifest.get("live_result"), dict) else {}
    return live.get(name, default)


def surface_value(manifest: dict[str, Any], name: str, default: Any = None) -> Any:
    surface = manifest.get("current_surface") if isinstance(manifest.get("current_surface"), dict) else {}
    return surface.get(name, default)


def v513_summary(v513: dict[str, Any]) -> dict[str, Any]:
    return {
        "exists": bool(v513.get("exists")) and not v513.get("invalid"),
        "decision": v513.get("decision"),
        "pass": v513.get("pass"),
        "reason": v513.get("reason"),
        "all_postflight_safe": live_value(v513, "all_postflight_safe"),
        "driver_state_on": key(v513, "wifi_hal_composite_start.wlan_driver_state_on"),
        "write_executed": key(v513, "wifi_hal_composite_start.wlan_driver_state_on.executed"),
        "write_rc": key(v513, "wifi_hal_composite_start.wlan_driver_state_on.write_rc"),
        "write_errno": key(v513, "wifi_hal_composite_start.wlan_driver_state_on.write_errno"),
        "private_dev_wlan": key(v513, "wifi_runtime_surface.during.private.dev_wlan.exists"),
        "cnss_observable": key(v513, "wifi_hal_composite_start.child.cnss_daemon.observable"),
        "wlan_count": key(v513, "wifi_surface_composite.during.wlan_count"),
        "phy_count": key(v513, "wifi_surface_composite.during.phy_count"),
    }


def v576_summary(v576: dict[str, Any]) -> dict[str, Any]:
    counts = surface_value(v576, "dmesg_counts", {}) or {}
    return {
        "exists": bool(v576.get("exists")) and not v576.get("invalid"),
        "decision": v576.get("decision"),
        "pass": v576.get("pass"),
        "qipcrtr_protocol_present": surface_value(v576, "qipcrtr_protocol_present"),
        "qipcrtr_sockets": surface_value(v576, "qipcrtr_sockets"),
        "proc_net_qrtr_present": surface_value(v576, "proc_net_qrtr_present"),
        "dev_wlan_present": surface_value(v576, "dev_wlan_present"),
        "qmi_server_connected": counts.get("qmi_server_connected", 0) if isinstance(counts, dict) else 0,
        "wlan_fw_ready": counts.get("wlan_fw_ready", 0) if isinstance(counts, dict) else 0,
        "wlan0_event": counts.get("wlan0_event", 0) if isinstance(counts, dict) else 0,
    }


def v577_summary(v577: dict[str, Any]) -> dict[str, Any]:
    counts = {}
    dmesg = v577.get("dmesg_summary") if isinstance(v577.get("dmesg_summary"), dict) else {}
    if isinstance(dmesg.get("counts"), dict):
        counts = dmesg["counts"]
    return {
        "exists": bool(v577.get("exists")) and not v577.get("invalid"),
        "decision": v577.get("decision"),
        "pass": v577.get("pass"),
        "reason": v577.get("reason"),
        "all_postflight_safe": live_value(v577, "all_postflight_safe"),
        "identity_contracts_ok": live_value(v577, "rmt_tftp_identity_contracts_ok"),
        "iwifi_status": f"{live_value(v577, 'iwifi_start_wifi_status_name', '')}/{live_value(v577, 'iwifi_start_wifi_status_code', '')}",
        "qipcrtr_sockets_window": live_value(v577, "qipcrtr_sockets_window"),
        "qcwlanstate_write": key(v577, "wifi_companion_hal_order.qcwlanstate_write"),
        "dev_wlan_after_iwifi": key(v577, "wifi_companion_hal_order.runtime_after_iwifi_start.private.dev_wlan.exists"),
        "qmi_server_connected": counts.get("qmi_server_connected", 0),
        "wlan_fw_ready": counts.get("wlan_fw_ready", 0),
        "wlan0_event": counts.get("wlan0_event", 0),
    }


def android_summary(v519: dict[str, Any]) -> dict[str, Any]:
    markers = (
        "wlan_driver_load",
        "wlan_state_initialized",
        "qrtr_modem_readiness_rx",
        "qrtr_ns_start",
        "sysmon_qmi_ready",
        "service_notifier_ready",
        "cnss_daemon_wlfw_start",
        "qmi_server_connected",
        "bdf_regdb",
        "bdf_bdwlan",
        "wlan_fw_ready",
        "wlan0_event",
    )
    return {
        "exists": bool(v519.get("exists")) and not v519.get("invalid"),
        "decision": v519.get("decision"),
        "pass": v519.get("pass"),
        "markers": {name: count(v519, name) for name in markers},
    }


def add_check(checks: list[Check],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 android: dict[str, Any],
                 old_driver: dict[str, Any],
                 qrtr: dict[str, Any],
                 broader: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no evidence inspected", [], "run V578 classifier")
        return checks
    required_android = android["markers"]
    add_check(
        checks,
        "android-reference-complete",
        "pass" if android["decision"] == "v519-qrtr-companion-service-gap-classified" and all(required_android.values()) else "blocked",
        "blocker",
        f"decision={android['decision']} markers={required_android}",
        [str(args.v519_manifest)],
        "refresh Android QRTR/CNSS baseline",
    )
    add_check(
        checks,
        "v513-driver-state-proof",
        "pass" if old_driver["decision"] == "v513-dual-hal-driver-state-on-icnss-timeout-captured" and old_driver["write_executed"] == "1" else "blocked",
        "blocker",
        f"decision={old_driver['decision']} write={old_driver['write_executed']} rc={old_driver['write_rc']} errno={old_driver['write_errno']} dev_wlan={old_driver['private_dev_wlan']}",
        [str(args.v513_manifest)],
        "rerun bounded driver-state proof if stale",
    )
    add_check(
        checks,
        "v576-qrtr-surface",
        "pass" if qrtr["decision"] == "v576-qrtr-namespace-surface-absent" and qrtr["qipcrtr_protocol_present"] is True else "blocked",
        "blocker",
        f"decision={qrtr['decision']} sockets={qrtr['qipcrtr_sockets']} proc_net_qrtr={qrtr['proc_net_qrtr_present']} dev_wlan={qrtr['dev_wlan_present']}",
        [str(args.v576_manifest)],
        "rerun V576 after V95 companion proof",
    )
    add_check(
        checks,
        "v577-v95-broader-proof",
        "pass" if broader["decision"] == "v577-v95-broader-not-sufficient" and broader["identity_contracts_ok"] is True else "blocked",
        "blocker",
        f"decision={broader['decision']} iwifi={broader['iwifi_status']} qipcrtr={broader['qipcrtr_sockets_window']} qcwlanstate={broader['qcwlanstate_write']} dev_wlan={broader['dev_wlan_after_iwifi']}",
        [str(args.v577_manifest)],
        "rerun V577 after helper v95 deploy",
    )
    add_check(
        checks,
        "missing-combined-window",
        "warn",
        "warning",
        "V513 has qcwlanstate write without V95 companion stack; V577 has V95 companion stack without qcwlanstate write",
        [str(args.v513_manifest), str(args.v577_manifest)],
        "implement a V95 combined companion + driver-state ON proof before scan/connect",
    )
    return checks


def classify(checks: list[Check],
             old_driver: dict[str, Any],
             qrtr: dict[str, Any],
             broader: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "v578-combined-gate-blocked", False, "blocked by " + ", ".join(blockers), "refresh missing prerequisite evidence"
    if (
        old_driver["write_executed"] == "1"
        and broader["qcwlanstate_write"] == "0"
        and broader["identity_contracts_ok"] is True
        and str(broader["qipcrtr_sockets_window"]) == "0"
        and qrtr["dev_wlan_present"] is False
    ):
        return (
            "v578-combined-companion-driver-state-needed",
            True,
            "existing evidence split the required Android sequence: V513 exercised qcwlanstate without the V95 companion stack, while V577 exercised the V95 companion stack without qcwlanstate/dev_wlan",
            "build V579 as a bounded V95 companion + service-manager + dual-HAL + wificond + IWifi.start + qcwlanstate ON proof; still no scan/connect",
        )
    if broader["qmi_server_connected"] or broader["wlan_fw_ready"] or broader["wlan0_event"]:
        return (
            "v578-readiness-advanced",
            True,
            "V577 already contains readiness progress",
            "move to scan-only gate after confirming wlan surface",
        )
    return (
        "v578-combined-gate-review-required",
        False,
        f"unclassified summaries: v513={old_driver} v576={qrtr} v577={broader}",
        "inspect evidence manually before live action",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in manifest["checks"]]
    android_rows = [[name, value] for name, value in manifest["android_summary"]["markers"].items()]
    v513_rows = [[key, value] for key, value in manifest["v513_summary"].items()]
    v576_rows = [[key, value] for key, value in manifest["v576_summary"].items()]
    v577_rows = [[key, value] for key, value in manifest["v577_summary"].items()]
    return "\n".join([
        "# V578 Combined Gate Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- evidence: `{manifest['out_dir']}`",
        "- device_mutations: `False`",
        "- daemon_start_executed: `False`",
        "- wifi_bringup_executed: `False`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], checks),
        "",
        "## Android Reference Markers",
        "",
        markdown_table(["marker", "count"], android_rows),
        "",
        "## V513 Driver-state Window",
        "",
        markdown_table(["key", "value"], v513_rows),
        "",
        "## V576 QRTR Surface",
        "",
        markdown_table(["key", "value"], v576_rows),
        "",
        "## V577 V95 Broader Window",
        "",
        markdown_table(["key", "value"], v577_rows),
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v519 = load_manifest(args.v519_manifest)
    v513 = load_manifest(args.v513_manifest)
    v576 = load_manifest(args.v576_manifest)
    v577 = load_manifest(args.v577_manifest)
    android = android_summary(v519)
    old_driver = v513_summary(v513)
    qrtr = v576_summary(v576)
    broader = v577_summary(v577)
    checks = build_checks(args, android, old_driver, qrtr, broader)
    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v578-combined-gate-plan-ready",
            True,
            "plan-only; no evidence decision made",
            "run V578 classifier",
        )
    else:
        decision, pass_ok, reason, next_step = classify(checks, old_driver, qrtr, broader)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "inputs": {
            "v519": str(repo_path(args.v519_manifest)),
            "v513": str(repo_path(args.v513_manifest)),
            "v576": str(repo_path(args.v576_manifest)),
            "v577": str(repo_path(args.v577_manifest)),
        },
        "checks": [asdict(check) for check in checks],
        "android_summary": android,
        "v513_summary": old_driver,
        "v576_summary": qrtr,
        "v577_summary": broader,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wlan_driver_state_write_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
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
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
