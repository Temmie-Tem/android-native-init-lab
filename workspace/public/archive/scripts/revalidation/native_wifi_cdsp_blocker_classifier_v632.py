#!/usr/bin/env python3
"""V632 host-only CDSP blocker classifier.

This classifier consolidates V631 per-node SSCTL evidence with Android lower
surface timing and vendor init contracts. It does not contact the device, write
sysfs, flash boot images, start daemons, start Wi-Fi HAL, scan, connect, use
credentials, run DHCP, change routes, or ping externally.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v632-cdsp-blocker-classifier")
DEFAULT_V631_REPORT = Path("docs/reports/NATIVE_INIT_V631_PER_NODE_SIBLING_SSCTL_PROOF_LIVE_2026-05-23.md")
DEFAULT_V631_TIMELINE = Path("tmp/wifi/v631-armed-proof-20260523-045943/timeline.txt")
DEFAULT_V631_MARKERS = Path("tmp/wifi/v631-armed-proof-20260523-045943/markers.txt")
DEFAULT_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V629_MANIFEST = Path("tmp/wifi/v629-sibling-ssctl-trigger-classifier/manifest.json")
DEFAULT_V614_SNAPSHOT = Path(
    "tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt"
)

NODE_PATHS = {
    "adsp": "/sys/kernel/boot_adsp/boot",
    "cdsp": "/sys/kernel/boot_cdsp/boot",
    "slpi": "/sys/kernel/boot_slpi/boot",
}

FORBIDDEN_ACTIONS = [
    "device command",
    "sysfs write",
    "boot image build/flash",
    "DSP boot-node retry",
    "daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
]

EXTERNAL_REFERENCES = [
    {
        "title": "Android kernel msm CDSP loader driver",
        "url": "https://android.googlesource.com/kernel/msm/+/9f8c2d8438a7f0cd3d65a588bb60f10b67adf2a8%5E%21/",
        "relevance": "The CDSP loader loads compute DSP firmware images and brings the subsystem out of reset.",
    },
    {
        "title": "Google Coral init.insmod boot devices",
        "url": "https://android.googlesource.com/device/google/coral/+/2c5e9cd2569af264f59bec8354e1ec20636871bb/init.insmod.coral.cfg",
        "relevance": "Adjacent Qualcomm Android config enables ADSP, CDSP, and SLPI only after module setup is complete.",
    },
    {
        "title": "Google Crosshatch init hardware early-boot",
        "url": "https://android.googlesource.com/device/google/crosshatch/+/refs/tags/android-10.0.0_r17/init.hardware.rc",
        "relevance": "Adjacent Qualcomm Android init waits for module readiness before writing ADSP/CDSP boot nodes.",
    },
]

TIMELINE_RE = re.compile(
    r"^\s*(?P<index>\d+)\s+(?P<ms>\d+)ms\s+(?P<tag>\S+)\s+"
    r"rc=(?P<rc>-?\d+)\s+errno=(?P<errno>\d+)\s+(?P<message>.*)$"
)
PARENT_RE = re.compile(r"node\s+(?P<node>adsp|cdsp|slpi)\s+parent\s+rc=(?P<rc>-?\d+)\s+status=0x(?P<status>[0-9a-fA-F]+)\s+reaped=(?P<reaped>[01])")
WRITE_OK_RE = re.compile(r"node\s+(?P<node>adsp|cdsp|slpi)\s+write\s+rc=0")
WRITE_FAIL_RE = re.compile(r"node\s+(?P<node>adsp|cdsp|slpi)\s+write\s+rc=(?P<rc>-?\d+)")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v631-report", type=Path, default=DEFAULT_V631_REPORT)
    parser.add_argument("--v631-timeline", type=Path, default=DEFAULT_V631_TIMELINE)
    parser.add_argument("--v631-markers", type=Path, default=DEFAULT_V631_MARKERS)
    parser.add_argument("--v622-manifest", type=Path, default=DEFAULT_V622_MANIFEST)
    parser.add_argument("--v629-manifest", type=Path, default=DEFAULT_V629_MANIFEST)
    parser.add_argument("--v614-snapshot", type=Path, default=DEFAULT_V614_SNAPSHOT)
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


def line_context(text: str, needle: str) -> str:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if needle in line:
            return line
    return "missing"


def parse_timeline(text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = TIMELINE_RE.match(line)
        if not match:
            continue
        message = match.group("message")
        for node in NODE_PATHS:
            if message.startswith(f"{node} "):
                state = rows.setdefault(node, {})
                if "start" in message:
                    state["start_ms"] = int(match.group("ms"))
                else:
                    state["end_ms"] = int(match.group("ms"))
                    state["timeline_rc"] = int(match.group("rc"))
                    state["timeline_errno"] = int(match.group("errno"))
                    state["timeline_message"] = message
    return rows


def parse_proof_log(text: str) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {node: {"node": node, "path": path} for node, path in NODE_PATHS.items()}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = WRITE_OK_RE.search(line)
        if match:
            rows[match.group("node")]["write_rc"] = 0
            continue
        match = WRITE_FAIL_RE.search(line)
        if match:
            rows[match.group("node")]["write_rc"] = int(match.group("rc"))
            continue
        match = PARENT_RE.search(line)
        if match:
            row = rows[match.group("node")]
            row["parent_rc"] = int(match.group("rc"))
            row["status_hex"] = "0x" + match.group("status").lower()
            row["reaped"] = match.group("reaped") == "1"
    return rows


def merge_node_rows(proof_rows: dict[str, dict[str, Any]], timeline_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for node in ("adsp", "cdsp", "slpi"):
        row = dict(proof_rows.get(node, {"node": node, "path": NODE_PATHS[node]}))
        row.update(timeline_rows.get(node, {}))
        if "start_ms" in row and "end_ms" in row:
            row["duration_ms"] = row["end_ms"] - row["start_ms"]
        else:
            row["duration_ms"] = None
        if row.get("parent_rc") == 0 and row.get("write_rc") == 0:
            row["classification"] = "write-returned"
        elif row.get("parent_rc") == -110:
            row["classification"] = "write-blocked-timeout"
        else:
            row["classification"] = "unclassified"
        merged.append(row)
    return merged


def android_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary", {})
    counts = summary.get("counts", {}) or {}
    deltas = summary.get("deltas_ms", {}) or {}
    first = summary.get("first", {}) or {}
    return {
        "counts": counts,
        "deltas_ms": deltas,
        "first_ms": {
            marker: (first.get(marker) or {}).get("timestamp")
            for marker in (
                "sysmon_modem",
                "sysmon_slpi",
                "sysmon_cdsp",
                "sysmon_adsp",
                "service_notifier_180",
                "service_notifier_74",
                "wlan_pd",
                "wlan_fw_ready",
            )
        },
    }


def table_value(value: Any) -> str:
    if value is None:
        return "missing"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def node_table_rows(nodes: list[dict[str, Any]]) -> list[list[str]]:
    return [
        [
            row["node"],
            row["path"],
            table_value(row.get("write_rc")),
            table_value(row.get("parent_rc")),
            table_value(row.get("status_hex")),
            table_value(row.get("reaped")),
            table_value(row.get("duration_ms")),
            row["classification"],
        ]
        for row in nodes
    ]


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v631_markers = read_text(args.v631_markers)
    v631_timeline = read_text(args.v631_timeline)
    v622 = android_summary(load_json(args.v622_manifest))
    v629 = load_json(args.v629_manifest)
    v614_snapshot = read_text(args.v614_snapshot)

    nodes = merge_node_rows(parse_proof_log(v631_markers), parse_timeline(v631_timeline))
    node_map = {row["node"]: row for row in nodes}
    android_counts = v622["counts"]
    android_deltas = v622["deltas_ms"]
    android_first_ms = v622["first_ms"]

    vendor_contract = {
        "adsp_line": line_context(v614_snapshot, "write /sys/kernel/boot_adsp/boot 1"),
        "cdsp_line": line_context(v614_snapshot, "write /sys/kernel/boot_cdsp/boot 1"),
        "slpi_line": line_context(v614_snapshot, "write /sys/kernel/boot_slpi/boot 1"),
        "early_boot_exec_line": line_context(v614_snapshot, "exec u:r:vendor_qti_init_shell:s0 -- /vendor/bin/init.qcom.early_boot.sh"),
        "boot_wlan_line": line_context(v614_snapshot, "/sys/kernel/boot_wlan/boot_wlan"),
    }

    cdsp_timeout = node_map["cdsp"].get("parent_rc") == -110 and node_map["cdsp"].get("write_rc") is None
    adsp_ok = node_map["adsp"].get("classification") == "write-returned"
    slpi_ok = node_map["slpi"].get("classification") == "write-returned"
    android_cdsp_ready = int(android_counts.get("sysmon_cdsp", 0) or 0) > 0
    android_service74 = int(android_counts.get("service_notifier_74", 0) or 0) > 0
    vendor_cdsp_write = vendor_contract["cdsp_line"] != "missing"
    v629_classified = v629.get("decision") == "v629-boot-time-sibling-ssctl-candidate-classified"

    if args.command == "plan":
        decision = "v632-cdsp-blocker-classifier-plan-ready"
        pass_ok = True
        reason = "plan-only; run will classify existing V631/V622/V614/V629 evidence without device contact"
        next_step = "run V632 host-only classifier"
    elif cdsp_timeout and adsp_ok and slpi_ok and android_cdsp_ready and android_service74 and vendor_cdsp_write and v629_classified:
        decision = "v632-cdsp-prerequisite-gap-classified"
        pass_ok = True
        reason = (
            "V631 isolates CDSP as the only per-node boot write that blocks in the native post-ACM window; "
            "Android reaches CDSP SSCTL and service 74 from early-boot vendor init, so the next gate must "
            "classify CDSP loader/firmware/readiness prerequisites before another write."
        )
        next_step = "V633 should be a read-only native CDSP surface collector; do not repeat ADSP/SLPI or attempt Wi-Fi bring-up"
    else:
        decision = "v632-cdsp-evidence-gap"
        pass_ok = False
        reason = (
            f"cdsp_timeout={cdsp_timeout} adsp_ok={adsp_ok} slpi_ok={slpi_ok} "
            f"android_cdsp_ready={android_cdsp_ready} android_service74={android_service74} "
            f"vendor_cdsp_write={vendor_cdsp_write} v629_classified={v629_classified}"
        )
        next_step = "refresh missing host-only evidence before live action"

    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "host": collect_host_metadata(),
        "inputs": {
            "v631_report": str(repo_path(args.v631_report)),
            "v631_timeline": str(repo_path(args.v631_timeline)),
            "v631_markers": str(repo_path(args.v631_markers)),
            "v622_manifest": str(repo_path(args.v622_manifest)),
            "v629_manifest": str(repo_path(args.v629_manifest)),
            "v614_snapshot": str(repo_path(args.v614_snapshot)),
        },
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "node_rows": nodes,
        "android_v622": {
            "counts": {
                "sysmon_cdsp": android_counts.get("sysmon_cdsp", 0),
                "sysmon_adsp": android_counts.get("sysmon_adsp", 0),
                "sysmon_slpi": android_counts.get("sysmon_slpi", 0),
                "service_notifier_74": android_counts.get("service_notifier_74", 0),
                "wlan_pd": android_counts.get("wlan_pd", 0),
                "wlan_fw_ready": android_counts.get("wlan_fw_ready", 0),
            },
            "deltas_ms": {
                "sysmon_modem_to_sysmon_cdsp": android_deltas.get("sysmon_modem_to_sysmon_cdsp"),
                "sysmon_modem_to_sysmon_adsp": android_deltas.get("sysmon_modem_to_sysmon_adsp"),
                "sysmon_modem_to_sysmon_slpi": android_deltas.get("sysmon_modem_to_sysmon_slpi"),
                "service_notifier_180_to_service_notifier_74": android_deltas.get("service_notifier_180_to_service_notifier_74"),
                "service_notifier_180_to_wlan_pd": android_deltas.get("service_notifier_180_to_wlan_pd"),
            },
            "first_ms": android_first_ms,
        },
        "vendor_contract": vendor_contract,
        "v629_decision": v629.get("decision"),
        "checks": {
            "cdsp_timeout": cdsp_timeout,
            "adsp_ok": adsp_ok,
            "slpi_ok": slpi_ok,
            "android_cdsp_ready": android_cdsp_ready,
            "android_service74": android_service74,
            "vendor_cdsp_write": vendor_cdsp_write,
            "v629_classified": v629_classified,
        },
        "device_commands_executed": False,
        "sysfs_writes_executed": False,
        "boot_image_write_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "external_references": EXTERNAL_REFERENCES,
    }
    return manifest


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android_v622"]
    return "\n".join([
        "# Native Init V632 CDSP Blocker Classifier Report",
        "",
        "- date: `2026-05-23 KST`",
        "- status: `classified/host-only`; Wi-Fi external ping is **not** complete",
        "- runner: `scripts/revalidation/native_wifi_cdsp_blocker_classifier_v632.py`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Scope",
        "",
        "V632 is host-only. It reads existing V631 live proof evidence, Android V622",
        "same-boot lower timing, V629 sibling-SSCTL classification, and V614 vendor",
        "init snapshot evidence.",
        "",
        "No device command, sysfs write, boot image build/flash, daemon start,",
        "service-manager start, Wi-Fi HAL start, scan/connect/link-up, credential,",
        "DHCP, route change, or external ping was executed.",
        "",
        "## V631 Per-Node Result",
        "",
        markdown_table(
            ["node", "path", "write_rc", "parent_rc", "status", "reaped", "duration_ms", "classification"],
            node_table_rows(manifest["node_rows"]),
        ),
        "",
        "## Android V622 Lower Timing",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["sysmon_cdsp_count", table_value(android["counts"]["sysmon_cdsp"])],
                ["service_notifier_74_count", table_value(android["counts"]["service_notifier_74"])],
                ["wlan_pd_count", table_value(android["counts"]["wlan_pd"])],
                ["wlan_fw_ready_count", table_value(android["counts"]["wlan_fw_ready"])],
                ["sysmon_modem_to_sysmon_cdsp_ms", table_value(android["deltas_ms"]["sysmon_modem_to_sysmon_cdsp"])],
                ["service_notifier_180_to_service_notifier_74_ms", table_value(android["deltas_ms"]["service_notifier_180_to_service_notifier_74"])],
                ["service_notifier_180_to_wlan_pd_ms", table_value(android["deltas_ms"]["service_notifier_180_to_wlan_pd"])],
            ],
        ),
        "",
        "## Vendor Init Contract",
        "",
        markdown_table(
            ["surface", "line"],
            [[key, value] for key, value in manifest["vendor_contract"].items()],
        ),
        "",
        "## Classification",
        "",
        markdown_table(["check", "value"], [[key, table_value(value)] for key, value in manifest["checks"].items()]),
        "",
        "V631 proves the current post-ACM proof window is too late or missing a",
        "CDSP-specific prerequisite: ADSP and SLPI return, but CDSP remains inside",
        "the write path until killed at the bounded timeout. Android evidence proves",
        "CDSP SSCTL and service `74` are reachable during early boot, so the next",
        "action should not be Wi-Fi HAL, `boot_wlan`, `qcwlanstate`, or an external",
        "ping attempt.",
        "",
        "The next gate should collect CDSP loader state read-only under native v319:",
        "`/sys/kernel/boot_cdsp`, CDSP subsystem state, firmware mount/files,",
        "fastrpc/CDSP kernel threads, and relevant dmesg markers. A later write proof",
        "should target CDSP only and run only after those prerequisites are mapped.",
        "",
        "## External References",
        "",
        markdown_table(
            ["title", "url", "relevance"],
            [[item["title"], item["url"], item["relevance"]] for item in manifest["external_references"]],
        ),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
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
    print(f"sysfs_writes_executed: {manifest['sysfs_writes_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
