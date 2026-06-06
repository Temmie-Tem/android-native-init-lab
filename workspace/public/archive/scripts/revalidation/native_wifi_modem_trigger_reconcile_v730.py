#!/usr/bin/env python3
"""V730 modem trigger reconciliation classifier.

This classifier reconciles the current V729 modem-only open-pending result with
the earlier V594/V595/V596 firmware-mounted modem-readiness evidence and V622
same-boot Android mdm_helper timing. It runs only bounded read-only native
captures and does not create cdev nodes, open subsystem devices, mount filesystems,
start daemons, start Wi-Fi HAL, scan/connect, use credentials, DHCP, route, or
ping.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import capture_to_manifest, collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v730-modem-trigger-reconcile")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 30.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.244 (v725-fasttransport)"

DEFAULT_V729_MANIFEST = Path("tmp/wifi/v729-modem-only-hold/manifest.json")
DEFAULT_V592_REPORT = Path("docs/reports/NATIVE_INIT_V592_SUBSYS_HOLD_OPEN_2026-05-22.md")
DEFAULT_V594_V595_REPORT = Path("docs/reports/NATIVE_INIT_V594_V595_GLOBAL_FIRMWARE_MODEM_READINESS_2026-05-22.md")
DEFAULT_V596_REPORT = Path("docs/reports/NATIVE_INIT_V596_MODEM_HOLDER_COMPANION_2026-05-22.md")
DEFAULT_V622_MANIFEST = Path("tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/manifest.json")
DEFAULT_V623_MANIFEST = Path("tmp/wifi/v623-lower-publication-gap-classifier/manifest.json")

MSS_STATE = "/sys/devices/platform/soc/4080000.qcom,mss/subsys0/state"
MDM3_STATE = "/sys/devices/platform/soc/soc:qcom,mdm3/subsys9/state"
SUBSYS_MODEM_DEV = "/sys/class/subsys/subsys_modem/dev"
FIRMWARE_CLASS_PATH = "/sys/module/firmware_class/parameters/path"
MODEM_BLOB_PATHS = (
    "/vendor/firmware_mnt/image/modem.b00",
    "/vendor/firmware-modem/image/modem.b00",
    "/firmware/image/modem.b00",
)
FIRMWARE_MOUNT_TARGETS = (
    "/vendor/firmware_mnt",
    "/vendor/firmware-modem",
    "/firmware",
)
FORBIDDEN_ACTIONS = (
    "cdev node creation",
    "subsys_modem open",
    "esoc0 create/open",
    "subsystem state write",
    "mount/umount",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/route/external ping",
    "boot image or partition write",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v729-manifest", type=Path, default=DEFAULT_V729_MANIFEST)
    parser.add_argument("--v592-report", type=Path, default=DEFAULT_V592_REPORT)
    parser.add_argument("--v594-v595-report", type=Path, default=DEFAULT_V594_V595_REPORT)
    parser.add_argument("--v596-report", type=Path, default=DEFAULT_V596_REPORT)
    parser.add_argument("--v622-manifest", type=Path, default=DEFAULT_V622_MANIFEST)
    parser.add_argument("--v623-manifest", type=Path, default=DEFAULT_V623_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    return json.loads(text) if text else {}


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


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
    capture = run_capture(args, name, command, timeout=timeout or args.timeout)
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


def stat_exists(text: str) -> bool:
    lowered = text.lower()
    return bool(text.strip()) and "no such file" not in lowered and "errno=2" not in lowered and "[err]" not in lowered


def mount_hits(mounts_text: str) -> dict[str, bool]:
    hits = {target: False for target in FIRMWARE_MOUNT_TARGETS}
    for raw_line in mounts_text.splitlines():
        parts = raw_line.split()
        if len(parts) >= 2 and parts[1] in hits:
            hits[parts[1]] = True
    return hits


def report_has(report: str, pattern: str) -> bool:
    return re.search(pattern, report, re.I | re.M) is not None


def collect_current(args: argparse.Namespace, store: EvidenceStore) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    run_step(args, store, steps, "version", ["version"], 15.0)
    run_step(args, store, steps, "status", ["status"], 25.0)
    run_step(args, store, steps, "selftest", ["selftest"], 25.0)
    run_step(args, store, steps, "firmware-class-path", ["cat", FIRMWARE_CLASS_PATH], 10.0)
    run_step(args, store, steps, "proc-mounts", ["cat", "/proc/mounts"], 20.0)
    run_step(args, store, steps, "subsys-modem-dev", ["cat", SUBSYS_MODEM_DEV], 10.0)
    run_step(args, store, steps, "mss-state", ["cat", MSS_STATE], 10.0)
    run_step(args, store, steps, "mdm3-state", ["cat", MDM3_STATE], 10.0)
    blob_stats: dict[str, bool] = {}
    for blob_path in MODEM_BLOB_PATHS:
        name = f"stat-{blob_path}"
        run_step(args, store, steps, name, ["stat", blob_path], 10.0)
        blob_stats[blob_path] = stat_exists(step_payload(steps, name))
    current = {
        "version_ok": args.expect_version in step_payload(steps, "version"),
        "status_healthy": "fail=0" in step_payload(steps, "status"),
        "selftest_healthy": "fail=0" in step_payload(steps, "selftest"),
        "firmware_class_path": step_payload(steps, "firmware-class-path").strip(),
        "mount_hits": mount_hits(step_payload(steps, "proc-mounts")),
        "blob_stats": blob_stats,
        "subsys_modem_dev": step_payload(steps, "subsys-modem-dev").strip(),
        "mss_state": step_payload(steps, "mss-state").strip(),
        "mdm3_state": step_payload(steps, "mdm3-state").strip(),
    }
    return steps, current


def build_evidence(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v592_report = read_text(args.v592_report)
    v594_v595_report = read_text(args.v594_v595_report)
    v596_report = read_text(args.v596_report)
    v729 = load_json(args.v729_manifest)
    v622 = load_json(args.v622_manifest)
    v623 = load_json(args.v623_manifest)
    steps: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    if args.command == "run":
        steps, current = collect_current(args, store)
    prior = {
        "v592": {
            "report_exists": bool(v592_report),
            "no_firmware_open_pending": report_has(v592_report, r"firmware visibility is not ready|long firmware request wait"),
            "mss_offlining": report_has(v592_report, r"mss_state=OFFLINING"),
        },
        "v594_v595": {
            "report_exists": bool(v594_v595_report),
            "v594_mss_online": report_has(v594_v595_report, r"mss:\s+OFFLINING\s+->\s+ONLINE"),
            "v595_decision_positive": report_has(v594_v595_report, r"v595-global-firmware-modem-open-readiness-delta"),
            "firmware_mounts_key": report_has(v594_v595_report, r"native needed Android-style global firmware visibility"),
            "close_warning": report_has(v594_v595_report, r"Reference count mismatch|kernel WARNING"),
        },
        "v596": {
            "report_exists": bool(v596_report),
            "subsys_modem_only": report_has(v596_report, r"opened only `subsys_modem`; no `esoc0` open"),
            "qrtr_rx": report_has(v596_report, r"qrtr_rx=1|Modem QMI Readiness RX"),
            "qrtr_tx": report_has(v596_report, r"qrtr_tx=1|Modem QMI Readiness TX"),
            "sysmon_qmi": report_has(v596_report, r"sysmon_qmi=1|sysmon-qmi"),
            "service_notifier_missing": report_has(v596_report, r"No `service-notifier`|service-notifier.*did not appear"),
        },
        "v622": {
            "manifest_exists": bool(v622),
            "decision": v622.get("decision", ""),
            "pass": bool(v622.get("pass")),
            "reason": v622.get("reason", ""),
        },
        "v623": {
            "manifest_exists": bool(v623),
            "decision": v623.get("decision", ""),
            "pass": bool(v623.get("pass")),
            "reason": v623.get("reason", ""),
        },
        "v729": {
            "manifest_exists": bool(v729),
            "decision": v729.get("decision", ""),
            "pass": bool(v729.get("pass")),
            "reason": v729.get("reason", ""),
            "holder_open_pending": bool(((v729.get("live") or {}).get("holder_open_pending_after"))),
            "mss_state": (v729.get("live") or {}).get("after_mss_state", ""),
            "mdm3_state": (v729.get("live") or {}).get("after_mdm3_state", ""),
            "qrtr_rx": ((v729.get("live") or {}).get("dmesg_after") or {}).get("counts", {}).get("qrtr_rx", 0),
            "sysmon": ((v729.get("live") or {}).get("dmesg_after") or {}).get("counts", {}).get("sysmon", 0),
        },
    }
    store.write_text("source/v592-report-excerpt.txt", "\n".join(v592_report.splitlines()[:120]) + ("\n" if v592_report else ""))
    store.write_text("source/v594-v595-report-excerpt.txt", "\n".join(v594_v595_report.splitlines()[:150]) + ("\n" if v594_v595_report else ""))
    store.write_text("source/v596-report-excerpt.txt", "\n".join(v596_report.splitlines()[:150]) + ("\n" if v596_report else ""))
    return {
        "steps": steps,
        "current": current,
        "prior": prior,
    }


def check_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    current = manifest["current"]
    prior = manifest["prior"]
    no_current_mounts = bool(current) and not any((current.get("mount_hits") or {}).values())
    no_current_blobs = bool(current) and not any((current.get("blob_stats") or {}).values())
    return [
        {
            "name": "plan-or-readonly-only",
            "status": "pass",
            "detail": {"command": manifest["command"], "forbidden_actions": list(FORBIDDEN_ACTIONS)},
            "next_step": "continue to current-state read-only run if plan-only",
        },
        {
            "name": "current-native-baseline",
            "status": "pass" if manifest["command"] == "plan" or (current.get("version_ok") and current.get("status_healthy") and current.get("selftest_healthy")) else "blocked",
            "detail": {
                "version_ok": current.get("version_ok"),
                "status_healthy": current.get("status_healthy"),
                "selftest_healthy": current.get("selftest_healthy"),
            },
            "next_step": "restore native baseline before any live lower trigger",
        },
        {
            "name": "current-global-firmware-absent",
            "status": "pass" if manifest["command"] == "plan" or (no_current_mounts and no_current_blobs) else "blocked",
            "detail": {
                "firmware_class_path": current.get("firmware_class_path"),
                "mount_hits": current.get("mount_hits"),
                "blob_stats": current.get("blob_stats"),
            },
            "next_step": "current modem trigger proof must mount firmware partitions read-only before opening subsys_modem",
        },
        {
            "name": "v729-reproduces-no-firmware-open-pending",
            "status": "pass" if prior["v729"]["holder_open_pending"] and prior["v729"]["mss_state"] == "OFFLINING" else "blocked",
            "detail": prior["v729"],
            "next_step": "do not interpret V729 as disproving firmware-mounted modem holder evidence",
        },
        {
            "name": "v594-v595-proves-firmware-mounted-modem-readiness",
            "status": "pass" if prior["v594_v595"]["v594_mss_online"] and prior["v594_v595"]["v595_decision_positive"] else "blocked",
            "detail": prior["v594_v595"],
            "next_step": "preserve firmware mount parity for next modem holder gate",
        },
        {
            "name": "v596-proves-firmware-mounted-holder-to-sysmon",
            "status": "pass" if prior["v596"]["subsys_modem_only"] and prior["v596"]["qrtr_rx"] and prior["v596"]["qrtr_tx"] and prior["v596"]["sysmon_qmi"] else "blocked",
            "detail": prior["v596"],
            "next_step": "next live proof should start from this known-good lower window, not from no-firmware V729",
        },
        {
            "name": "mdm-helper-not-first-trigger",
            "status": "pass" if prior["v622"]["decision"] == "v622-mdm-helper-post-notifier-not-root-trigger" and prior["v622"]["pass"] else "blocked",
            "detail": prior["v622"],
            "next_step": "do not use mdm_helper as a first lower publication trigger",
        },
        {
            "name": "close-warning-contract",
            "status": "review" if prior["v594_v595"]["close_warning"] else "pass",
            "detail": {"close_warning_known": prior["v594_v595"]["close_warning"]},
            "next_step": "next live holder should avoid deliberate close and use an explicit cleanup boundary",
        },
    ]


def decide(manifest: dict[str, Any]) -> tuple[str, bool, str, str]:
    checks = manifest["checks"]
    blockers = [check["name"] for check in checks if check["status"] == "blocked"]
    if blockers:
        return (
            "v730-modem-trigger-reconcile-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "repair missing evidence or current native baseline before choosing next live gate",
        )
    return (
        "v730-global-firmware-mounted-modem-holder-required",
        True,
        "V729 matches the no-global-firmware open-pending class; V594/V595/V596 show firmware-mounted subsys_modem holder reaches QRTR/sysmon, while V622 excludes mdm_helper as first trigger",
        "plan V731 current-build firmware-mount plus modem-only holder gate; avoid esoc0, deliberate close, daemon/HAL, scan/connect, credentials, DHCP, route, and external ping",
    )


def evidence_table(manifest: dict[str, Any]) -> list[list[str]]:
    current = manifest["current"]
    prior = manifest["prior"]
    return [
        [
            "current native",
            "global firmware absent",
            json.dumps({
                "firmware_class_path": current.get("firmware_class_path"),
                "mount_hits": current.get("mount_hits"),
                "blob_stats": current.get("blob_stats"),
            }, ensure_ascii=False, sort_keys=True),
            "restore firmware mount parity before modem trigger retry",
        ],
        [
            "V729",
            "no-firmware open pending",
            json.dumps(prior["v729"], ensure_ascii=False, sort_keys=True),
            "not a contradiction of V595/V596; it lacks global firmware mounts",
        ],
        [
            "V594/V595",
            "firmware-mounted modem readiness",
            json.dumps(prior["v594_v595"], ensure_ascii=False, sort_keys=True),
            "firmware partitions are a prerequisite for subsys_modem trigger",
        ],
        [
            "V596",
            "holder reaches QRTR/sysmon",
            json.dumps(prior["v596"], ensure_ascii=False, sort_keys=True),
            "recreate this lower window on current build before broader Wi-Fi work",
        ],
        [
            "V622",
            "mdm_helper later than notifier",
            json.dumps(prior["v622"], ensure_ascii=False, sort_keys=True),
            "mdm_helper is not the first trigger",
        ],
    ]


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows_for_table = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    return "\n".join([
        "# V730 Modem Trigger Reconciliation",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- readonly_device_commands_only: `{manifest['readonly_device_commands_only']}`",
        f"- cdev_or_subsys_open_executed: `{manifest['cdev_or_subsys_open_executed']}`",
        f"- mounts_executed: `{manifest['mounts_executed']}`",
        f"- daemon_or_hal_start_executed: `{manifest['daemon_or_hal_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["source", "classification", "evidence", "next"], evidence_table(manifest)),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], check_rows_for_table),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    evidence = build_evidence(args, store)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v730",
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": evidence["steps"],
        "current": evidence["current"],
        "prior": evidence["prior"],
        "device_commands_executed": args.command == "run",
        "readonly_device_commands_only": True,
        "cdev_or_subsys_open_executed": False,
        "esoc0_open_executed": False,
        "subsystem_writes_executed": False,
        "mounts_executed": False,
        "module_load_unload_executed": False,
        "daemon_or_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
    }
    manifest["checks"] = check_rows(manifest)
    decision, pass_ok, reason, next_step = decide(manifest)
    manifest["decision"] = decision
    manifest["pass"] = pass_ok
    manifest["reason"] = reason
    manifest["next_step"] = next_step
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    store.mkdir("source")
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    latest = repo_path("tmp/wifi/latest-v730-modem-trigger-reconcile.txt")
    write_private_text(latest, str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"readonly_device_commands_only: {manifest['readonly_device_commands_only']}")
    print(f"cdev_or_subsys_open_executed: {manifest['cdev_or_subsys_open_executed']}")
    print(f"mounts_executed: {manifest['mounts_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
