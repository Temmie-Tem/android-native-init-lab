#!/usr/bin/env python3
"""V614 Android/native mdm3 trigger-path classifier.

This runner compares the Android V611 lower-surface boot evidence, the native
V613 mdm3/esoc observer result, and a fresh read-only vendor init snapshot. It
does not start CNSS, service-manager, Wi-Fi HAL, supplicant, hostapd, scan,
connect, DHCP, routing, credentials, or external ping.
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
from native_wifi_qmi_publication_precondition_v610 import TIMELINE_MARKERS


DEFAULT_OUT_DIR = Path("tmp/wifi/v614-mdm3-trigger-path-classifier")
DEFAULT_V611_DIR = Path("tmp/wifi/v612-android-lower-surface-handoff-20260523-011739/v611-android-lower-surface-recapture-run")
DEFAULT_V613_DIR = Path("tmp/wifi/v613-mdm3-esoc-20260523-013228/v613-live")

FORBIDDEN_ACTIONS = [
    "CNSS daemon start",
    "service-manager start",
    "Wi-Fi HAL start",
    "wificond/supplicant/hostapd start",
    "qcwlanstate/sysfs WLAN state write",
    "scan/connect/link-up",
    "credential/DHCP/routing/external ping",
    "raw esoc0 close/retry",
]

BOOT_NODE_PATHS = (
    "/sys/kernel/boot_adsp/boot",
    "/sys/kernel/boot_cdsp/boot",
    "/sys/kernel/boot_slpi/boot",
    "/sys/kernel/boot_wlan/boot_wlan",
)

ANDROID_DSP_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("android_mss_pil", re.compile(r"subsys-pil.*mss: modem: loading", re.I)),
    ("android_adsp_pil", re.compile(r"subsys-pil.*lpass: adsp: loading", re.I)),
    ("android_cdsp_pil", re.compile(r"subsys-pil.*turing: cdsp: loading", re.I)),
    ("android_slpi_pil", re.compile(r"subsys-pil.*ssc: slpi: loading", re.I)),
)

NATIVE_DSP_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("native_mss_pil", re.compile(r"subsys-pil.*mss: modem: loading", re.I)),
    ("native_adsp_pil", re.compile(r"subsys-pil.*lpass: adsp: loading", re.I)),
    ("native_cdsp_pil", re.compile(r"subsys-pil.*turing: cdsp: loading", re.I)),
    ("native_slpi_pil", re.compile(r"subsys-pil.*ssc: slpi: loading", re.I)),
    ("native_esoc_get", re.compile(r"__subsystem_get: esoc0", re.I)),
)

RC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("boot_adsp_write", re.compile(r"write\s+/sys/kernel/boot_adsp/boot\s+1", re.I)),
    ("boot_cdsp_write", re.compile(r"write\s+/sys/kernel/boot_cdsp/boot\s+1", re.I)),
    ("boot_slpi_write", re.compile(r"write\s+/sys/kernel/boot_slpi/boot\s+1", re.I)),
    ("boot_wlan_permission", re.compile(r"/sys/kernel/boot_wlan/boot_wlan", re.I)),
    ("vendor_qrtr_ns_service", re.compile(r"service\s+vendor\.qrtr-ns\s+/vendor/bin/qrtr-ns", re.I)),
    ("vendor_rmt_storage_service", re.compile(r"service\s+vendor\.rmt_storage\s+/vendor/bin/rmt_storage", re.I)),
    ("vendor_tftp_service", re.compile(r"service\s+vendor\.tftp_server\s+/vendor/bin/tftp_server", re.I)),
    ("vendor_pd_mapper_service", re.compile(r"service\s+vendor\.pd_mapper\s+/vendor/bin/pd-mapper", re.I)),
    ("cnss_diag_trigger", re.compile(r"start\s+cnss_diag|service\s+cnss_diag\s+", re.I)),
    ("cnss_daemon_service", re.compile(r"service\s+cnss-daemon\s+", re.I)),
    ("wcnss_service_trigger", re.compile(r"start\s+wcnss-service", re.I)),
    ("mdm_launcher_service", re.compile(r"service\s+vendor\.mdm_launcher\s+", re.I)),
    ("mdm_helper_service", re.compile(r"service\s+vendor\.mdm_helper\s+", re.I)),
    ("mdm_helper_baseband_gate", re.compile(r"baseband.*mdm|ro\.baseband|start\s+vendor\.mdm_helper", re.I)),
)

TS_RE = re.compile(r"\[\s*(?P<ts>[0-9]+(?:\.[0-9]+)?)\]")
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@dataclass(frozen=True)
class CaptureRecord:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", "--bridge-host", dest="host", default="127.0.0.1")
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v611-dir", type=Path, default=DEFAULT_V611_DIR)
    parser.add_argument("--v613-dir", type=Path, default=DEFAULT_V613_DIR)
    parser.add_argument("command", choices=("plan", "run"))
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {}
    return json.loads(resolved.read_text(encoding="utf-8", errors="replace"))


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def safe_line(line: str) -> str:
    clean = ANSI_RE.sub("", line.strip())
    return re.sub(r"/tmp/a90-[A-Za-z0-9_.+-]+/vendor", "<vendor>", clean)


def dmesg_time(line: str) -> float | None:
    match = TS_RE.search(line)
    if not match:
        return None
    try:
        return float(match.group("ts"))
    except ValueError:
        return None


def count_patterns(text: str, patterns: tuple[tuple[str, re.Pattern[str]], ...]) -> dict[str, Any]:
    counts = {name: 0 for name, _ in patterns}
    first: dict[str, dict[str, Any]] = {}
    for index, raw_line in enumerate(text.splitlines()):
        line = safe_line(raw_line)
        if not line:
            continue
        for name, pattern in patterns:
            if pattern.search(line):
                counts[name] += 1
                first.setdefault(name, {"index": index, "time": dmesg_time(line), "line": line})
    return {"counts": counts, "first": first}


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    path = store.write_text(f"native/{name}.txt", text.rstrip() + "\n")
    return str(path.relative_to(store.run_dir))


def capture_device(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str], timeout: float) -> CaptureRecord:
    capture = run_capture(args, name, command, timeout=timeout)
    stripped = strip_cmdv1_text(capture.text) if capture.text else capture.error
    relative = write_capture(store, name, stripped)
    data = capture_to_manifest(capture)
    visible = stripped
    if len(visible) > 12000:
        visible = visible[:12000] + "\n[truncated in manifest]\n"
    return CaptureRecord(
        name=name,
        command=" ".join(command),
        ok=bool(data["ok"]),
        rc=data.get("rc"),
        status=str(data.get("status", "missing")),
        duration_sec=float(data["duration_sec"]),
        file=relative,
        text=visible,
        error=str(data.get("error", "")),
    )


def vendor_init_script() -> str:
    return r"""set -u
