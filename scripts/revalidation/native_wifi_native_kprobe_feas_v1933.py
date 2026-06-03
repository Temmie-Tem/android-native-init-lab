#!/usr/bin/env python3
"""V1933 native kernel trace feasibility preflight."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore


CYCLE = "V1933"
OUT_DIR = Path("tmp/wifi/v1933-native-kprobe-feas")
REPORT_PATH = repo_path("docs/reports/NATIVE_INIT_V1933_NATIVE_KPROBE_FEAS_2026-06-04.md")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 25.0
EXPECTED_VERSION = "A90 Linux init 0.9.68 (v724)"
BUSYBOX = "/mnt/sdext/a90/bin/busybox"

CONFIG_PATTERN = (
    "CONFIG_(KPROBE_EVENTS|UPROBE_EVENTS|KPROBES|KALLSYMS|FUNCTION_TRACER|"
    "FTRACE|TRACEPOINTS)"
)
KALLSYMS_PATTERN = (
    "service_notif_register_notifier|service_notifier_new_server|"
    "root_service_service_ind_cb|qmi_add_lookup|wlfw_new_server|"
    "icnss_service_notifier_notify"
)


@dataclass
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def rel(path: Path | str) -> str:
    value = Path(path)
    try:
        return str(value.relative_to(repo_path(".")))
    except ValueError:
        return str(value)


def redact(text: str) -> str:
    text = re.sub(r"temmie[0-9A-Za-z_@.-]*", "[REDACTED]", text)
    text = re.sub(r"made by[^\n\r]*", "made by [REDACTED]", text)
    return text


def store_capture(store: EvidenceStore, capture: Any) -> CaptureRecord:
    text = redact(capture.text.replace("\r", ""))
    record = CaptureRecord(
        name=capture.name,
        command=capture.command,
        ok=bool(capture.ok),
        rc=capture.rc,
        status=capture.status,
        duration_sec=capture.duration_sec,
        file=f"native/{capture.name}.txt",
        text=text,
        error=capture.error,
    )
    store.write_text(record.file, text)
    return record


def run_step(args: argparse.Namespace, store: EvidenceStore, name: str, command: list[str]) -> CaptureRecord:
    capture = run_capture(args, name, command, timeout=args.timeout)
    return store_capture(store, capture)


def parse_config(text: str) -> dict[str, Any]:
    values: dict[str, str] = {}
    for raw_line in strip_cmdv1_text(text).splitlines():
        line = raw_line.strip()
        enabled = re.match(r"^(CONFIG_[A-Za-z0-9_]+)=(.*)$", line)
        disabled = re.match(r"^# (CONFIG_[A-Za-z0-9_]+) is not set$", line)
        if enabled:
            values[enabled.group(1)] = enabled.group(2)
        elif disabled:
            values[disabled.group(1)] = "not set"
    return {
        "values": values,
        "kprobes": values.get("CONFIG_KPROBES") == "y",
        "kprobe_events": values.get("CONFIG_KPROBE_EVENTS") == "y",
        "uprobe_events": values.get("CONFIG_UPROBE_EVENTS") == "y",
        "kallsyms": values.get("CONFIG_KALLSYMS") == "y",
        "kallsyms_all": values.get("CONFIG_KALLSYMS_ALL") == "y",
        "function_tracer": values.get("CONFIG_FUNCTION_TRACER") == "y",
    }


def parse_kallsyms(text: str) -> dict[str, Any]:
    lines = [line.strip() for line in strip_cmdv1_text(text).splitlines() if line.strip()]
    target_names: list[str] = []
    zero_address_count = 0
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            target_names.append(parts[2])
            if parts[0] == "0000000000000000":
                zero_address_count += 1
    return {
        "line_count": len(lines),
        "target_names": sorted(set(target_names)),
        "zero_address_count": zero_address_count,
        "all_zero_addresses": bool(lines) and zero_address_count == len(lines),
        "sample_lines": lines[:20],
    }


def tracefs_summary(filesystems_text: str, tracefs_ls_text: str) -> dict[str, Any]:
    filesystems = strip_cmdv1_text(filesystems_text)
    tracefs_listing = strip_cmdv1_text(tracefs_ls_text)
    return {
        "tracefs_filesystem_present": "nodev\ttracefs" in filesystems or "nodev tracefs" in filesystems,
        "tracefs_dir_exists": "/sys/kernel/tracing:" in tracefs_listing or "total " in tracefs_listing,
        "tracefs_dir_listing": tracefs_listing.splitlines()[:20],
    }


def classify(version_text: str, selftest_text: str, config: dict[str, Any], kallsyms: dict[str, Any], tracefs: dict[str, Any]) -> dict[str, Any]:
    version_ok = EXPECTED_VERSION in version_text
    selftest_ok = "fail=0" in selftest_text
    kernel_kprobe_unavailable = not config["kprobes"] and not config["kprobe_events"]
    user_uprobe_available = bool(config["uprobe_events"])
    symbols_present = all(
        name in kallsyms["target_names"]
        for name in (
            "service_notif_register_notifier",
            "service_notifier_new_server",
            "root_service_service_ind_cb",
            "qmi_add_lookup",
            "wlfw_new_server",
        )
    )
    if version_ok and selftest_ok and kernel_kprobe_unavailable and user_uprobe_available and symbols_present:
        label = "native-kprobe-unavailable-uprobe-only-fallback"
        reason = "native v724 exposes target symbol names but has CONFIG_KPROBES/KPROBE_EVENTS disabled, so service-notifier kernel callbacks cannot be kprobed; continue with userland uprobes/QRTR/dmesg fallback"
        passed = True
    elif not version_ok or not selftest_ok:
        label = "native-baseline-not-clean"
        reason = "native baseline version or selftest did not match v724 fail=0"
        passed = False
    elif not kernel_kprobe_unavailable:
        label = "native-kprobe-maybe-available-review"
        reason = "kernel config does not rule out kprobes; a bounded tracefs mount/preflight can review kprobe_events"
        passed = True
    elif not user_uprobe_available:
        label = "native-trace-userland-observer-regression"
        reason = "UPROBE_EVENTS is not enabled, contradicting prior libqmi/cnss userland observer runs"
        passed = False
    else:
        label = "native-kprobe-feas-incomplete"
        reason = "kernel config or target kallsyms evidence is incomplete"
        passed = False
    return {
        "label": label,
        "decision": f"v1933-{label}-{'pass' if passed else 'fail'}",
        "pass": passed,
        "reason": reason,
        "version_ok": version_ok,
        "selftest_ok": selftest_ok,
        "kernel_kprobe_unavailable": kernel_kprobe_unavailable,
        "user_uprobe_available": user_uprobe_available,
        "symbols_present": symbols_present,
        "tracefs_filesystem_present": tracefs["tracefs_filesystem_present"],
    }


def render_report(manifest: dict[str, Any]) -> str:
    config = manifest["config"]
    kallsyms = manifest["kallsyms"]
    tracefs = manifest["tracefs"]
    classification = manifest["classification"]
    rows = [
        ["version/selftest", classification["version_ok"], f"version_ok={classification['version_ok']} selftest_ok={classification['selftest_ok']}"],
        ["kernel kprobe", not classification["kernel_kprobe_unavailable"], f"CONFIG_KPROBES={config['values'].get('CONFIG_KPROBES')} CONFIG_KPROBE_EVENTS={config['values'].get('CONFIG_KPROBE_EVENTS')}"],
        ["user uprobe", classification["user_uprobe_available"], f"CONFIG_UPROBE_EVENTS={config['values'].get('CONFIG_UPROBE_EVENTS')}"],
        ["kallsyms targets", classification["symbols_present"], f"targets={kallsyms['target_names']} all_zero_addresses={kallsyms['all_zero_addresses']}"],
        ["tracefs fs", tracefs["tracefs_filesystem_present"], f"dir_exists={tracefs['tracefs_dir_exists']}"],
    ]
    lines = [
        "# Native Init V1933 Native Kprobe Feasibility\n\n",
        "## Summary\n\n",
        f"- Cycle: `{CYCLE}`\n",
        f"- Decision: `{classification['decision']}`\n",
        f"- Label: `{classification['label']}`\n",
        f"- Pass: `{manifest['pass']}`\n",
        f"- Reason: {classification['reason']}\n",
        f"- Evidence: `{manifest['out_dir']}`\n\n",
        "## Matrix\n\n",
        markdown_table(["area", "value", "detail"], [[str(cell) for cell in row] for row in rows]),
        "\n\n## Kallsyms Sample\n\n",
    ]
    lines.extend(f"- `{line}`\n" for line in kallsyms["sample_lines"])
    lines.extend([
        "\n## Decision\n\n",
        "- Do not implement a native kernel kprobe observer for `root_service_service_ind_cb`, `service_notifier_new_server`, or `wlfw_new_server`: current native config has `CONFIG_KPROBES` disabled.\n",
        "- Continue with the already-proven userland observer class: `libqmi_cci.so`/CNSS uprobes, QRTR service snapshots, and dmesg state lines around the A1 window.\n",
        "- Stop before Wi-Fi HAL, scan/connect, credentials, DHCP/routes, or external ping until native exposes WLFW69/WLAN-PD and `wlan0`.\n\n",
        "## Safety Scope\n\n",
        "Read-only native preflight. This script reads `/proc/filesystems`, `/proc/config.gz`, `/proc/kallsyms`, `/sys/kernel/tracing` directory metadata, version, and selftest only. It does not mount tracefs, write tracefs, flash, reboot, stage properties, write firmware/partitions, remount-write, open `/dev/subsys_esoc0`, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, external ping, force RC1/case, touch PMIC/GPIO/GDSC/regulators, rescan PCI, bind/unbind platforms, fake ONLINE, or send eSoC notify/BOOT_DONE.\n",
    ])
    return "".join(lines)


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    store.mkdir("native")
    version = run_step(args, store, "version", ["version"])
    selftest = run_step(args, store, "selftest", ["selftest"])
    filesystems = run_step(args, store, "proc-filesystems", ["cat", "/proc/filesystems"])
    tracefs_ls = run_step(args, store, "tracefs-ls", ["run", BUSYBOX, "ls", "-la", "/sys/kernel/tracing"])
    config_capture = run_step(
        args,
        store,
        "config-trace",
        [
            "run",
            BUSYBOX,
            "sh",
            "-c",
            f"{BUSYBOX} zcat /proc/config.gz 2>/dev/null | {BUSYBOX} grep -E '{CONFIG_PATTERN}'",
        ],
    )
    kallsyms_capture = run_step(
        args,
        store,
        "kallsyms-targets",
        [
            "run",
            BUSYBOX,
            "sh",
            "-c",
            f"{BUSYBOX} grep -E '({KALLSYMS_PATTERN})' /proc/kallsyms | {BUSYBOX} head -80",
        ],
    )
    config = parse_config(config_capture.text)
    kallsyms = parse_kallsyms(kallsyms_capture.text)
    tracefs = tracefs_summary(filesystems.text, tracefs_ls.text)
    classification = classify(version.text, selftest.text, config, kallsyms, tracefs)
    host_metadata = collect_host_metadata()
    host_metadata["repo"] = "."
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "cycle": CYCLE,
        "out_dir": rel(args.out_dir),
        "pass": bool(classification["pass"]),
        "decision": classification["decision"],
        "label": classification["label"],
        "reason": classification["reason"],
        "classification": classification,
        "captures": [asdict(record) for record in (version, selftest, filesystems, tracefs_ls, config_capture, kallsyms_capture)],
        "config": config,
        "kallsyms": kallsyms,
        "tracefs": tracefs,
        "host_metadata": host_metadata,
    }
    report = render_report(manifest)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", report)
    args.report_path.write_text(report, encoding="utf-8")
    print(
        f"{'PASS' if manifest['pass'] else 'FAIL'} "
        f"label={manifest['label']} "
        f"kprobes={config['kprobes']} "
        f"uprobes={config['uprobe_events']} "
        f"out_dir={manifest['out_dir']}"
    )
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
