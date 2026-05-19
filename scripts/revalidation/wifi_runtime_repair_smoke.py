#!/usr/bin/env python3
"""V366 guarded runtime repair smoke for Wi-Fi service prerequisites.

The real run is mutation-gated by an exact approval phrase.  Without it this
script only emits plan/preflight/refusal evidence.  The approved run may create
and remove temporary /dev nodes, run a private property lookup through the static
execns helper, and verify postflight cleanliness.  It must not start
service-manager, Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or
cnss_diag.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v366-runtime-repair-smoke")
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_V365 = Path("tmp/wifi/v365-service-runtime-repair-packet-live-20260520-r2/manifest.json")
APPROVAL_PHRASE = "approve v366 bounded runtime repair smoke only; no service-manager start and no Wi-Fi bring-up"
TOYBOX = "/cache/bin/toybox"
HELPER = "/cache/bin/a90_android_execns_probe"
SYSTEM_ROOT = "/mnt/system/system"
VENDOR_BLOCK = "/dev/block/sda29"
PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/dev/__properties__"
LD_CONFIG = "/cache/bin/a90_real_ld.config.txt"
APEX_LIBRARIES = "/cache/bin/a90_real_apex.libraries.config.txt"
BINDER_NODES = {
    "/dev/binder": (10, 81),
    "/dev/hwbinder": (10, 80),
    "/dev/vndbinder": (10, 79),
}
VENDOR_NODE = (VENDOR_BLOCK, 259, 13)
CLEANUP_PATHS = [*BINDER_NODES.keys(), VENDOR_BLOCK]
CNSS_PROCESS_RE = re.compile(r"\b(cnss-daemon|cnss_diag)\b", re.IGNORECASE)
MANAGER_PROCESS_RE = re.compile(r"\b(servicemanager|hwservicemanager|vndservicemanager)\b")
WLAN_NETDEV_RE = re.compile(r"(^|\s)(wlan\S*|swlan\S*|p2p\S*|wifi-aware\S*|wiphy\S*|phy\d+)(\s|:|$)", re.IGNORECASE)

PREFLIGHT_COMMANDS: tuple[tuple[str, list[str], float], ...] = (
    ("version", ["version"], 10.0),
    ("status", ["status"], 10.0),
    ("mountsystem-ro", ["mountsystem", "ro"], 20.0),
    ("stat-helper", ["stat", HELPER], 10.0),
    ("stat-ld-config", ["stat", LD_CONFIG], 10.0),
    ("stat-apex-libraries", ["stat", APEX_LIBRARIES], 10.0),
    ("stat-property-root", ["stat", PROPERTY_ROOT], 10.0),
    ("stat-system-root", ["stat", SYSTEM_ROOT], 10.0),
    ("stat-dev-block-dir", ["stat", "/dev/block"], 10.0),
    ("stat-vendor-block", ["stat", VENDOR_BLOCK], 10.0),
    ("proc-partitions", ["cat", "/proc/partitions"], 10.0),
    ("stat-dev-binder", ["stat", "/dev/binder"], 10.0),
    ("stat-dev-hwbinder", ["stat", "/dev/hwbinder"], 10.0),
    ("stat-dev-vndbinder", ["stat", "/dev/vndbinder"], 10.0),
    ("ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
    ("proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
    ("sys-class-rfkill", ["ls", "/sys/class/rfkill"], 10.0),
)


@dataclass
class StepResult:
    name: str
    command: str
    ok: bool
    rc: int | None
    status: str
    duration_sec: float
    file: str
    error: str


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--v365-manifest", type=Path, default=DEFAULT_V365)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    subparsers.add_parser("cleanup")
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


def capture_command(args: argparse.Namespace,
                    store: EvidenceStore,
                    name: str,
                    command: list[str],
                    timeout: float | None = None) -> StepResult:
    record = run_capture(args, name, command, timeout=timeout if timeout is not None else args.timeout)
    text = strip_cmdv1_text(record.text) if record.text else record.error + "\n"
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, text)
    return StepResult(name, record.command, record.ok, record.rc, record.status, record.duration_sec, rel, record.error)


def capture_text(store: EvidenceStore, steps: list[StepResult], name: str) -> str:
    for step in steps:
        if step.name != name:
            continue
        path = store.path(step.file)
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return ""


def step_ok(steps: list[StepResult], name: str) -> bool:
    return any(step.name == name and step.ok for step in steps)


def run_preflight(args: argparse.Namespace, store: EvidenceStore) -> list[StepResult]:
    store.mkdir("native")
    return [capture_command(args, store, name, command, timeout=timeout) for name, command, timeout in PREFLIGHT_COMMANDS]


def cleanup_nodes(args: argparse.Namespace, store: EvidenceStore, prefix: str = "cleanup") -> list[StepResult]:
    return [capture_command(args, store, prefix, ["run", TOYBOX, "rm", "-f", *CLEANUP_PATHS], timeout=10.0)]


def create_nodes(args: argparse.Namespace, store: EvidenceStore, preflight: list[StepResult]) -> list[StepResult]:
    steps: list[StepResult] = []
    if not step_ok(preflight, "stat-dev-block-dir"):
        steps.append(capture_command(args, store, "mkdir-dev-block", ["mkdir", "/dev/block"], timeout=10.0))
    path, major, minor = VENDOR_NODE
    if not step_ok(preflight, "stat-vendor-block"):
        steps.append(capture_command(args, store, "create-vendor-block", ["mknodb", path, str(major), str(minor)], timeout=10.0))
    for path, (major, minor) in BINDER_NODES.items():
        name = Path(path).name
        if not step_ok(preflight, f"stat-dev-{name}"):
            steps.append(capture_command(args, store, f"create-{name}", ["mknodc", path, str(major), str(minor)], timeout=10.0))
    return steps


def stat_created(args: argparse.Namespace, store: EvidenceStore) -> list[StepResult]:
    commands = [("created-stat-vendor-block", ["stat", VENDOR_BLOCK])]
    commands.extend((f"created-stat-{Path(path).name}", ["stat", path]) for path in BINDER_NODES)
    return [capture_command(args, store, name, command, timeout=10.0) for name, command in commands]


def property_lookup(args: argparse.Namespace, store: EvidenceStore) -> StepResult:
    return capture_command(
        args,
        store,
        "property-lookup",
        [
            "run", HELPER,
            "--system-root", SYSTEM_ROOT,
            "--vendor-block", VENDOR_BLOCK,
            "--vendor-fstype", "ext4",
            "--target-profile", "system-getprop",
            "--mode", "property-lookup",
            "--null-device-mode", "dev-null",
            "--property-root", PROPERTY_ROOT,
            "--property-key", "ro.build.version.sdk",
            "--timeout-sec", "10",
        ],
        timeout=20.0,
    )


def postflight(args: argparse.Namespace, store: EvidenceStore) -> list[StepResult]:
    return [
        capture_command(args, store, "post-stat-vendor-block", ["stat", VENDOR_BLOCK], timeout=10.0),
        capture_command(args, store, "post-stat-binder", ["stat", "/dev/binder"], timeout=10.0),
        capture_command(args, store, "post-stat-hwbinder", ["stat", "/dev/hwbinder"], timeout=10.0),
        capture_command(args, store, "post-stat-vndbinder", ["stat", "/dev/vndbinder"], timeout=10.0),
        capture_command(args, store, "post-ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], timeout=20.0),
        capture_command(args, store, "post-proc-net-dev", ["cat", "/proc/net/dev"], timeout=10.0),
        capture_command(args, store, "post-version", ["version"], timeout=10.0),
    ]


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace, store: EvidenceStore, v365: dict[str, Any], steps: list[StepResult]) -> list[Check]:
    checks: list[Check] = []
    v365_ok = v365.get("decision") == "service-runtime-repair-packet-ready" and bool(v365.get("pass"))
    add_check(checks, "v365-packet", "pass" if v365_ok else "missing", "info" if v365_ok else "blocker",
              f"decision={v365.get('decision')} pass={v365.get('pass')}", [str(v365.get("path", ""))],
              "V365 packet is required before V366 smoke")
    if args.command == "plan":
        add_check(checks, "approval-gate", "needs-operator", "approval",
                  "plan-only mode; no live command executed", [APPROVAL_PHRASE],
                  "exact phrase required for any temporary node creation")
        return checks
    version_text = capture_text(store, steps, "version") or capture_text(store, steps, "post-version")
    add_check(checks, "native-version", "pass" if args.expect_version in version_text else "warn",
              "info" if args.expect_version in version_text else "warning", f"expect_version={args.expect_version}",
              [line for line in version_text.splitlines() if "A90 Linux init" in line][:3],
              "refresh defaults if native version changed")
    required_preflight = ("stat-helper", "stat-ld-config", "stat-apex-libraries", "stat-property-root", "stat-system-root")
    missing = [name for name in required_preflight if not step_ok(steps, name)]
    add_check(checks, "preflight-inputs", "pass" if not missing else "missing", "info" if not missing else "blocker",
              f"missing={missing}", missing, "all helper/property/linker inputs must exist")
    partitions = capture_text(store, steps, "proc-partitions")
    sda29 = bool(re.search(r"^\s*259\s+13\s+\d+\s+sda29\s*$", partitions, re.MULTILINE))
    add_check(checks, "vendor-partition-metadata", "pass" if sda29 else "missing", "info" if sda29 else "blocker",
              "sda29=259:13" if sda29 else "sda29 not found", [], "do not create vendor node without partition metadata")
    approval_ok = args.approval_phrase == APPROVAL_PHRASE and args.apply and args.assume_yes
    add_check(checks, "approval-gate", "pass" if approval_ok else "needs-operator", "approval",
              f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} apply={args.apply} assume_yes={args.assume_yes}",
              [APPROVAL_PHRASE], "exact phrase required for any temporary node creation")
    property_text = capture_text(store, steps, "property-lookup")
    if any(step.name == "property-lookup" for step in steps):
        prop_ok = step_ok(steps, "property-lookup") and "helper_status=namespace-ready" in property_text and "child_exit_code=0" in property_text
        add_check(checks, "property-lookup-smoke", "pass" if prop_ok else "failed", "info" if prop_ok else "blocker",
                  "helper_status/child_exit_code checked", [], "property lookup must pass inside private namespace")
    post_names = ("post-stat-vendor-block", "post-stat-binder", "post-stat-hwbinder", "post-stat-vndbinder")
    if any(any(step.name == name for step in steps) for name in post_names):
        still_present = [name for name in post_names if step_ok(steps, name)]
        add_check(checks, "post-node-cleanup", "clean" if not still_present else "present",
                  "info" if not still_present else "blocker", f"still_present={still_present}", still_present,
                  "temporary nodes must be removed after smoke")
    ps_text = capture_text(store, steps, "post-ps") or capture_text(store, steps, "ps")
    manager_lines = [line.strip() for line in ps_text.splitlines() if MANAGER_PROCESS_RE.search(line)]
    cnss_lines = [line.strip() for line in ps_text.splitlines() if CNSS_PROCESS_RE.search(line)]
    net_text = capture_text(store, steps, "post-proc-net-dev") or capture_text(store, steps, "proc-net-dev")
    wlan = WLAN_NETDEV_RE.search(net_text) is not None
    add_check(checks, "post-service-process-clean", "clean" if not manager_lines and not cnss_lines else "present",
              "info" if not manager_lines and not cnss_lines else "blocker",
              f"manager={len(manager_lines)} cnss={len(cnss_lines)}", manager_lines[:6] + cnss_lines[:6],
              "smoke must not leave service-manager or CNSS processes")
    add_check(checks, "post-wifi-link-clean", "clean" if not wlan else "present", "info" if not wlan else "blocker",
              f"wlan_surface={wlan}", [], "smoke must not create Wi-Fi link surface")
    return checks


def check_blocks(check: Check) -> bool:
    if check.severity != "blocker":
        return False
    return check.status not in {"pass", "clean"}


def decide(args: argparse.Namespace, checks: list[Check], steps: list[StepResult]) -> tuple[bool, str, str]:
    blockers = [check.name for check in checks if check_blocks(check)]
    if blockers:
        return False, "runtime-repair-smoke-blocked", "blocked by " + ", ".join(blockers)
    if args.command == "plan":
        return True, "runtime-repair-smoke-plan-ready", "plan-only; no live command executed"
    if args.command == "preflight":
        return True, "runtime-repair-smoke-preflight-ready", "preflight ready; run still requires exact approval"
    if args.command == "cleanup":
        cleanup_ok = any(step.name == "cleanup" and step.ok for step in steps)
        return cleanup_ok, "runtime-repair-smoke-cleanup-done" if cleanup_ok else "runtime-repair-smoke-cleanup-failed", "cleanup attempted"
    approval = next((check for check in checks if check.name == "approval-gate"), None)
    if approval is None or approval.status != "pass":
        return True, "runtime-repair-smoke-approval-required", "exact approval phrase required; no mutation executed"
    if any(step.name == "property-lookup" for step in steps):
        return True, "runtime-repair-smoke-pass", "temporary runtime repair smoke passed and cleaned up"
    return False, "runtime-repair-smoke-not-run", "approved run did not execute smoke steps"


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["command"], s["file"]] for s in manifest["steps"]]
    return "\n".join([
        "# V366 Runtime Repair Smoke",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- mode: `{manifest['mode']}`",
        f"- apply: `{manifest['apply']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- required approval phrase: `{manifest['required_approval_phrase']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "command", "file"], step_rows),
        "",
        "## Guardrails",
        "",
        "- no service-manager, hwservicemanager, or vndservicemanager execution",
        "- no Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or cnss_diag execution",
        "- no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
        "- cleanup is attempted in a finally block for approved runs",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v365 = load_manifest(args.v365_manifest)
    steps: list[StepResult] = []
    if args.command in {"preflight", "run"}:
        steps.extend(run_preflight(args, store))
    elif args.command == "cleanup":
        store.mkdir("native")
        steps.extend(cleanup_nodes(args, store))
        steps.extend(postflight(args, store))
    else:
        store.mkdir("native")
    approval_ok = args.command == "run" and args.approval_phrase == APPROVAL_PHRASE and args.apply and args.assume_yes
    if approval_ok:
        try:
            steps.extend(create_nodes(args, store, steps))
            steps.extend(stat_created(args, store))
            steps.append(property_lookup(args, store))
        finally:
            steps.extend(cleanup_nodes(args, store))
            steps.extend(postflight(args, store))
    checks = build_checks(args, store, v365, steps)
    pass_ok, decision, reason = decide(args, checks, steps)
    return {
        "generated_at": now_iso(),
        "mode": args.command,
        "apply": bool(args.apply),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "expect_version": args.expect_version,
        "required_approval_phrase": APPROVAL_PHRASE,
        "v365_manifest": {"path": str(repo_path(args.v365_manifest)), "decision": v365.get("decision"), "pass": v365.get("pass")},
        "steps": [asdict(step) for step in steps],
        "checks": [asdict(check) for check in checks],
        "host": collect_host_metadata(),
        "guardrails": [
            "no service-manager execution",
            "no Wi-Fi HAL, wificond, supplicant, hostapd, cnss-daemon, or cnss_diag execution",
            "no Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "cleanup attempted for approved runs",
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
    print(f"required_approval_phrase: {manifest['required_approval_phrase']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