BB=/cache/bin/toybox
BUSY=/cache/bin/busybox
STAMP=$($BB date +%Y%m%d-%H%M%S 2>/dev/null || echo now)
BASE=/tmp/a90-v614-$STAMP
MOUNTED=0
cleanup() {
  if [ "$MOUNTED" = "1" ]; then
    $BB umount "$BASE/vendor" 2>/dev/null || true
  fi
  $BB rm -rf "$BASE" 2>/dev/null || true
}
trap cleanup EXIT
$BB mkdir -p "$BASE/vendor" || exit 1
DEV=$($BB cat /sys/class/block/sda29/dev 2>/dev/null || true)
MAJ=${DEV%:*}
MIN=${DEV#*:}
echo A90_V614_SDA29_DEV=$DEV
case "$MAJ:$MIN" in
  [0-9]*:[0-9]*) ;;
  *) echo A90_V614_BAD_DEV=$DEV; exit 1 ;;
esac
$BUSY mknod -m 600 "$BASE/sda29" b "$MAJ" "$MIN" || exit 1
$BB mount -t ext4 -o ro,noload "$BASE/sda29" "$BASE/vendor" || exit 1
MOUNTED=1
echo A90_V614_VENDOR_INIT_GREP_BEGIN
$BB grep -R -n -i -E '/sys/kernel/boot_|boot_wlan|shutdown_wlan|mdm_helper|mdm_launcher|rfs_access|qcom-c_main-sh|wcnss-service|vold.decrypt|class_start|vendor\.qrtr-ns|rmt_storage|tftp_server|pd-mapper|cnss|service vendor\.wifi|wpa_supplicant' "$BASE/vendor/etc/init" "$BASE/vendor/bin/init.mdm.sh" "$BASE/vendor/bin/init.class_main.sh" "$BASE/vendor/bin/init.qcom.early_boot.sh" 2>/dev/null || true
echo A90_V614_VENDOR_INIT_GREP_END
echo A90_V614_RELEVANT_RC_BEGIN
for spec in \
  "$BASE/vendor/etc/init/hw/init.qcom.rc:100,150p" \
  "$BASE/vendor/etc/init/hw/init.qcom.rc:600,780p" \
  "$BASE/vendor/etc/init/hw/init.target.rc:120,145p" \
  "$BASE/vendor/etc/init/hw/init.target.rc:260,285p" \
  "$BASE/vendor/etc/init/init.vendor.sensors.rc:1,70p" \
  "$BASE/vendor/etc/init/vendor.qti.rmt_storage.rc:1,80p" \
  "$BASE/vendor/etc/init/vendor.qti.tftp.rc:1,80p" \
  "$BASE/vendor/etc/init/wifi_qcom.rc:1,80p" \
  "$BASE/vendor/bin/init.mdm.sh:1,80p"; do
  FILE=${spec%:*}
  RANGE=${spec#*:}
  echo A90_V614_FILE_RANGE_BEGIN:$spec
  $BB sed -n "$RANGE" "$FILE" 2>/dev/null || true
  echo A90_V614_FILE_RANGE_END:$spec
done
echo A90_V614_RELEVANT_RC_END
"""


def collect_vendor_init(args: argparse.Namespace, store: EvidenceStore) -> list[CaptureRecord]:
    captures = [
        capture_device(args, store, "version", ["version"], 15.0),
        capture_device(args, store, "status", ["status"], 25.0),
        capture_device(args, store, "pre-proc-mounts", ["cat", "/proc/mounts"], 20.0),
        *[
            capture_device(args, store, f"stat-{path.strip('/').replace('/', '-')}", ["run", "/cache/bin/toybox", "ls", "-l", path], 10.0)
            for path in BOOT_NODE_PATHS
        ],
        capture_device(args, store, "vendor-init-readonly-snapshot", ["run", "/cache/bin/busybox", "sh", "-c", vendor_init_script()], 60.0),
        capture_device(args, store, "post-proc-mounts", ["cat", "/proc/mounts"], 20.0),
    ]
    return captures


def capture_text(captures: list[CaptureRecord], name: str) -> str:
    return "\n".join(capture.text for capture in captures if capture.name == name)


def mount_leftover(captures: list[CaptureRecord]) -> bool:
    return "a90-v614" in capture_text(captures, "post-proc-mounts")


def boot_nodes_visible(captures: list[CaptureRecord]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    for path in BOOT_NODE_PATHS:
        name = f"stat-{path.strip('/').replace('/', '-')}"
        result[path] = any(capture.name == name and capture.ok for capture in captures)
    return result


def line_rows(summary: dict[str, Any], limit: int = 40) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, item in sorted((summary.get("first") or {}).items()):
        rows.append([name, str((summary.get("counts") or {}).get(name, 0)), str(item.get("time")), str(item.get("line"))])
    return rows[:limit]


def rc_line_rows(rc_summary: dict[str, Any], limit: int = 60) -> list[list[str]]:
    rows: list[list[str]] = []
    for name, item in sorted((rc_summary.get("first") or {}).items()):
        rows.append([name, str((rc_summary.get("counts") or {}).get(name, 0)), str(item.get("line"))])
    return rows[:limit]


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v611_dir = repo_path(args.v611_dir)
    v613_dir = repo_path(args.v613_dir)
    v611_manifest = load_json(v611_dir / "manifest.json")
    v613_manifest = load_json(v613_dir / "manifest.json")
    android_dmesg = read_text(v611_dir / "android" / "commands" / "dmesg-lower-surface-tail.txt")
    native_dmesg = read_text(v613_dir / "native" / "dmesg-delta.txt")
    captures = collect_vendor_init(args, store) if args.command == "run" else []
    rc_text = capture_text(captures, "vendor-init-readonly-snapshot")

    android_summary = v611_manifest.get("android_summary") or {}
    v613_live = v613_manifest.get("live") or {}
    android_dsp = count_patterns(android_dmesg, ANDROID_DSP_PATTERNS)
    native_dsp = count_patterns(native_dmesg, NATIVE_DSP_PATTERNS)
    rc_summary = count_patterns(rc_text, RC_PATTERNS)

    android_counts = android_summary.get("counts") or {}
    native_counts = ((v613_live.get("markers") or {}).get("counts") or {})
    rc_counts = rc_summary["counts"]
    android_has_dsp_boot = all(android_dsp["counts"].get(name, 0) > 0 for name in ("android_adsp_pil", "android_cdsp_pil", "android_slpi_pil"))
    native_missing_dsp_boot = all(native_dsp["counts"].get(name, 0) == 0 for name in ("native_adsp_pil", "native_cdsp_pil", "native_slpi_pil"))
    rc_has_dsp_triggers = all(rc_counts.get(name, 0) > 0 for name in ("boot_adsp_write", "boot_cdsp_write", "boot_slpi_write"))
    android_publication = bool(android_summary.get("has_service_notifier_pair")) and bool(android_summary.get("has_sibling_sysmon"))
    native_base_ready = (
        v613_live.get("mss_after_companion") == "ONLINE"
        and native_counts.get("qrtr_rx", 0) > 0
        and native_counts.get("qrtr_tx", 0) > 0
        and native_counts.get("sysmon_qmi", 0) > 0
    )
    native_publication_missing = (
        v613_live.get("mdm3_after_companion") == "OFFLINING"
        and native_counts.get("service_notifier", 0) == 0
        and native_counts.get("wlan_pd", 0) == 0
    )
    cleanup_ok = not mount_leftover(captures)
    rc_capture_ok = args.command == "plan" or any(capture.name == "vendor-init-readonly-snapshot" and capture.ok for capture in captures)
    boot_node_visibility = boot_nodes_visible(captures)
    required_boot_nodes_visible = args.command == "plan" or all(boot_node_visibility.get(path) for path in BOOT_NODE_PATHS[:3])

    if args.command == "plan":
        decision, pass_ok, reason, next_step = (
            "v614-mdm3-trigger-path-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V614 classifier to capture read-only vendor init trigger evidence",
        )
    elif not rc_capture_ok or not cleanup_ok or not required_boot_nodes_visible:
        decision, pass_ok, reason, next_step = (
            "v614-vendor-init-capture-review",
            False,
            f"rc_capture_ok={rc_capture_ok} cleanup_ok={cleanup_ok} required_boot_nodes_visible={required_boot_nodes_visible}",
            "inspect read-only vendor init capture and cleanup before live trigger planning",
        )
    elif android_publication and native_base_ready and native_publication_missing and android_has_dsp_boot and native_missing_dsp_boot and rc_has_dsp_triggers:
        decision, pass_ok, reason, next_step = (
            "v614-dsp-boot-trigger-gap-classified",
            True,
            "Android boots ADSP/CDSP/SLPI before service-notifier; native V613 only boots MSS and raw esoc open does not publish lower services",
            "plan V615 bounded DSP boot-node observer before any CNSS/HAL/scan/connect retry",
        )
    elif android_publication and native_base_ready and native_publication_missing:
        decision, pass_ok, reason, next_step = (
            "v614-lower-trigger-gap-unclassified",
            True,
            "Android/native publication gap remains, but vendor init did not prove the DSP boot-node trigger set",
            "refresh Android boot/init evidence before another live trigger",
        )
    else:
        decision, pass_ok, reason, next_step = (
            "v614-evidence-insufficient",
            False,
            "V611/V613 evidence does not cover the required lower publication comparison",
            "refresh V611 Android recapture and V613 native observer evidence",
        )

    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "v611_dir": str(v611_dir),
            "v613_dir": str(v613_dir),
            "v611_manifest_decision": v611_manifest.get("decision"),
            "v613_manifest_decision": v613_manifest.get("decision"),
        },
        "diagnostics": {
            "android_publication": android_publication,
            "native_base_ready": native_base_ready,
            "native_publication_missing": native_publication_missing,
            "android_has_dsp_boot": android_has_dsp_boot,
            "native_missing_dsp_boot": native_missing_dsp_boot,
            "rc_has_dsp_triggers": rc_has_dsp_triggers,
            "rc_capture_ok": rc_capture_ok,
            "cleanup_ok": cleanup_ok,
            "required_boot_nodes_visible": required_boot_nodes_visible,
        },
        "android_v611": {
            "mss_state": android_summary.get("mss_state"),
            "mdm3_state": android_summary.get("mdm3_state"),
            "has_service_notifier_pair": android_summary.get("has_service_notifier_pair"),
            "has_sibling_sysmon": android_summary.get("has_sibling_sysmon"),
            "counts": {marker: android_counts.get(marker, 0) for marker in TIMELINE_MARKERS},
            "deltas_ms": android_summary.get("deltas_ms") or {},
            "dsp_pil": android_dsp,
        },
        "native_v613": {
            "mss_after_companion": v613_live.get("mss_after_companion"),
            "mdm3_after_companion": v613_live.get("mdm3_after_companion"),
            "esoc_holder_started": v613_live.get("esoc_holder_started"),
            "esoc_get_seen": v613_live.get("esoc_get_seen") or native_dsp["counts"].get("native_esoc_get", 0) > 0,
            "counts": native_counts,
            "dsp_pil": native_dsp,
        },
        "vendor_init": {
            "rc_summary": rc_summary,
            "mount_leftover": mount_leftover(captures),
            "boot_node_visibility": boot_node_visibility,
        },
        "captures": [asdict(capture) for capture in captures],
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "device_commands_executed": args.command == "run",
        "device_mutations": args.command == "run",
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    android = manifest["android_v611"]
    native = manifest["native_v613"]
    vendor = manifest["vendor_init"]
    captures = manifest.get("captures") or []
    return "\n".join([
        "# V614 MDM3 Trigger-Path Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        "",
        "## Diagnostics",
        "",
        markdown_table(["key", "value"], [[key, str(value)] for key, value in manifest["diagnostics"].items()]),
        "",
        "## Android V611",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["mss_state", android.get("mss_state")],
                ["mdm3_state", android.get("mdm3_state")],
                ["has_service_notifier_pair", android.get("has_service_notifier_pair")],
                ["has_sibling_sysmon", android.get("has_sibling_sysmon")],
            ],
        ),
        "",
        "## Android DSP PIL Events",
        "",
        markdown_table(["event", "count", "time", "line"], line_rows(android["dsp_pil"])),
        "",
        "## Native V613",
        "",
        markdown_table(
            ["key", "value"],
            [
                ["mss_after_companion", native.get("mss_after_companion")],
                ["mdm3_after_companion", native.get("mdm3_after_companion")],
                ["esoc_holder_started", native.get("esoc_holder_started")],
                ["esoc_get_seen", native.get("esoc_get_seen")],
            ],
        ),
        "",
        "## Native DSP PIL Events",
        "",
        markdown_table(["event", "count", "time", "line"], line_rows(native["dsp_pil"])),
        "",
        "## Vendor Init Trigger Evidence",
        "",
        markdown_table(["trigger", "count", "first_line"], rc_line_rows(vendor["rc_summary"])),
        "",
        "## Native Boot Nodes",
        "",
        markdown_table(["path", "visible"], [[path, str(visible)] for path, visible in (vendor.get("boot_node_visibility") or {}).items()]),
        "",
        "## Captures",
        "",
        markdown_table(
            ["capture", "ok", "rc", "duration", "file"],
            [[item["name"], str(item["ok"]), str(item["rc"]), f"{item['duration_sec']:.3f}s", item["file"]] for item in captures] or [["none", "-", "-", "-", "-"]],
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
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
