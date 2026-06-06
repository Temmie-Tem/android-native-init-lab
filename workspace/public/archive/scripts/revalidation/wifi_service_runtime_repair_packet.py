#!/usr/bin/env python3
"""V365 service-runtime repair packet for Wi-Fi HAL bring-up.

This is a no-daemon/no-link-up packet builder.  It combines Binder, private
property, CNSS start-only, and V364 readiness evidence, then checks whether the
next bounded smoke can safely repair the missing runtime surface temporarily.
It must not start service-manager, Wi-Fi HAL, wificond, supplicant, hostapd,
cnss-daemon, or cnss_diag.
"""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v365-service-runtime-repair-packet")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
DEFAULT_APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
DEFAULT_SYSTEM_ROOT = "/mnt/system/system"
DEFAULT_VENDOR_BLOCK = "/dev/block/sda29"
DEFAULT_V292 = Path("tmp/wifi/v292-binder-open-smoke-live-20260519-141358/manifest.json")
DEFAULT_V320 = Path("tmp/wifi/v320-private-property-lookup-proof-live-v11-mounted/manifest.json")
DEFAULT_V362 = Path("tmp/wifi/v362-cnss-start-only-live-20260520/manifest.json")
DEFAULT_V364 = Path("tmp/wifi/v364-hal-service-readiness-gate-live-20260520/manifest.json")
NEXT_APPROVAL_PHRASE = "approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up"
BINDER_ORDER = ("binder", "hwbinder", "vndbinder")
BINDER_EXPECTED = {
    "binder": (10, 81),
    "hwbinder": (10, 80),
    "vndbinder": (10, 79),
}
PROPERTY_KEYS = (
    "ro.build.version.sdk",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
)

LIVE_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-helper", ["stat", DEFAULT_HELPER], 10.0),
    ("stat-real-ld-config", ["stat", DEFAULT_LD_CONFIG], 10.0),
    ("stat-real-apex-libraries", ["stat", DEFAULT_APEX_LIBRARIES], 10.0),
    ("stat-property-root", ["stat", DEFAULT_PROPERTY_ROOT], 10.0),
    ("ls-property-root", ["run", DEFAULT_TOYBOX, "ls", DEFAULT_PROPERTY_ROOT], 10.0),
    ("stat-system-root", ["stat", DEFAULT_SYSTEM_ROOT], 10.0),
    ("stat-dev-block-dir", ["stat", "/dev/block"], 10.0),
    ("stat-vendor-block", ["stat", DEFAULT_VENDOR_BLOCK], 10.0),
    ("proc-partitions", ["cat", "/proc/partitions"], 10.0),
    ("stat-system-linker64", ["stat", "/mnt/system/system/bin/linker64"], 10.0),
    ("stat-system-servicemanager", ["stat", "/mnt/system/system/bin/servicemanager"], 10.0),
    ("stat-system-hwservicemanager", ["stat", "/mnt/system/system/bin/hwservicemanager"], 10.0),
    ("stat-system-wificond", ["stat", "/mnt/system/system/bin/wificond"], 10.0),
    ("stat-dev-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-dev-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-dev-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
    ("ps", ["run", DEFAULT_TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("sys-class-rfkill", ["ls", "/sys/class/rfkill"], 10.0),
)

CNSS_PROCESS_RE = re.compile(r"\b(cnss-daemon|cnss_diag)\b", re.IGNORECASE)
MANAGER_PROCESS_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WLAN_NETDEV_RE = re.compile(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*|wiphy\S*|phy\d+)(\s|:|$)", re.IGNORECASE)


@dataclass
class CaptureSummary:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class PacketCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


@dataclass
class RepairStep:
    name: str
    order: int
    status: str
    future_only: bool
    commands: list[str]
    guardrail: str
    cleanup: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v292-manifest", type=Path, default=DEFAULT_V292)
    parser.add_argument("--v320-manifest", type=Path, default=DEFAULT_V320)
    parser.add_argument("--v362-manifest", type=Path, default=DEFAULT_V362)
    parser.add_argument("--v364-manifest", type=Path, default=DEFAULT_V364)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.+-]+", "-", value)
    return re.sub(r"-+", "-", cleaned).strip("-") or "capture"


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved), "decision": "missing", "pass": False}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def live_collect(args: argparse.Namespace, store: EvidenceStore) -> list[CaptureSummary]:
    captures: list[CaptureSummary] = []
    store.mkdir("native")
    for name, command, timeout in LIVE_COMMANDS:
        record = run_capture(args, name, command, timeout=timeout)
        text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
        rel = f"native/{safe_name(name)}.txt"
        store.write_text(rel, text)
        captures.append(CaptureSummary(
            name=name,
            command=record.command,
            ok=record.ok,
            rc=record.rc,
            status=record.status,
            duration_sec=record.duration_sec,
            file=rel,
            error=record.error,
        ))
    return captures


