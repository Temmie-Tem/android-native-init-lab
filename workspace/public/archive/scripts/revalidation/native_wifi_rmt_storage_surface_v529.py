#!/usr/bin/env python3
"""V529 read-only rmt_storage runtime surface classifier.

V528 proved that the companion identity replay reaches Android-style root and
SELinux domains, but `rmt_storage` exits before the observe window.  This
classifier does not start daemons, does not write device state, and does not
bring Wi-Fi up.  It collects read-only evidence for the runtime surfaces that
`rmt_storage` and `tftp_server` advertise in their own binaries, then compares
that contract with both native global state and the V528 private namespace.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v529-rmt-storage-surface-classifier")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_V528_MANIFEST = Path("tmp/wifi/v528-companion-start-only/manifest.json")
TOYBOX = "/cache/bin/toybox"
BUSYBOX = "/cache/bin/busybox"

RMT_KEYWORDS = re.compile(
    r"(/dev/|/sys/|/boot/|bootdevice|by-name|modem|rmt|rmtfs|qmi|uio|wake|kmsg|property|block|fsg|fsc|ssd)",
    re.IGNORECASE,
)
TFTP_KEYWORDS = re.compile(
    r"(/vendor/rfs|/mnt/vendor/persist|/data/vendor|qrtr|qmi|AF_QIPCRTR|wlan|bdf|bdwlan|regdb|firmware|wake|socket)",
    re.IGNORECASE,
)
COMPANION_CHILDREN = ("qrtr_ns", "rmt_storage", "tftp_server", "pd_mapper", "cnss_diag", "cnss_daemon")


@dataclass(frozen=True)
class CaptureStep:
    name: str
    command: list[str]
    timeout: float


@dataclass(frozen=True)
class SurfaceFinding:
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
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v528-manifest", type=Path, default=DEFAULT_V528_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def safe_name(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)).strip("-") or "capture"


def write_capture(store: EvidenceStore, name: str, text: str) -> str:
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text.rstrip() + "\n")
    return rel


def run_step(args: argparse.Namespace,
             store: EvidenceStore,
             name: str,
             command: list[str],
             timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = strip_cmdv1_text(capture.text) if capture.text else capture.error + "\n"
    item = capture_to_manifest(capture)
    item["file"] = write_capture(store, name, text)
    item["payload"] = text
    return item


def capture_plan() -> list[CaptureStep]:
    return [
        CaptureStep("version", ["version"], 15.0),
        CaptureStep("status", ["status"], 20.0),
        CaptureStep("selftest", ["selftest"], 20.0),
        CaptureStep("ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
        CaptureStep("proc-mounts", ["run", TOYBOX, "cat", "/proc/mounts"], 10.0),
        CaptureStep("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        CaptureStep("proc-net-qrtr", ["run", TOYBOX, "cat", "/proc/net/qrtr"], 10.0),
        CaptureStep("toybox-list", ["run", TOYBOX], 20.0),
        CaptureStep("vendor-init-list", ["run", TOYBOX, "find", "/mnt/vendor_ro/etc/init", "-maxdepth", "1", "-type", "f"], 20.0),
        CaptureStep("rmt-storage-rc", ["run", TOYBOX, "cat", "/mnt/vendor_ro/etc/init/vendor.qti.rmt_storage.rc"], 10.0),
        CaptureStep("tftp-server-rc", ["run", TOYBOX, "cat", "/mnt/vendor_ro/etc/init/vendor.qti.tftp.rc"], 10.0),
        CaptureStep("rmt-storage-strings", ["run", TOYBOX, "strings", "/mnt/vendor_ro/bin/rmt_storage"], 20.0),
        CaptureStep("tftp-server-strings", ["run", TOYBOX, "strings", "/mnt/vendor_ro/bin/tftp_server"], 20.0),
        CaptureStep("pd-mapper-strings", ["run", TOYBOX, "strings", "/mnt/vendor_ro/bin/pd-mapper"], 20.0),
        CaptureStep("qrtr-ns-strings", ["run", TOYBOX, "strings", "/mnt/vendor_ro/bin/qrtr-ns"], 20.0),
        CaptureStep(
            "runtime-surface-ls",
            [
                "run", TOYBOX, "ls", "-ld",
                "/vendor",
                "/mnt/vendor_ro",
                "/mnt/vendor/efs",
                "/efs",
                "/mnt/vendor/persist",
                "/persist",
                "/dev/block",
                "/dev/block/by-name",
                "/dev/block/bootdevice",
                "/dev/block/bootdevice/by-name",
                "/sys/class/uio",
                "/dev/uio0",
                "/sys/power/wake_lock",
                "/sys/power/wake_unlock",
                "/dev/kmsg",
                "/dev/socket",
                "/dev/socket/property_service",
                "/dev/__properties__",
                "/dev/binder",
                "/dev/hwbinder",
                "/dev/vndbinder",
                "/proc/net/qrtr",
            ],
            20.0,
        ),
        CaptureStep(
            "block-uevent-map",
            [
                "run",
                BUSYBOX,
                "sh",
                "-c",
                (
                    'for f in /sys/class/block/sd[a-z][0-9]*/uevent '
                    '/sys/class/block/mmcblk*p*/uevent; do '
                    '[ -r "$f" ] || continue; '
                    'dev=${f%/uevent}; dev=${dev##*/}; '
                    'echo A90BLOCK:$dev; '
                    '/cache/bin/toybox cat "$f"; '
                    "done"
                ),
            ],
            30.0,
        ),
        CaptureStep("dev-block-find", ["run", TOYBOX, "find", "/dev/block", "-maxdepth", "4"], 20.0),
        CaptureStep("sys-uio-find", ["run", TOYBOX, "find", "/sys/class/uio", "-maxdepth", "3"], 20.0),
        CaptureStep("vendor-rfs-find", ["run", TOYBOX, "find", "/mnt/vendor_ro/rfs", "-maxdepth", "4"], 20.0),
        CaptureStep("vendor-firmware-find", ["run", TOYBOX, "find", "/mnt/vendor_ro/firmware", "-maxdepth", "3"], 20.0),
        CaptureStep("selinux-current", ["run", TOYBOX, "cat", "/proc/self/attr/current"], 10.0),
        CaptureStep("selinux-enforce", ["run", TOYBOX, "cat", "/sys/fs/selinux/enforce"], 10.0),
        CaptureStep("vendor-sepolicy-rmt", ["run", TOYBOX, "grep", "-n", "rmt_storage", "/mnt/vendor_ro/etc/selinux/vendor_sepolicy.cil"], 20.0),
        CaptureStep("vendor-sepolicy-rfs", ["run", TOYBOX, "grep", "-n", "vendor_rfs_access", "/mnt/vendor_ro/etc/selinux/vendor_sepolicy.cil"], 20.0),
    ]


def run_captures(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [run_step(args, store, step.name, step.command, step.timeout) for step in capture_plan()]


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["exists"] = True
    payload["path"] = str(resolved)
    return payload


def helper_payload_from_v528(v528: dict[str, Any]) -> str:
    live = ((v528.get("live_result") or {}).get("live") or {})
    payload = live.get("payload")
    if isinstance(payload, str) and payload:
        return payload
    file_name = live.get("file")
    out_dir = v528.get("out_dir")
    if isinstance(file_name, str) and isinstance(out_dir, str):
        path = repo_path(Path(out_dir) / file_name)
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def child_summary(keys: dict[str, str], child: str) -> dict[str, str]:
    prefix = f"wifi_companion_start.child.{child}."
    return {
        key.removeprefix(prefix): value
        for key, value in keys.items()
        if key.startswith(prefix)
    }


def interesting_lines(text: str, pattern: re.Pattern[str], limit: int = 80) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line in seen:
            continue
        if pattern.search(line):
            seen.add(line)
            lines.append(line)
            if len(lines) >= limit:
                break
    return lines


def present_in_find(text: str, path: str) -> bool:
    return any(line.strip() == path for line in text.splitlines())


def present_in_ls(text: str, path: str) -> bool:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("ls:"):
            continue
        if line.endswith(" " + path) or line == path or re.search(rf"\s{re.escape(path)}(?:\s+->\s+|$)", line):
            return True
    return False


def context_exists(keys: dict[str, str], name: str) -> bool:
    return keys.get(f"context.{name}.exists") == "1"


def parse_block_uevent_map(text: str) -> dict[str, dict[str, str]]:
    blocks: dict[str, dict[str, str]] = {}
    current = ""
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("A90BLOCK:"):
            current = line.split(":", 1)[1].strip()
            blocks.setdefault(current, {})
            continue
        if current and "=" in line:
            key, value = line.split("=", 1)
            blocks[current][key] = value
    return blocks


def partition_aliases(blocks: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    aliases: dict[str, dict[str, str]] = {}
    for devname, values in blocks.items():
        partname = values.get("PARTNAME")
        if partname:
            aliases[partname] = {"devname": devname, **values}
    return aliases


def add_finding(findings: list[SurfaceFinding],
                name: str,
                status: str,
                severity: str,
                detail: str,
                evidence: list[str] | None = None,
                next_step: str = "") -> None:
    findings.append(SurfaceFinding(name, status, severity, detail, evidence or [], next_step))


def build_findings(args: argparse.Namespace,
                   steps: list[dict[str, Any]],
                   v528: dict[str, Any],
                   helper_text: str) -> tuple[list[SurfaceFinding], dict[str, Any]]:
    findings: list[SurfaceFinding] = []
    helper_keys = parse_key_values(helper_text)
    child = {name: child_summary(helper_keys, name) for name in COMPANION_CHILDREN}

    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    surface_ls = step_payload(steps, "runtime-surface-ls")
    block_uevent = step_payload(steps, "block-uevent-map")
    dev_block = step_payload(steps, "dev-block-find")
    sys_uio = step_payload(steps, "sys-uio-find")
    vendor_rfs = step_payload(steps, "vendor-rfs-find")
    rmt_strings = step_payload(steps, "rmt-storage-strings")
    tftp_strings = step_payload(steps, "tftp-server-strings")
    sepolicy_rmt = step_payload(steps, "vendor-sepolicy-rmt")
    sepolicy_rfs = step_payload(steps, "vendor-sepolicy-rfs")
    proc_qrtr = step_payload(steps, "proc-net-qrtr")

    rmt_hits = interesting_lines(rmt_strings, RMT_KEYWORDS)
    tftp_hits = interesting_lines(tftp_strings, TFTP_KEYWORDS)
    helper_rmt = child.get("rmt_storage", {})
    dmesg_counts = (v528.get("dmesg_summary") or {}).get("counts") or {}
    block_map = parse_block_uevent_map(block_uevent)
    aliases = partition_aliases(block_map)
    required_rmt_aliases = ("modemst1", "modemst2", "fsc", "fsg")

    native_clean = (
        args.expect_version in version and
        "fail=0" in status and
        "fail=0" in selftest
    )
    add_finding(
        findings,
        "native-baseline-clean",
        "pass" if native_clean else "gap",
        "blocker",
        f"expect_version={args.expect_version}",
        [line for line in version.splitlines() if "A90 Linux init" in line][:2],
        "restore native baseline before using this classifier result",
    )

    v528_runtime_gap = (
        v528.get("exists") is True and
        v528.get("decision") == "v528-companion-start-only-runtime-gap" and
        helper_rmt.get("exit_code") == "1"
    )
    add_finding(
        findings,
        "v528-rmt-storage-exit1",
        "pass" if v528_runtime_gap else "warn",
        "info",
        f"decision={v528.get('decision')} rmt_exit={helper_rmt.get('exit_code')} observable={helper_rmt.get('observable')}",
        [str(v528.get("path")), "wifi_companion_start.child.rmt_storage.exit_code"],
        "use V528 as the current bottleneck evidence",
    )

    add_finding(
        findings,
        "selinux-not-primary-suspect",
        "pass" if dmesg_counts.get("avc_denied", 0) == 0 and "vendor_rmt_storage" in sepolicy_rmt else "warn",
        "info",
        f"v528_avc_denied={dmesg_counts.get('avc_denied', 0)} rmt_policy_lines={'vendor_rmt_storage' in sepolicy_rmt}",
        interesting_lines(sepolicy_rmt, re.compile(r"rmt_storage|modemst|uio|wake|property|qipcrtr", re.IGNORECASE), 12),
        "keep SELinux loaded, but focus V530 on missing runtime files/devices",
    )

    rmt_needs_by_name = "/dev/block/bootdevice/by-name" in rmt_strings
    native_by_name = present_in_ls(surface_ls, "/dev/block/bootdevice/by-name") or present_in_find(dev_block, "/dev/block/bootdevice/by-name")
    alias_ready = all(name in aliases for name in required_rmt_aliases)
    add_finding(
        findings,
        "rmt-block-by-name-surface",
        "gap" if rmt_needs_by_name and not native_by_name else "pass",
        "blocker",
        f"rmt_requires_bootdevice_by_name={rmt_needs_by_name} native_present={native_by_name} sysfs_alias_map_ready={alias_ready}",
        [line for line in rmt_hits if "bootdevice/by-name" in line or "by-name" in line][:10]
        + [f"{name}->{aliases.get(name, {}).get('devname', '-')}" for name in required_rmt_aliases],
        "materialize /dev/block/bootdevice/by-name partition aliases in a private namespace",
    )

    missing_aliases = [name for name in required_rmt_aliases if name not in aliases]
    add_finding(
        findings,
        "rmt-required-partition-map",
        "gap" if missing_aliases else "pass",
        "blocker",
        "missing_aliases=" + (",".join(missing_aliases) if missing_aliases else "-"),
        [
            f"{name}:dev={aliases.get(name, {}).get('devname', '-')}"
            f" major={aliases.get(name, {}).get('MAJOR', '-')}"
            f" minor={aliases.get(name, {}).get('MINOR', '-')}"
            for name in required_rmt_aliases
        ],
        "do not create by-name aliases unless sysfs exposes the exact partition map",
    )

    missing_dev_nodes = [
        aliases[name]["devname"]
        for name in required_rmt_aliases
        if name in aliases and not present_in_find(dev_block, f"/dev/block/{aliases[name]['devname']}")
    ]
    add_finding(
        findings,
        "rmt-required-dev-nodes",
        "gap" if missing_dev_nodes else "pass",
        "blocker",
        "missing_dev_nodes=" + (",".join(missing_dev_nodes) if missing_dev_nodes else "-"),
        [line for line in dev_block.splitlines() if line.startswith("/dev/block")][:20],
        "create private mknod block nodes from sysfs major:minor before symlinking by-name aliases",
    )

    helper_dev_block_ready = "context.dev_block.exists" in helper_keys and helper_keys.get("context.dev_block.exists") == "1"
    add_finding(
        findings,
        "helper-private-dev-block-surface",
        "gap" if rmt_needs_by_name and not helper_dev_block_ready else "pass",
        "blocker",
        f"helper_reports_dev_block={helper_dev_block_ready}; V528 helper context has no /dev/block materialization",
        [line for line in helper_text.splitlines() if "context.dev_" in line][:16],
        "teach helper a minimal, explicit /dev/block/bootdevice/by-name surface before retrying rmt_storage",
    )

    rmt_needs_uio = "/sys/class/uio" in rmt_strings or "/dev/uio%u" in rmt_strings
    native_uio_sys = present_in_find(sys_uio, "/sys/class/uio/uio0") or present_in_ls(surface_ls, "/sys/class/uio")
    native_uio_dev = present_in_ls(surface_ls, "/dev/uio0")
    add_finding(
        findings,
        "rmt-uio-surface",
        "gap" if rmt_needs_uio and (not native_uio_sys or not native_uio_dev) else "pass",
        "blocker",
        f"rmt_requires_uio={rmt_needs_uio} sys_class_uio={native_uio_sys} dev_uio0={native_uio_dev}",
        [line for line in rmt_hits if "uio" in line.lower()][:10] + [line for line in sys_uio.splitlines() if "/sys/class/uio" in line][:6],
        "map whether /dev/uio0 must be created from /sys/class/uio/uio0/dev for rmt_storage only",
    )

    rmt_needs_wakelock = "/sys/power/wake_lock" in rmt_strings
    native_wakelock = present_in_ls(surface_ls, "/sys/power/wake_lock") and present_in_ls(surface_ls, "/sys/power/wake_unlock")
    helper_sys_power_ready = "context.sys_power_wake_lock.exists" in helper_keys and helper_keys.get("context.sys_power_wake_lock.exists") == "1"
    add_finding(
        findings,
        "rmt-wakelock-surface",
        "gap" if rmt_needs_wakelock and (not native_wakelock or not helper_sys_power_ready) else "pass",
        "blocker",
        f"rmt_requires_wakelock={rmt_needs_wakelock} native_present={native_wakelock} helper_private_present={helper_sys_power_ready}",
        [line for line in rmt_hits if "wake" in line.lower()][:10],
        "bind or intentionally stub wakelock files in a bounded private namespace before retry",
    )

    rmt_needs_kmsg = "/dev/kmsg" in rmt_strings
    native_kmsg = present_in_ls(surface_ls, "/dev/kmsg")
    add_finding(
        findings,
        "rmt-kmsg-surface",
        "warn" if rmt_needs_kmsg and not native_kmsg else "pass",
        "info",
        f"rmt_mentions_kmsg={rmt_needs_kmsg} native_present={native_kmsg}",
        [line for line in rmt_hits if "kmsg" in line.lower()][:8],
        "treat /dev/kmsg as diagnostic unless a later rmt-only proof still exits",
    )

    tftp_needs_persist = "/mnt/vendor/persist/rfs" in tftp_strings
    native_persist = present_in_ls(surface_ls, "/mnt/vendor/persist") or present_in_ls(surface_ls, "/persist")
    vendor_rfs_present = present_in_find(vendor_rfs, "/mnt/vendor_ro/rfs")
    add_finding(
        findings,
        "tftp-persist-rfs-surface",
        "gap" if tftp_needs_persist and not native_persist else "pass",
        "blocker",
        f"tftp_requires_persist_rfs={tftp_needs_persist} native_persist_present={native_persist} vendor_ro_rfs_present={vendor_rfs_present}",
        [line for line in tftp_hits if "/mnt/vendor/persist" in line][:12] + [line for line in vendor_rfs.splitlines()[:12]],
        "classify persist/RFS source before expecting tftp_server to serve WLAN DSP firmware paths",
    )

    tftp_needs_qrtr = "AF_QIPCRTR" in tftp_strings or "qrtr" in tftp_strings.lower()
    qrtr_proc_visible = "No such file" not in proc_qrtr and bool(proc_qrtr.strip())
    add_finding(
        findings,
        "tftp-qrtr-surface",
        "warn" if tftp_needs_qrtr and not qrtr_proc_visible else "pass",
        "info",
        f"tftp_requires_qrtr={tftp_needs_qrtr} proc_net_qrtr_visible={qrtr_proc_visible}",
        [line for line in tftp_hits if "qrtr" in line.lower() or "AF_QIPCRTR" in line][:10],
        "keep qrtr-ns first in start order; use socket-level evidence rather than /proc/net/qrtr alone",
    )

    property_or_binder_needed = "property_get" in rmt_strings or "property_set" in rmt_strings
    helper_property_ready = context_exists(helper_keys, "dev_properties")
    helper_binders_ready = all(context_exists(helper_keys, name) for name in ("dev_binder", "dev_hwbinder", "dev_vndbinder"))
    add_finding(
        findings,
        "property-binder-helper-surface",
        "gap" if property_or_binder_needed and (not helper_property_ready or not helper_binders_ready) else "pass",
        "blocker",
        f"rmt_property_symbols={property_or_binder_needed} helper_properties={helper_property_ready} helper_binders={helper_binders_ready}",
        [line for line in helper_text.splitlines() if any(token in line for token in ("context.dev_properties", "context.dev_binder", "context.dev_hwbinder", "context.dev_vndbinder"))][:16],
        "reuse the private property/binder surface for companion start-only if rmt-only proof requires it",
    )

    add_finding(
        findings,
        "vendor-rfs-static-tree",
        "pass" if vendor_rfs_present else "gap",
        "blocker",
        f"vendor_ro_rfs_present={vendor_rfs_present}",
        [line for line in vendor_rfs.splitlines() if "/mnt/vendor_ro/rfs" in line][:16],
        "mount vendor read-only before tftp/rfs companion proofs",
    )

    summary = {
        "v528_decision": v528.get("decision"),
        "v528_rmt_storage": helper_rmt,
        "v528_children": child,
        "rmt_string_hits": rmt_hits,
        "tftp_string_hits": tftp_hits,
        "block_aliases": aliases,
        "dmesg_counts": dmesg_counts,
    }
    return findings, summary


def classify(args: argparse.Namespace, findings: list[SurfaceFinding]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v529-rmt-storage-surface-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V529 read-only classifier against current native boot",
        )
    blockers = [finding.name for finding in findings if finding.severity == "blocker" and finding.status == "gap"]
    if blockers:
        return (
            "v529-rmt-storage-runtime-surface-gap",
            True,
            "read-only classifier found missing rmt/tftp runtime surfaces: " + ", ".join(blockers),
            "build V530 rmt-only private namespace surface proof before retrying full companion replay",
        )
    warns = [finding.name for finding in findings if finding.status == "warn"]
    if warns:
        return (
            "v529-rmt-storage-surface-warn-only",
            True,
            "no blocker surface gap found; warnings remain: " + ", ".join(warns),
            "capture rmt_storage stderr/ptrace or narrow QMI registration failure",
        )
    return (
        "v529-rmt-storage-surface-clean",
        True,
        "read-only classifier found no missing runtime surface from known rmt/tftp contracts",
        "advance to rmt-only start proof with stronger crash/exit capture",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    finding_rows = [
        [item["name"], item["status"], item["severity"], item["detail"], item["next_step"]]
        for item in manifest["findings"]
    ]
    command_rows = [
        [step["name"], step["ok"], step["rc"], step["status"], step["file"]]
        for step in manifest["steps"]
    ]
    rmt_hits = [[line] for line in manifest.get("analysis", {}).get("rmt_string_hits", [])[:30]]
    tftp_hits = [[line] for line in manifest.get("analysis", {}).get("tftp_string_hits", [])[:30]]
    return "\n".join([
        "# V529 rmt_storage Runtime Surface Classifier",
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
        "## Findings",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], finding_rows) if finding_rows else "- none",
        "",
        "## rmt_storage Contract Hints",
        "",
        markdown_table(["line"], rmt_hits) if rmt_hits else "- none",
        "",
        "## tftp_server Contract Hints",
        "",
        markdown_table(["line"], tftp_hits) if tftp_hits else "- none",
        "",
        "## Captures",
        "",
        markdown_table(["name", "ok", "rc", "status", "file"], command_rows) if command_rows else "- none",
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v528 = load_json(args.v528_manifest)
    helper_text = helper_payload_from_v528(v528)
    steps = [] if args.command == "plan" else run_captures(args, store)
    if helper_text:
        write_capture(store, "v528-helper-transcript", helper_text)
    findings, analysis = build_findings(args, steps, v528, helper_text) if args.command != "plan" else ([], {})
    decision, pass_ok, reason, next_step = classify(args, findings)
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
        "findings": [asdict(finding) for finding in findings],
        "analysis": analysis,
        "inputs": {
            "v528_manifest": {
                "exists": v528.get("exists"),
                "path": v528.get("path"),
                "decision": v528.get("decision"),
                "pass": v528.get("pass"),
                "daemon_start_executed": v528.get("daemon_start_executed"),
                "wifi_bringup_executed": v528.get("wifi_bringup_executed"),
            },
            "v528_helper_transcript_present": bool(helper_text),
        },
        "device_commands_executed": args.command != "plan",
        "device_mutations": False,
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
    store.mkdir("native")
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
