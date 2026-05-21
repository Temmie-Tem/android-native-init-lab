#!/usr/bin/env python3
"""V533 bounded rmt_storage start-only proof.

This proof starts only `/vendor/bin/rmt_storage` inside the helper-owned
private namespace.  It does not start qrtr-ns, tftp_server, pd-mapper,
cnss_diag, cnss-daemon, service-manager, Wi-Fi HAL, scan, connect, DHCP, or
external ping.  The helper v66 namespace supplies the V529-classified
rmt_storage runtime surfaces plus private UIO sysfs files and /dev/kmsg diagnostics.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v533-rmt-storage-start-only")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 54321
DEFAULT_TIMEOUT = 45.0
DEFAULT_EXPECT_VERSION = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_HELPER_SHA256 = "d64f389601783d8826f2821febc681c1b12e9bd7cd6a3e2fae9d77461331faa5"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v66"
DEFAULT_PROPERTY_ROOT = "/mnt/sdext/a90/private-property-v317/v471/dev/__properties__"
DEFAULT_V490_MANIFEST = Path("tmp/wifi/v527-v490-current-run/manifest.json")
DEFAULT_V529_MANIFEST = Path("tmp/wifi/v529-rmt-storage-surface-classifier/manifest.json")
APPROVAL_PHRASE = (
    "approve v533 rmt-storage start-only proof only; "
    "no service-manager, no CNSS daemon, no Wi-Fi HAL start, no scan/connect/link-up and no external ping"
)
HELPER_MODE = "rmt-storage-start-only"
TOYBOX = "/cache/bin/toybox"
PROCESS_RE = re.compile(
    r"\b(qrtr-ns|rmt_storage|tftp_server|pd-mapper|cnss_diag|cnss-daemon|servicemanager|hwservicemanager|wificond|supplicant|hostapd|android\.hardware\.wifi|vendor\.samsung\.hardware\.wifi)\b",
    re.IGNORECASE,
)
WIFI_RE = re.compile(r"\b(wlan\d*|swlan\d*|p2p\d*|wifi-aware\d*|wiphy\d*|phy\d+)\b", re.IGNORECASE)
KEY_RE = re.compile(r"^(rmt_storage_start|wifi_hal_composite_start|wifi_hal_composite_child|context)\.([A-Za-z0-9_.-]+)=(.*)$")
DMESG_PATTERNS = {
    "rmt_storage": re.compile(r"rmt_storage|rmtfs", re.IGNORECASE),
    "qmi": re.compile(r"\bqmi\b|qmi_csi|qmi_server", re.IGNORECASE),
    "uio": re.compile(r"\buio\b|rmts", re.IGNORECASE),
    "wake": re.compile(r"wake_lock|wakelock", re.IGNORECASE),
    "block": re.compile(r"modemst|fsg|fsc|bootdevice|by-name|block", re.IGNORECASE),
    "avc_denied": re.compile(r"\bavc:\s+denied\b", re.IGNORECASE),
}


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
    parser.add_argument("--property-root", default=DEFAULT_PROPERTY_ROOT)
    parser.add_argument("--v490-manifest", type=Path, default=DEFAULT_V490_MANIFEST)
    parser.add_argument("--v529-manifest", type=Path, default=DEFAULT_V529_MANIFEST)
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
        match = KEY_RE.match(raw_line.strip())
        if match:
            keys[f"{match.group(1)}.{match.group(2)}"] = match.group(3).strip()
    return keys


def execns_section(text: str, name: str) -> str:
    pattern = re.compile(
        rf"^A90_EXECNS_{re.escape(name)}_BEGIN\n(.*?)^A90_EXECNS_{re.escape(name)}_END .*$",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def tail_lines(text: str, limit: int = 40) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    return lines[-limit:]


def focus_key_rows(keys: dict[str, str]) -> list[list[str]]:
    prefixes = (
        "rmt_storage_start.",
        "wifi_hal_composite_child.rmt_storage.",
        "context.dev_kmsg.",
        "context.dev_uio0.",
        "context.sys_class_uio0_",
        "context.sys_power_",
    )
    rows: list[list[str]] = []
    for key in sorted(keys):
        if key.startswith(prefixes):
            rows.append([key, keys[key]])
    return rows


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["exists"] = True
    payload["path"] = str(resolved)
    return payload


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


def current_for_boot(manifest: dict[str, Any], status_text: str) -> tuple[bool, str]:
    uptime = parse_status_uptime_sec(status_text)
    generated = manifest_generated_at_epoch(manifest)
    if uptime is None or generated is None:
        return False, f"uptime={uptime} generated={generated}"
    boot_epoch = dt.datetime.now(dt.timezone.utc).timestamp() - uptime
    fresh = generated >= boot_epoch - 120.0
    return fresh, f"generated_epoch={generated:.0f} boot_epoch={boot_epoch:.0f} uptime={uptime:.1f}s"


def dmesg_summary(text: str) -> dict[str, Any]:
    events = {name: [] for name in DMESG_PATTERNS}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for name, pattern in DMESG_PATTERNS.items():
            if pattern.search(line):
                events[name].append(line)
    return {
        "counts": {name: len(lines) for name, lines in events.items()},
        "latest": {name: (lines[-1] if lines else "") for name, lines in events.items()},
        "focus_tail": [line for lines in events.values() for line in lines][-120:],
    }


def dmesg_last_timestamp(text: str) -> float | None:
    last: float | None = None
    for line in text.splitlines():
        match = re.match(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]", line.strip())
        if match:
            last = float(match.group(1))
    return last


def dmesg_delta_text(before: str, after: str) -> str:
    before_last = dmesg_last_timestamp(before)
    if before_last is None:
        return after[len(before):] if after.startswith(before) else after
    lines = []
    for line in after.splitlines():
        match = re.match(r"^\[\s*([0-9]+(?:\.[0-9]+)?)\]", line.strip())
        if match and float(match.group(1)) > before_last:
            lines.append(line)
    return "\n".join(lines) + ("\n" if lines else "")


def preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    return [
        run_step(args, store, "version", ["version"], 15.0),
        run_step(args, store, "status", ["status"], 20.0),
        run_step(args, store, "selftest", ["selftest"], 20.0),
        run_step(args, store, "sha-helper", ["run", TOYBOX, "sha256sum", args.helper], 20.0),
        run_step(args, store, "helper-usage", ["run", args.helper, "--help"], 20.0),
        run_step(args, store, "ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0),
        run_step(args, store, "proc-net-dev", ["cat", "/proc/net/dev"], 10.0),
        run_step(args, store, "proc-mounts", ["run", TOYBOX, "cat", "/proc/mounts"], 10.0),
        run_step(args, store, "property-root-ls", ["run", TOYBOX, "ls", "-ld", args.property_root], 10.0),
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
        "--property-root", args.property_root,
        "--timeout-sec", str(args.max_runtime_sec),
    ]
    if approved(args):
        command.append("--allow-wifi-companion-start-only")
    return command


def run_live(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    before = run_step(args, store, "dmesg-before", ["run", TOYBOX, "dmesg"], 60.0)
    live = run_step(args, store, "v533-helper-run", helper_command(args), args.max_runtime_sec + 45.0)
    after = run_step(args, store, "dmesg-after", ["run", TOYBOX, "dmesg"], 60.0)
    post_ps = run_step(args, store, "post-ps", ["run", TOYBOX, "ps", "-A", "-o", "pid,stat,comm,args"], 20.0)
    live_text = step_payload([live], "v533-helper-run")
    keys = parse_keys(live_text)
    helper_stdout = execns_section(live_text, "STDOUT")
    helper_stderr = execns_section(live_text, "STDERR")
    dmesg_delta = dmesg_delta_text(step_payload([before], "dmesg-before"), step_payload([after], "dmesg-after"))
    write_capture(store, "dmesg-delta", dmesg_delta)
    write_capture(store, "helper-stdout-section", helper_stdout or "<empty>")
    write_capture(store, "helper-stderr-section", helper_stderr or "<empty>")
    return {
        "before": before,
        "live": live,
        "after": after,
        "post_ps": post_ps,
        "keys": keys,
        "focus_keys": focus_key_rows(keys),
        "helper_stdout_tail": tail_lines(helper_stdout, 50),
        "helper_stderr_tail": tail_lines(helper_stderr, 80),
        "helper_result": keys.get("rmt_storage_start.result", "missing"),
        "all_postflight_safe": keys.get("rmt_storage_start.all_postflight_safe") == "1",
        "all_observable": keys.get("rmt_storage_start.all_observable") == "1",
        "dmesg_delta": dmesg_delta,
    }


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str,
              evidence: list[str] | None = None, next_step: str = "") -> None:
    checks.append(Check(name, status, severity, detail, evidence or [], next_step))


def build_checks(args: argparse.Namespace,
                 steps: list[dict[str, Any]],
                 v490: dict[str, Any],
                 v529: dict[str, Any]) -> list[Check]:
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
    property_root = step_payload(steps, "property-root-ls")
    process_hits = [line.strip() for line in ps.splitlines() if PROCESS_RE.search(line)]
    wifi_hits = [line.strip() for line in netdev.splitlines() if WIFI_RE.search(line)]
    helper_ready = args.helper_sha256 in helper_sha and args.helper_marker in helper_usage and HELPER_MODE in helper_usage
    v490_fresh, v490_detail = current_for_boot(v490, status) if v490.get("exists") else (False, "manifest-missing")

    add_check(checks, "native-clean", "pass" if args.expect_version in version and "fail=0" in status and "fail=0" in selftest else "blocked", "blocker",
              f"expect_version={args.expect_version}", [line for line in version.splitlines() if "A90 Linux init" in line][:2],
              "restore native baseline before V533")
    add_check(checks, "helper-v66-ready", "pass" if helper_ready else "blocked", "blocker",
              f"sha_match={args.helper_sha256 in helper_sha} marker={args.helper_marker in helper_usage} mode={HELPER_MODE in helper_usage}",
              [args.helper_sha256, args.helper_marker, HELPER_MODE],
              "deploy helper v66 before V533")
    add_check(checks, "v490-current-policy-load", "pass" if v490.get("decision") == "v490-selinux-policy-load-proof-pass" and v490.get("policy_load_executed") is True and v490_fresh else "blocked", "blocker",
              f"decision={v490.get('decision')} policy_load={v490.get('policy_load_executed')} fresh={v490_fresh} {v490_detail}",
              [str(v490.get("path"))],
              "run approved V490 after current boot before V533")
    add_check(checks, "v529-surface-classifier", "pass" if v529.get("decision") == "v529-rmt-storage-runtime-surface-gap" and v529.get("pass") is True else "blocked", "blocker",
              f"decision={v529.get('decision')} pass={v529.get('pass')}",
              [str(v529.get("path"))],
              "run V529 read-only surface classifier first")
    add_check(checks, "property-root-present", "pass" if args.property_root in property_root and "No such file" not in property_root else "blocked", "blocker",
              f"property_root={args.property_root}",
              [line for line in property_root.splitlines() if args.property_root in line][:3],
              "refresh private property snapshot from Android before V533")
    add_check(checks, "no-active-target-processes", "pass" if not process_hits else "blocked", "blocker",
              f"process_count={len(process_hits)}", process_hits[:8],
              "cleanup residual Wi-Fi/companion processes before rmt-only proof")
    add_check(checks, "no-wifi-link-surface", "pass" if not wifi_hits else "blocked", "blocker",
              f"wifi_hits={len(wifi_hits)}", wifi_hits[:8],
              "do not run rmt-only proof while Wi-Fi link is already active")
    return checks


def blockers(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def classify(args: argparse.Namespace,
             checks: list[Check],
             live_result: dict[str, Any] | None,
             dmesg: dict[str, Any]) -> tuple[str, bool, str, str, bool]:
    if args.command == "plan":
        return "v533-rmt-storage-start-only-plan-ready", True, "plan-only; no device command executed", "deploy helper v66 and run preflight", False
    blocked = blockers(checks)
    if blocked:
        return "v533-rmt-storage-start-only-blocked", False, "blocked before live run by " + ", ".join(blocked), "resolve blockers before V533 live", False
    if args.command == "preflight":
        return "v533-rmt-storage-start-only-preflight-ready", True, "read-only preflight ready; live run still needs exact approval", "run approved V533 rmt-only proof", False
    if not approved(args):
        return "v533-rmt-storage-start-only-approval-required", True, "exact approval phrase required; no live command executed", "rerun with exact V533 approval", False
    if not live_result:
        return "v533-rmt-storage-start-only-review-required", False, "missing live result", "inspect runner failure", True
    if not live_result["all_postflight_safe"]:
        return "v533-rmt-storage-start-only-cleanup-review", False, "rmt_storage was not proven cleaned", "inspect evidence and consider recovery reboot", True
    helper_result = live_result["helper_result"]
    if helper_result == "rmt-window-pass":
        return "v533-rmt-storage-window-pass", True, "rmt_storage stayed observable through the bounded window and cleaned up", "advance to companion replay with v66 surfaces", True
    if helper_result == "start-only-runtime-gap":
        return "v533-rmt-storage-runtime-gap", True, "rmt_storage still exited before the observe window", "inspect stderr/context keys; add only the next missing surface", True
    return "v533-rmt-storage-review", True, f"helper_result={helper_result} dmesg_counts={dmesg.get('counts')}", "inspect V533 transcript", True


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    dmesg_rows = [[k, v] for k, v in sorted((manifest.get("dmesg_summary") or {}).get("counts", {}).items())]
    live = manifest.get("live_result") or {}
    focus_rows = live.get("focus_keys") or []
    stdout_tail = "\n".join(live.get("helper_stdout_tail") or [])
    stderr_tail = "\n".join(live.get("helper_stderr_tail") or [])
    return "\n".join([
        "# V533 rmt_storage Start-Only Proof",
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
        "## Dmesg Counts",
        "",
        markdown_table(["pattern", "count"], dmesg_rows) if dmesg_rows else "- none",
        "",
        "## Live Result",
        "",
        f"- helper_result: `{live.get('helper_result', '-')}`",
        f"- all_postflight_safe: `{live.get('all_postflight_safe', '-')}`",
        f"- all_observable: `{live.get('all_observable', '-')}`",
        "",
        "## Focus Keys",
        "",
        markdown_table(["key", "value"], focus_rows[:80]) if focus_rows else "- none",
        "",
        "## Helper STDERR Tail",
        "",
        "```text",
        stderr_tail or "<empty>",
        "```",
        "",
        "## Helper STDOUT Tail",
        "",
        "```text",
        stdout_tail or "<empty>",
        "```",
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
    v529 = load_manifest(args.v529_manifest)
    if args.command != "plan":
        steps = preflight_steps(args, store)
    checks = build_checks(args, steps, v490, v529)
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
        "v490_manifest": {"exists": v490.get("exists"), "path": v490.get("path"), "decision": v490.get("decision"), "pass": v490.get("pass")},
        "v529_manifest": {"exists": v529.get("exists"), "path": v529.get("path"), "decision": v529.get("decision"), "pass": v529.get("pass")},
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
