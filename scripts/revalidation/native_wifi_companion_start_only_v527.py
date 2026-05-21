#!/usr/bin/env python3
"""V527 bounded native Wi-Fi companion start-only proof.

This proof starts only the V525 Android-observed companion service set in the
Android order: qrtr-ns, rmt_storage, tftp_server, pd-mapper, cnss_diag, and
cnss-daemon. It does not start service-manager, Wi-Fi HAL, wificond,
supplicant, hostapd, scan, connect, request DHCP, change routes, or ping
externally.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v527-companion-start-only")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "11fcecad47a684d9a9a7ddd782189c11cf16b7f5cb25fe222379635c9ae782f5"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v61"
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v527-v490-current-run/manifest.json")
DEFAULT_V525_MANIFEST = Path("tmp/wifi/v526-android-companion-identity-handoff-run/v525-android-companion-identity-run/manifest.json")
HELPER_MODE = "wifi-companion-start-only"
PROOF_VERSION = "V527"
PROOF_SLUG = "v527-companion-start-only"
LIVE_HELPER_STEP_NAME = "v527-helper-run"
APPROVAL_PHRASE = (
    "approve v527 companion start-only proof only; "
    "no service-manager, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)

KEY_RE = re.compile(r"^(wifi_companion_start|wifi_hal_composite_start|wifi_hal_composite_child)\.([A-Za-z0-9_.-]+)=(.*)$")
PROCESS_RE = re.compile(
    r"\b(qrtr-ns|rmt_storage|tftp_server|pd-mapper|cnss_diag|cnss-daemon|servicemanager|hwservicemanager|wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
DMESG_TS_RE = re.compile(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]")
DMESG_PATTERNS = {
    "qrtr_modem_readiness": re.compile(r"Modem QMI Readiness|qrtr.*modem", re.IGNORECASE),
    "qrtr": re.compile(r"\bqrtr\b|qrtr-ns", re.IGNORECASE),
    "rmt_storage": re.compile(r"rmt_storage|rmtfs", re.IGNORECASE),
    "tftp_server": re.compile(r"tftp_server|tqftp|tftp", re.IGNORECASE),
    "pd_mapper": re.compile(r"pd-mapper|pd_mapper|pdr", re.IGNORECASE),
    "cnss_diag_netlink": re.compile(r"netlink_create.*comm:\s*cnss_diag|comm:cnss_diag", re.IGNORECASE),
    "cnss_daemon_netlink": re.compile(r"netlink_create.*comm:\s*cnss-daemon|comm:cnss-daemon|cnss-daemon.*ctrl_getfamily", re.IGNORECASE),
    "wlfw_start": re.compile(r"cnss-daemon wlfw_start: Starting", re.IGNORECASE),
    "wlfw_thread": re.compile(r"cnss-daemon wlfw_service_request", re.IGNORECASE),
    "qmi_server_connected": re.compile(r"icnss_qmi: QMI Server Connected", re.IGNORECASE),
    "bdf_regdb": re.compile(r"BDF file\s*:\s*regdb\.bin", re.IGNORECASE),
    "bdf_bdwlan": re.compile(r"BDF file\s*:\s*bdwlan\.bin", re.IGNORECASE),
    "wlan_fw_ready": re.compile(r"icnss: WLAN FW is ready", re.IGNORECASE),
    "wcnss_cfg_request": re.compile(r"WCNSS_qcom_cfg\.ini", re.IGNORECASE),
    "wma_service_ready": re.compile(r"wma_rx_service_ready_event|FW ready event received", re.IGNORECASE),
    "wlan0_event": re.compile(r"dev\s*:\s*wlan0\s*:\s*event", re.IGNORECASE),
    "avc_denied": re.compile(r"\bavc:\s+denied\b", re.IGNORECASE),
    "timed_out": re.compile(r"Timed-out!!", re.IGNORECASE),
    "modules_not_initialized": re.compile(r"Modules not initialized just return", re.IGNORECASE),
}
READINESS_MARKERS = (
    "qrtr_modem_readiness",
    "wlfw_start",
    "wlfw_thread",
    "qmi_server_connected",
    "bdf_regdb",
    "bdf_bdwlan",
    "wlan_fw_ready",
    "wcnss_cfg_request",
    "wma_service_ready",
    "wlan0_event",
)


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
    parser.add_argument("--host", "--bridge-host", dest="host", default=DEFAULT_HOST)
    parser.add_argument("--port", "--bridge-port", dest="port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--expect-version", default=DEFAULT_EXPECT_VERSION)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--v525-manifest", type=Path, default=DEFAULT_V525_MANIFEST)
    parser.add_argument("--max-runtime-sec", type=int, default=10)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.apply and args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def helper_label(args: argparse.Namespace) -> str:
    marker = str(args.helper_marker).strip()
    return marker.rsplit(" ", 1)[-1] if marker else "helper"


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


def step_payload(steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return str(step.get("payload") or "")
    return ""


def parse_keys(text: str) -> dict[str, str]:
    keys: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = KEY_RE.match(line)
        if match:
            keys[f"{match.group(1)}.{match.group(2)}"] = match.group(3).strip()
    return keys


def dmesg_last_timestamp(text: str) -> float | None:
    last: float | None = None
    for raw_line in text.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        match = DMESG_TS_RE.match(line)
        if match:
            last = float(match.group(1))
    return last


def dmesg_delta_text(before: str, after: str) -> str:
    before_last = dmesg_last_timestamp(before)
    if before_last is None:
        return after[len(before):] if after.startswith(before) else after
    lines = []
    for raw_line in after.splitlines():
        line = ANSI_RE.sub("", raw_line).strip()
        match = DMESG_TS_RE.match(line)
        if match and float(match.group(1)) > before_last:
            lines.append(raw_line)
    return "\n".join(lines) + ("\n" if lines else "")


def dmesg_summary(text: str) -> dict[str, Any]:
    lines = [ANSI_RE.sub("", line).strip() for line in text.splitlines() if line.strip()]
    events: dict[str, list[str]] = {name: [] for name in DMESG_PATTERNS}
    for line in lines:
        for name, pattern in DMESG_PATTERNS.items():
            if pattern.search(line):
                events[name].append(line)
    counts = {name: len(items) for name, items in events.items()}
    return {
        "counts": counts,
        "latest": {name: (items[-1] if items else "") for name, items in events.items()},
        "readiness_markers": [name for name in READINESS_MARKERS if counts.get(name, 0) > 0],
        "focus_tail": [line for name in DMESG_PATTERNS for line in events[name]][-160:],
    }


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    data = json.loads(resolved.read_text(encoding="utf-8"))
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def parse_status_uptime_sec(text: str) -> float | None:
    match = re.search(r"^uptime:\s*([0-9]+(?:\.[0-9]+)?)s", text, re.MULTILINE)
    return float(match.group(1)) if match else None


def manifest_generated_at_epoch(manifest: dict[str, Any]) -> float | None:
    generated = manifest.get("generated_at")
    if not isinstance(generated, str) or not generated:
        return None
    try:
        return dt.datetime.fromisoformat(generated.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def v490_current_for_boot(v490: dict[str, Any], status_text: str) -> tuple[bool, str]:
    uptime = parse_status_uptime_sec(status_text)
    generated = manifest_generated_at_epoch(v490)
    if uptime is None or generated is None:
        return False, f"uptime={uptime} generated={generated}"
    boot_epoch = dt.datetime.now(dt.timezone.utc).timestamp() - uptime
    fresh = generated >= boot_epoch - 120.0
    return fresh, f"generated_epoch={generated:.0f} boot_epoch={boot_epoch:.0f} uptime={uptime:.1f}s"


def preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    store.mkdir("native")
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 20.0),
        run_step(args, store, "selftest", ["selftest"], 20.0),
        run_step(args, store, "sha-helper", ["run", "/cache/bin/toybox", "sha256sum", args.helper], 20.0),
        run_step(args, store, "helper-usage", ["run", args.helper, "--help"], 20.0),
        run_step(args, store, "ps", ["run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
        run_step(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        run_step(args, store, "proc-net-qrtr", ["run", "/cache/bin/toybox", "cat", "/proc/net/qrtr"], 10.0),
        run_step(args, store, "proc-mounts", ["run", "/cache/bin/toybox", "cat", "/proc/mounts"], 10.0),
        run_step(args, store, "selinux-current", ["run", "/cache/bin/toybox", "cat", "/proc/self/attr/current"], 10.0),
        run_step(args, store, "selinux-enforce", ["run", "/cache/bin/toybox", "cat", "/sys/fs/selinux/enforce"], 10.0),
    ]


def helper_command(args: argparse.Namespace) -> list[str]:
    command = [
        "run", args.helper,
        "--system-root", "/mnt/system/system",
        "--vendor-block", "/dev/block/sda29",
        "--vendor-fstype", "ext4",
        "--mode", HELPER_MODE,
        "--null-device-mode", "dev-null",
        "--vndk-apex-alias-mode", "v30-to-system-ext-v30",
        "--linkerconfig-mode", "minimal-vendor",
        "--android-selinux-context-mode", "service-defaults",
        "--timeout-sec", str(args.max_runtime_sec),
    ]
    if approved(args):
        command.extend(["--allow-cnss-start-only", "--allow-wifi-companion-start-only"])
    return command


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    before = run_step(args, store, "dmesg-before", ["run", "/cache/bin/toybox", "dmesg"], 60.0)
    qrtr_before = run_step(args, store, "qrtr-before", ["run", "/cache/bin/toybox", "cat", "/proc/net/qrtr"], 10.0)
    live = run_step(args, store, LIVE_HELPER_STEP_NAME, helper_command(args), args.max_runtime_sec + 45.0)
    after = run_step(args, store, "dmesg-after", ["run", "/cache/bin/toybox", "dmesg"], 60.0)
    qrtr_after = run_step(args, store, "qrtr-after", ["run", "/cache/bin/toybox", "cat", "/proc/net/qrtr"], 10.0)
    post_ps = run_step(args, store, "post-ps", ["run", "/cache/bin/toybox", "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    post_net = run_step(args, store, "post-proc-net-dev", ["cat", "/proc/net/dev"], 10.0)
    keys = parse_keys(step_payload([live], LIVE_HELPER_STEP_NAME))
    dmesg_delta = dmesg_delta_text(step_payload([before], "dmesg-before"), step_payload([after], "dmesg-after"))
    write_capture(store, "dmesg-delta", dmesg_delta)
    return {
        "before": before,
        "qrtr_before": qrtr_before,
        "live": live,
        "after": after,
        "qrtr_after": qrtr_after,
        "dmesg_delta": dmesg_delta,
        "post_ps": post_ps,
        "post_net": post_net,
        "keys": keys,
        "helper_result": keys.get("wifi_companion_start.result", "missing"),
        "all_postflight_safe": keys.get("wifi_companion_start.all_postflight_safe") == "1",
        "all_observable": keys.get("wifi_companion_start.all_observable") == "1",
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 v490: dict[str, Any],
                 v525: dict[str, Any]) -> list[Check]:
    checks: list[Check] = []
    if args.command == "plan":
        add_check(checks, "plan-only", "pass", "info", "no device command executed", [], "run preflight")
        return checks

    version = step_payload(steps, "version")
    status = step_payload(steps, "status")
    selftest = step_payload(steps, "selftest")
    helper_sha = step_payload(steps, "sha-helper")
    helper_usage = step_payload(steps, "helper-usage")
    ps = step_payload(steps, "ps")
    netdev = step_payload(steps, "proc-net-dev")
    mounts = step_payload(steps, "proc-mounts")
    process_hits = [line.strip() for line in ps.splitlines() if PROCESS_RE.search(line)]
    wifi_hits = [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)]
    helper_ready = args.helper_sha256 in helper_sha and args.helper_marker in helper_usage and HELPER_MODE in helper_usage
    v490_fresh, v490_fresh_detail = v490_current_for_boot(v490, status) if v490.get("exists") else (False, "manifest-missing")
    v525_summary = v525.get("android_summary") or {}

    label = helper_label(args)

    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2],
              f"restore native baseline before {PROOF_VERSION}")
    add_check(checks, f"helper-{label}-ready", "pass" if helper_ready else "blocked", "blocker",
              f"sha_match={args.helper_sha256 in helper_sha} marker={args.helper_marker in helper_usage} mode={HELPER_MODE in helper_usage}",
              [args.helper_sha256, args.helper_marker, HELPER_MODE],
              f"deploy helper {label} before {PROOF_VERSION}")
    add_check(checks, "selinuxfs-mounted", "pass" if "/sys/fs/selinux" in mounts and " selinuxfs " in mounts else "blocked", "blocker",
              "global SELinuxfs must be mounted before post-load domains are used",
              [line for line in mounts.splitlines() if "/sys/fs/selinux" in line][:3],
              "run approved V401 toybox selinuxfs mount")
    add_check(checks, "v490-current-policy-load", "pass" if v490.get("decision") == "v490-selinux-policy-load-proof-pass" and v490.get("policy_load_executed") is True and v490_fresh else "blocked", "blocker",
              f"decision={v490.get('decision')} policy_load={v490.get('policy_load_executed')} fresh={v490_fresh} {v490_fresh_detail}",
              [str(v490.get("path"))],
              f"run approved V490 after current boot before {PROOF_VERSION} live")
    add_check(checks, "v525-identity-contract", "pass" if v525.get("decision") == "v525-companion-identity-captured" and v525.get("pass") is True and v525_summary.get("all_required_process_identities") else "blocked", "blocker",
              f"decision={v525.get('decision')} pass={v525.get('pass')} identities={v525_summary.get('all_required_process_identities')}",
              [str(v525.get("path"))],
              "capture Android companion identities before native replay")
    add_check(checks, "no-active-target-processes", "pass" if not process_hits else "blocked", "blocker",
              f"process_count={len(process_hits)}", process_hits[:8],
              "cleanup residual companion/Wi-Fi processes before bounded replay")
    add_check(checks, "no-wifi-link-surface", "pass" if not wifi_hits else "blocked", "blocker",
              f"wifi_hits={len(wifi_hits)}", wifi_hits[:8],
              f"if wlan0 already exists, move to scan-only instead of {PROOF_VERSION}")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def classify(args: argparse.Namespace,
             checks: list[Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return f"{PROOF_SLUG}-plan-ready", True, "plan-only; no device command executed", f"run V401/V490 current preconditions, deploy {helper_label(args)}, then preflight", False
    blocked = blockers(checks)
    if blocked:
        return f"{PROOF_SLUG}-blocked", False, "blocked before live run by " + ", ".join(blocked), f"resolve blockers before {PROOF_VERSION}", False
    if args.command == "preflight":
        return f"{PROOF_SLUG}-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", f"run approved {PROOF_VERSION} companion start-only proof", False
    if not approved(args):
        return f"{PROOF_SLUG}-approval-required", True, "exact approval phrase required; no live command executed", f"rerun with exact {PROOF_VERSION} approval", False
    if not live_result:
        return f"{PROOF_SLUG}-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return f"{PROOF_SLUG}-cleanup-review", False, "helper-owned companion children were not proven cleaned", "inspect evidence and consider recovery reboot", True

    readiness_markers = dmesg.get("readiness_markers") or []
    helper_result = live_result["helper_result"]
    if readiness_markers:
        return f"{PROOF_SLUG}-marker-observed", True, "bounded companion replay observed readiness markers: " + ",".join(readiness_markers), "advance to bounded HAL/qcwlanstate retry; still no scan/connect", True
    if helper_result == "companion-window-pass":
        return f"{PROOF_SLUG}-no-fw-marker", True, "all companions were observable and cleaned, but no QRTR/QMI/WLFW/BDF/FW-ready marker appeared", "inspect QRTR/proc-net delta and companion logs before qcwlanstate retry", True
    if helper_result == "start-only-runtime-gap":
        return f"{PROOF_SLUG}-runtime-gap", True, "one companion child exited before the observe window", "inspect child stdout/stderr, SELinux, and missing runtime resources", True
    return f"{PROOF_SLUG}-review-required", False, f"helper_result={helper_result}", f"inspect {PROOF_VERSION} transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    dmesg = manifest.get("dmesg_summary") or {}
    count_rows = [[key, value] for key, value in sorted((dmesg.get("counts") or {}).items())]
    return "\n".join([
        f"# {PROOF_VERSION} Companion Start-Only Proof",
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
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Dmesg Pattern Counts",
        "",
        markdown_table(["pattern", "count"], count_rows) if count_rows else "- none",
        "",
        "## Readiness Markers",
        "",
        ", ".join(dmesg.get("readiness_markers") or []) or "- none",
        "",
        "## Evidence",
        "",
        f"- `{manifest['out_dir']}`",
        "",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    live_result: dict[str, Any] | None = None
    v490 = load_manifest(args.v490_manifest)
    v525 = load_manifest(args.v525_manifest)
    if args.command != "plan":
        steps = preflight_steps(args, store)
    checks = build_checks(args, steps, v490, v525)
    if args.command == "run" and approved(args) and not blockers(checks):
        live_result = run_live(args, store)
    dmesg = dmesg_summary(str(live_result.get("dmesg_delta", ""))) if live_result else dmesg_summary("")
    decision, pass_ok, reason, next_step, live_executed = classify(args, checks, live_result, dmesg)
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
        "live_result": live_result,
        "dmesg_summary": dmesg,
        "v490_manifest": {
            "exists": v490.get("exists"),
            "path": v490.get("path"),
            "decision": v490.get("decision"),
            "pass": v490.get("pass"),
            "policy_load_executed": v490.get("policy_load_executed"),
            "generated_at": v490.get("generated_at"),
        },
        "v525_manifest": {
            "exists": v525.get("exists"),
            "path": v525.get("path"),
            "decision": v525.get("decision"),
            "pass": v525.get("pass"),
        },
        "required_approval_phrase": APPROVAL_PHRASE,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "apply": args.apply,
        "assume_yes": args.assume_yes,
        "device_commands_executed": args.command != "plan",
        "device_mutations": live_executed,
        "daemon_start_executed": live_executed,
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