def capture_ok(captures: list[CaptureSummary], name: str) -> bool:
    return any(capture.name == name and capture.ok for capture in captures)


def capture_text(store: EvidenceStore, captures: list[CaptureSummary], name: str) -> str:
    for capture in captures:
        if capture.name != name:
            continue
        path = store.path(capture.file)
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def add_check(checks: list[PacketCheck],
              name: str,
              status: str,
              severity: str,
              detail: str,
              evidence: list[str] | None = None,
              next_step: str = "") -> None:
    checks.append(PacketCheck(name, status, severity, detail, evidence or [], next_step))


def source_checks(args: argparse.Namespace,
                  v292: dict[str, Any],
                  v320: dict[str, Any],
                  v362: dict[str, Any],
                  v364: dict[str, Any]) -> list[PacketCheck]:
    checks: list[PacketCheck] = []
    expected = (
        ("v292-binder-open", v292, "binder-open-only-smoke-pass", args.v292_manifest),
        ("v320-private-property-lookup", v320, "private-property-lookup-getprop-pass", args.v320_manifest),
        ("v362-cnss-start-only", v362, "start-only-pass", args.v362_manifest),
        ("v364-readiness-gate", v364, "hal-service-readiness-blocked", args.v364_manifest),
    )
    for name, manifest, decision, path in expected:
        passed = manifest.get("decision") == decision and bool(manifest.get("pass"))
        add_check(
            checks,
            name,
            "pass" if passed else "missing",
            "info" if passed else "blocker",
            f"decision={manifest.get('decision', 'missing')} pass={manifest.get('pass')}",
            [str(repo_path(path))],
            "refresh prerequisite evidence before building the repair packet",
        )
    v364_reason = str(v364.get("reason") or "")
    required_blockers = {
        "current-binder-devnodes",
        "current-service-manager-processes",
        "current-property-runtime",
        "linkerconfig-visibility",
    }
    blocker_coverage = sorted(name for name in required_blockers if name in v364_reason)
    add_check(
        checks,
        "v364-blocker-coverage",
        "mapped" if len(blocker_coverage) == len(required_blockers) else "partial",
        "info" if len(blocker_coverage) == len(required_blockers) else "warning",
        f"mapped={len(blocker_coverage)}/{len(required_blockers)}",
        blocker_coverage,
        "packet must address exactly the mapped blocker classes",
    )
    return checks


