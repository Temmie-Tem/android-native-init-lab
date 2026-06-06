#!/usr/bin/env python3
"""V576 read-only QRTR namespace surface classifier after V95 companion repair."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import native_wifi_qrtr_modem_readiness_delta_v571 as v571
from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v576-qrtr-namespace-surface")
DEFAULT_V519_MANIFEST = Path("tmp/wifi/v519-android-native-qrtr-modem-delta/manifest.json")
DEFAULT_V575_MANIFEST = Path("tmp/wifi/v575-companion-init-root-start-only-run/manifest.json")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"

SOURCE_REFERENCES = (
    "https://codebrowser.dev/linux/linux/net/qrtr/",
    "https://android.googlesource.com/kernel/msm/+/android-7.1.0_r0.2/drivers/soc/qcom/service-notifier.c",
    "https://cateee.net/lkddb/web-lkddb/QCOM_SYSMON.html",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v519-manifest", type=Path, default=DEFAULT_V519_MANIFEST)
    parser.add_argument("--v575-manifest", type=Path, default=DEFAULT_V575_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def v575_summary(v575: dict[str, Any]) -> dict[str, Any]:
    live = v575.get("live_result") if isinstance(v575.get("live_result"), dict) else {}
    keys = live.get("keys") if isinstance(live.get("keys"), dict) else {}
    dmesg = v575.get("dmesg_summary") if isinstance(v575.get("dmesg_summary"), dict) else {}
    return {
        "exists": bool(v575.get("exists")) and not v575.get("invalid"),
        "decision": v575.get("decision"),
        "pass": v575.get("pass"),
        "reason": v575.get("reason"),
        "helper_result": live.get("helper_result"),
        "all_observable": live.get("all_observable"),
        "all_postflight_safe": live.get("all_postflight_safe"),
        "qrtr_after_ok": bool((live.get("qrtr_after") or {}).get("ok")) if isinstance(live.get("qrtr_after"), dict) else False,
        "qrtr_before_ok": bool((live.get("qrtr_before") or {}).get("ok")) if isinstance(live.get("qrtr_before"), dict) else False,
        "child_started": keys.get("wifi_companion_start.child_started"),
        "qrtr_net_window_captured": keys.get("wifi_companion_start.net_window.qrtr_captured"),
        "qrtr_readback": keys.get("wifi_companion_start.qrtr_nameservice_readback"),
        "qmi_payload": keys.get("wifi_companion_start.qmi_payload"),
        "readiness_counts": dmesg.get("counts") if isinstance(dmesg.get("counts"), dict) else {},
    }


def build_checks(args: argparse.Namespace,
                 steps: dict[str, dict[str, Any]],
                 surface: dict[str, Any],
                 v519: dict[str, Any],
                 baseline: dict[str, Any]) -> list[v571.Check]:
    checks: list[v571.Check] = []
    version = v571.payload(steps, "version")
    status = v571.payload(steps, "status")
    selftest = v571.payload(steps, "selftest")
    android_required = {
        "qrtr_modem_readiness_rx": v571.android_marker_count(v519, "qrtr_modem_readiness_rx"),
        "qrtr_modem_readiness_tx": v571.android_marker_count(v519, "qrtr_modem_readiness_tx"),
        "sysmon_qmi_ready": v571.android_marker_count(v519, "sysmon_qmi_ready"),
        "service_notifier_ready": v571.android_marker_count(v519, "service_notifier_ready"),
        "wlan_pd_indication": v571.android_marker_count(v519, "wlan_pd_indication"),
        "qmi_server_connected": v571.android_marker_count(v519, "qmi_server_connected"),
    }
    v571.add_check(
        checks,
        "native-clean",
        "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked",
        "blocker",
        f"expect_version={args.expect_version}",
        [line for line in version.splitlines() if "A90 Linux init" in line][:2],
        "restore native baseline before readiness classifier",
    )
    v571.add_check(
        checks,
        "v519-android-reference",
        "pass" if v519.get("decision") == "v519-qrtr-companion-service-gap-classified" and all(value > 0 for value in android_required.values()) else "blocked",
        "blocker",
        " ".join(f"{key}={value}" for key, value in android_required.items()),
        [str(args.v519_manifest)],
        "refresh Android QRTR/modem sequence evidence",
    )
    v571.add_check(
        checks,
        "v575-v95-companion-baseline",
        "pass" if baseline["decision"] == "v534-companion-start-only-no-fw-marker" and baseline["pass"] is True else "blocked",
        "blocker",
        f"decision={baseline['decision']} pass={baseline['pass']} helper={baseline['helper_result']} observable={baseline['all_observable']} safe={baseline['all_postflight_safe']}",
        [str(args.v575_manifest)],
        "rerun V575 helper v95 companion proof before V576",
    )
    v571.add_check(
        checks,
        "no-active-target-processes",
        "pass" if not surface["process_hits"] else "blocked",
        "blocker",
        f"process_hits={len(surface['process_hits'])}",
        surface["process_hits"][:8],
        "cleanup residual Wi-Fi/companion process before further live action",
    )
    v571.add_check(
        checks,
        "no-wifi-link-surface",
        "pass" if not surface["wifi_hits"] else "blocked",
        "blocker",
        f"wifi_hits={len(surface['wifi_hits'])}",
        surface["wifi_hits"][:8],
        "if wlan0/wiphy exists, move to scan-only gate instead",
    )
    v571.add_check(
        checks,
        "qipcrtr-protocol",
        "pass" if surface["qipcrtr_protocol_present"] else "blocked",
        "blocker",
        f"protocol={surface['qipcrtr_protocol_present']} sockets={surface['qipcrtr_sockets']}",
        [],
        "restore QRTR kernel address-family surface before companion replay",
    )
    v571.add_check(
        checks,
        "proc-net-qrtr-surface",
        "pass" if surface["proc_net_qrtr_present"] else "warn",
        "warning",
        f"proc_net_qrtr={surface['proc_net_qrtr_present']} dev_qrtr={surface['dev_qrtr_present']} v575_before={baseline['qrtr_before_ok']} v575_after={baseline['qrtr_after_ok']}",
        [],
        "classify missing QRTR namespace procfs/debug surface before HAL retry",
    )
    v571.add_check(
        checks,
        "modem-readiness-markers",
        "pass" if surface["dmesg_counts"].get("qmi_server_connected", 0) or surface["dmesg_counts"].get("wlan_fw_ready", 0) else "warn",
        "warning",
        f"counts={surface['dmesg_counts']}",
        surface["dmesg_focus_tail"][-12:],
        "do not retry scan/connect until QMI/BDF/FW markers appear",
    )
    v571.add_check(
        checks,
        "remoteproc-rpmsg-surface",
        "pass" if surface["remoteproc_present"] or surface["msm_subsys_present"] or surface["rpmsg_present"] else "warn",
        "warning",
        f"remoteproc={surface['remoteproc_present']} msm_subsys={surface['msm_subsys_present']} rpmsg={surface['rpmsg_present']}",
        surface["remoteproc_lines"][:6] + surface["msm_subsys_lines"][:6] + surface["rpmsg_lines"][:6],
        "compare modem/subsystem state to Android if QRTR namespace remains absent",
    )
    return checks


def classify(checks: list[v571.Check],
             surface: dict[str, Any],
             baseline: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blockers:
        return "v576-qrtr-namespace-surface-blocked", False, "blocked by " + ", ".join(blockers), "resolve blockers before further live proof"
    counts = surface["dmesg_counts"]
    if counts.get("qmi_server_connected", 0) > 0 or counts.get("wlan_fw_ready", 0) > 0:
        return (
            "v576-qrtr-readiness-advanced",
            True,
            "native now contains QMI/FW readiness markers after V95 baseline",
            "rerun bounded HAL start and prepare scan-only gate if wlan surface appears",
        )
    if surface["qipcrtr_protocol_present"] and surface["qipcrtr_sockets"] == 0 and not surface["proc_net_qrtr_present"]:
        return (
            "v576-qrtr-namespace-surface-absent",
            True,
            "V95 companion baseline is clean, but native still has QIPCRTR sockets=0, no /proc/net/qrtr, and no QMI/BDF/FW markers",
            "inspect why QRTR namespace/procfs surface is absent before qcwlanstate, HAL start, or scan/connect retry",
        )
    if surface["qipcrtr_sockets"] > 0 and counts.get("qmi_server_connected", 0) == 0:
        return (
            "v576-qrtr-sockets-no-modem-marker",
            True,
            "native has QRTR sockets but still lacks modem/QMI/FW readiness markers",
            "capture QRTR socket owners and compare against Android companion process state",
        )
    return (
        "v576-qrtr-namespace-surface-review-required",
        False,
        f"unclassified surface sockets={surface['qipcrtr_sockets']} proc_net_qrtr={surface['proc_net_qrtr_present']} counts={counts} baseline={baseline['decision']}",
        "inspect V576 evidence before further live action",
    )


def empty_surface() -> dict[str, Any]:
    return {
        "qipcrtr_protocol_present": False,
        "qipcrtr_sockets": -1,
        "proc_net_qrtr_present": False,
        "dev_qrtr_present": False,
        "dev_wlan_present": False,
        "debugfs_service_notifier_present": False,
        "remoteproc_present": False,
        "msm_subsys_present": False,
        "rpmsg_present": False,
        "process_hits": [],
        "wifi_hits": [],
        "dmesg_counts": {name: 0 for name, _pattern in v571.DMESG_MARKERS},
        "dmesg_focus_tail": [],
        "remoteproc_lines": [],
        "msm_subsys_lines": [],
        "rpmsg_lines": [],
        "qcom_module_lines": [],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [[item["name"], item["status"], item["severity"], item["detail"], item["next_step"]] for item in manifest["checks"]]
    surface = manifest["current_surface"]
    marker_rows = [[name, count] for name, count in surface["dmesg_counts"].items()]
    baseline = manifest["v575_summary"]
    surface_rows = [
        ["qipcrtr_protocol_present", surface["qipcrtr_protocol_present"]],
        ["qipcrtr_sockets", surface["qipcrtr_sockets"]],
        ["proc_net_qrtr_present", surface["proc_net_qrtr_present"]],
        ["dev_qrtr_present", surface["dev_qrtr_present"]],
        ["debugfs_service_notifier_present", surface["debugfs_service_notifier_present"]],
        ["remoteproc_present", surface["remoteproc_present"]],
        ["msm_subsys_present", surface["msm_subsys_present"]],
        ["rpmsg_present", surface["rpmsg_present"]],
        ["process_hits", len(surface["process_hits"])],
        ["wifi_hits", len(surface["wifi_hits"])],
    ]
    return "\n".join([
        "# V576 QRTR Namespace Surface",
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
        "## V575 Baseline",
        "",
        f"- decision: `{baseline['decision']}`",
        f"- helper_result: `{baseline['helper_result']}`",
        f"- all_observable: `{baseline['all_observable']}`",
        f"- all_postflight_safe: `{baseline['all_postflight_safe']}`",
        f"- child_started: `{baseline['child_started']}`",
        f"- qrtr_before_ok: `{baseline['qrtr_before_ok']}`",
        f"- qrtr_after_ok: `{baseline['qrtr_after_ok']}`",
        f"- readiness_counts: `{baseline['readiness_counts']}`",
        "",
        "## Current Native Surface",
        "",
        markdown_table(["key", "value"], surface_rows),
        "",
        "## Current Dmesg Marker Counts",
        "",
        markdown_table(["marker", "count"], marker_rows),
        "",
        "## Current Dmesg Focus Tail",
        "",
        "```text",
        "\n".join(surface["dmesg_focus_tail"][-80:]) if surface["dmesg_focus_tail"] else "<empty>",
        "```",
        "",
        "## References",
        "",
        *[f"- {url}" for url in SOURCE_REFERENCES],
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v519 = v571.load_json(args.v519_manifest)
    v575 = v571.load_json(args.v575_manifest)
    baseline = v575_summary(v575)
    if args.command == "plan":
        steps: list[dict[str, Any]] = []
        surface = empty_surface()
        checks = [v571.Check("plan-only", "pass", "info", "no device command executed", [], "run V576 read-only classifier")]
        decision, pass_ok, reason, next_step = (
            "v576-qrtr-namespace-surface-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V576 read-only QRTR namespace classifier",
        )
    else:
        steps = v571.run_read_only_commands(args, store)
        mapped = v571.step_map(steps)
        surface = v571.current_surface(mapped)
        checks = build_checks(args, mapped, surface, v519, baseline)
        decision, pass_ok, reason, next_step = classify(checks, surface, baseline)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "v519_manifest": str(repo_path(args.v519_manifest)),
        "v575_manifest": str(repo_path(args.v575_manifest)),
        "v575_summary": baseline,
        "current_surface": surface,
        "source_references": SOURCE_REFERENCES,
        "device_commands_executed": args.command == "run",
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "wifi_bringup_executed": False,
        "scan_connect_executed": False,
        "external_ping_executed": False,
        "explicitly_not_executed": [
            "daemon/service start",
            "Wi-Fi HAL start",
            "QMI payload",
            "supplicant/hostapd",
            "scan/connect/link-up",
            "credential use, DHCP, route change, external ping",
            "boot image flash, reboot, Android partition write",
        ],
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