def live_checks(store: EvidenceStore, captures: list[CaptureSummary], expect_version: str) -> list[PacketCheck]:
    checks: list[PacketCheck] = []
    version_text = capture_text(store, captures, "version")
    ps_text = capture_text(store, captures, "ps")
    proc_net = capture_text(store, captures, "proc-net-dev")
    partitions = capture_text(store, captures, "proc-partitions")
    rfkill_text = capture_text(store, captures, "sys-class-rfkill")
    cnss_lines = [line.strip() for line in ps_text.splitlines() if CNSS_PROCESS_RE.search(line)]
    manager_lines = [line.strip() for line in ps_text.splitlines() if MANAGER_PROCESS_RE.search(line)]
    wlan_surface = WLAN_NETDEV_RE.search(proc_net) is not None
    wifi_rfkill = bool(re.search(r"\bwifi\b", rfkill_text, re.IGNORECASE))

    add_check(checks, "native-version", "pass" if expect_version in version_text else "warn",
              "info" if expect_version in version_text else "warning", f"expect_version={expect_version}",
              [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
              "refresh defaults after native version change")
    for check_name, capture_name, path in (
        ("helper-present", "stat-helper", DEFAULT_HELPER),
        ("real-linkerconfig-present", "stat-real-ld-config", DEFAULT_LD_CONFIG),
        ("real-apex-libraries-present", "stat-real-apex-libraries", DEFAULT_APEX_LIBRARIES),
        ("property-root-present", "stat-property-root", DEFAULT_PROPERTY_ROOT),
        ("system-root-present", "stat-system-root", DEFAULT_SYSTEM_ROOT),
        ("system-linker64-present", "stat-system-linker64", "/mnt/system/system/bin/linker64"),
        ("servicemanager-binary-present", "stat-system-servicemanager", "/mnt/system/system/bin/servicemanager"),
        ("hwservicemanager-binary-present", "stat-system-hwservicemanager", "/mnt/system/system/bin/hwservicemanager"),
    ):
        ok = capture_ok(captures, capture_name)
        add_check(checks, check_name, "pass" if ok else "missing", "info" if ok else "blocker",
                  f"path={path}", [], "required for V366 repair smoke")
    dev_block_dir_ok = capture_ok(captures, "stat-dev-block-dir")
    add_check(checks, "dev-block-dir", "pass" if dev_block_dir_ok else "candidate",
              "info", "path=/dev/block", ["mkdir /dev/block"] if not dev_block_dir_ok else [],
              "V366 may create the directory before a temporary vendor block node")
    vendor_block_ok = capture_ok(captures, "stat-vendor-block")
    sda29_match = re.search(r"^\s*(\d+)\s+(\d+)\s+\d+\s+sda29\s*$", partitions, re.MULTILINE)
    if vendor_block_ok:
        add_check(checks, "vendor-block-source", "pass", "info", f"path={DEFAULT_VENDOR_BLOCK}", [],
                  "existing vendor block node can be used by V366 helper")
    elif sda29_match:
        add_check(checks, "vendor-block-source", "candidate", "info",
                  f"path={DEFAULT_VENDOR_BLOCK} major={sda29_match.group(1)} minor={sda29_match.group(2)}",
                  [f"mknodb {DEFAULT_VENDOR_BLOCK} {sda29_match.group(1)} {sda29_match.group(2)}"],
                  "V366 can create a temporary vendor block node before helper execution and remove it after")
    else:
        add_check(checks, "vendor-block-source", "missing", "blocker", "sda29 not found in /proc/partitions", [],
                  "do not run helper without a verified vendor block source")
    property_listing = capture_text(store, captures, "ls-property-root")
    required_property_files = ("properties_serial", "property_info")
    prop_files_ok = all(item in property_listing for item in required_property_files)
    add_check(checks, "property-root-layout", "pass" if prop_files_ok else "missing",
              "info" if prop_files_ok else "blocker", f"required={','.join(required_property_files)}",
              property_listing.splitlines()[:8], "property lookup smoke needs serialized property files")
    binder_current = [name for name in BINDER_ORDER if capture_ok(captures, f"stat-dev-{name}")]
    add_check(checks, "current-binder-devnodes-clean", "clean" if not binder_current else "present",
              "info" if not binder_current else "blocker", f"present={binder_current}", binder_current,
              "V366 should start from absent devnodes and clean them up after smoke")
    add_check(checks, "current-service-manager-processes-clean", "clean" if not manager_lines else "present",
              "info" if not manager_lines else "blocker", f"manager_process_lines={len(manager_lines)}",
              manager_lines[:8], "no service manager should be running before the repair smoke")
    add_check(checks, "current-cnss-process-clean", "clean" if not cnss_lines else "present",
              "info" if not cnss_lines else "blocker", f"cnss_process_lines={len(cnss_lines)}",
              cnss_lines[:8], "no CNSS process leak before the repair smoke")
    add_check(checks, "wifi-link-surface-clean", "clean" if not wlan_surface and not wifi_rfkill else "present",
              "info" if not wlan_surface and not wifi_rfkill else "blocker",
              f"wlan_surface={wlan_surface} wifi_rfkill={wifi_rfkill}", [],
              "repair smoke must not create Wi-Fi link surface")
    return checks


def binder_commands() -> list[str]:
    return [f"mknodc /dev/{name} {major} {minor}" for name, (major, minor) in BINDER_EXPECTED.items()]


def build_repair_steps() -> list[RepairStep]:
    property_probe = (
        f"run {DEFAULT_HELPER} --system-root {DEFAULT_SYSTEM_ROOT} --vendor-block {DEFAULT_VENDOR_BLOCK} "
        f"--vendor-fstype ext4 --target-profile system-getprop --mode property-lookup "
        f"--null-device-mode dev-null --property-root {DEFAULT_PROPERTY_ROOT} "
        f"--property-key {PROPERTY_KEYS[0]} --timeout-sec 10"
    )
    return [
        RepairStep(
            "temporary-device-nodes",
            1,
            "candidate",
            True,
            [
                "mkdir /dev/block",
                "mknodb /dev/block/sda29 259 13",
                *binder_commands(),
                "stat /dev/block/sda29",
                "stat /dev/binder",
                "stat /dev/hwbinder",
                "stat /dev/vndbinder",
            ],
            "temporary /dev nodes only; no Binder ioctl beyond open-only in a later smoke",
            ["run /cache/bin/toybox rm -f /dev/binder /dev/hwbinder /dev/vndbinder /dev/block/sda29"],
        ),
        RepairStep(
            "private-property-lookup",
            2,
            "candidate",
            True,
            [property_probe],
            "private helper namespace only; no global property_service socket and no property mutation",
            [],
        ),
        RepairStep(
            "private-linkerconfig-inputs",
            3,
            "candidate",
            True,
            [
                f"stat {DEFAULT_LD_CONFIG}",
                f"stat {DEFAULT_APEX_LIBRARIES}",
                "use a90_android_execns_probe --linkerconfig-mode copy-real inside private namespace",
            ],
            "private namespace materialization only; no global /linkerconfig bind mount",
            [],
        ),
        RepairStep(
            "postflight-cleanliness",
            4,
            "candidate",
            True,
            ["stat /dev/binder", "stat /dev/hwbinder", "stat /dev/vndbinder", "cat /proc/net/dev"],
            "devnodes removed; no service-manager/CNSS/Wi-Fi link surface remains",
            [],
        ),
    ]


def check_blocks(check: PacketCheck) -> bool:
    if check.severity != "blocker":
        return False
    return check.status not in {"pass", "clean"}


def decide(command: str, checks: list[PacketCheck]) -> tuple[bool, str, str]:
    blockers = [check.name for check in checks if check_blocks(check)]
    if blockers:
        return False, "service-runtime-repair-packet-blocked", "blocked by " + ", ".join(blockers)
    if command == "plan":
        return True, "service-runtime-repair-packet-plan-ready", "plan-only packet generated"
    return True, "service-runtime-repair-packet-ready", "V366 no-daemon repair smoke packet is ready"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["order"], s["name"], s["status"], "<br>".join(s["commands"]), s["guardrail"]] for s in manifest["repair_steps"]]
    return "\n".join([
        "# V365 Service Runtime Repair Packet",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- mode: `{manifest['mode']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next approval phrase: `{manifest['next_approval_phrase']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Future Repair Steps",
        "",
        markdown_table(["order", "step", "status", "future command sketch", "guardrail"], step_rows),
        "",
        "## Guardrails",
        "",
        "- no service-manager, hwservicemanager, vndservicemanager execution",
        "- no Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or cnss_diag execution",
        "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        "- no rfkill unblock, ICNSS bind/unbind, module load/unload, or firmware mutation",
        "- no Android partition write",
        "- V366 must still require the exact approval phrase before any temporary devnode mutation",
        "",
        "## References",
        "",
        "- Android linker namespace: https://source.android.com/docs/core/architecture/partitions/linker-namespace",
        "- Android HIDL: https://source.android.com/docs/core/architecture/hidl",
        "- Android Wi-Fi HAL: https://source.android.com/docs/core/connect/wifi-hal",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v292 = load_manifest(args.v292_manifest)
    v320 = load_manifest(args.v320_manifest)
    v362 = load_manifest(args.v362_manifest)
    v364 = load_manifest(args.v364_manifest)
    captures: list[CaptureSummary] = []
    checks = source_checks(args, v292, v320, v362, v364)
    if args.command == "run":
        captures = live_collect(args, store)
        checks.extend(live_checks(store, captures, args.expect_version))
    pass_ok, decision, reason = decide(args.command, checks)
    steps = build_repair_steps()
    return {
        "generated_at": now_iso(),
        "mode": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "expect_version": args.expect_version,
        "next_approval_phrase": NEXT_APPROVAL_PHRASE,
        "inputs": {
            "v292_manifest": str(repo_path(args.v292_manifest)),
            "v320_manifest": str(repo_path(args.v320_manifest)),
            "v362_manifest": str(repo_path(args.v362_manifest)),
            "v364_manifest": str(repo_path(args.v364_manifest)),
        },
        "source_decisions": {
            "v292": v292.get("decision"),
            "v320": v320.get("decision"),
            "v362": v362.get("decision"),
            "v364": v364.get("decision"),
        },
        "captures": [asdict(capture) for capture in captures],
        "checks": [asdict(check) for check in checks],
        "repair_steps": [asdict(step) for step in steps],
        "host": collect_host_metadata(),
        "references": {
            "android_linker_namespace": "https://source.android.com/docs/core/architecture/partitions/linker-namespace",
            "android_hidl": "https://source.android.com/docs/core/architecture/hidl",
            "android_wifi_hal": "https://source.android.com/docs/core/connect/wifi-hal",
        },
        "guardrails": [
            "no service-manager execution",
            "no Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or cnss_diag execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "no rfkill unblock, ICNSS bind/unbind, module load/unload, or firmware mutation",
            "no Android partition write",
        ],
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    store.write_json("manifest.json", manifest)
    store.write_json("checks.json", {"checks": manifest["checks"]})
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"next_approval_phrase: {manifest['next_approval_phrase']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
