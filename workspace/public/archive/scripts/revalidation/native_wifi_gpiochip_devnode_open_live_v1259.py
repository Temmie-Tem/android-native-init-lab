#!/usr/bin/env python3
"""V1259 bounded temporary gpiochip devnode-open proof."""

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


DEFAULT_OUT_DIR = Path("tmp/wifi/v1259-gpiochip-devnode-open-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1259-gpiochip-devnode-open-live.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER_SHA256 = "17773e5bcdec090c061a962833d27a783439e1b718c96b47a504f625d79cc36d"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v262"
MODE = "wifi-companion-pmic-gpiochip-devnode-open-preflight"
ALLOW_FLAG = "--allow-pmic-gpiochip-devnode-open-preflight"
PREFIX = "pmic_gpiochip_devnode_open_preflight."
APPROVAL_PHRASE = (
    "approve v1259 temporary gpiochip devnode-open proof only; "
    "no GPIO line request, no PMIC write, no eSoC ioctl, no daemon start and no Wi-Fi bring-up"
)

SECRET_RE = re.compile(r"(made by|creator: made by) [^\r\n]+", re.IGNORECASE)


@dataclass
class Check:
    name: str
    status: str
    severity: str
    detail: str
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=54321)
    parser.add_argument("--timeout", type=float, default=35.0)
    parser.add_argument("--helper", default=DEFAULT_HELPER)
    parser.add_argument("--toybox", default=DEFAULT_TOYBOX)
    parser.add_argument("--helper-sha256", default=DEFAULT_HELPER_SHA256)
    parser.add_argument("--helper-marker", default=DEFAULT_HELPER_MARKER)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--assume-yes", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("preflight")
    subparsers.add_parser("run")
    return parser.parse_args()


def approved(args: argparse.Namespace) -> bool:
    return args.assume_yes and args.approval_phrase == APPROVAL_PHRASE


def redact(text: str) -> str:
    return SECRET_RE.sub(r"\1 [redacted]", text)


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value).strip("-") or "capture"


def capture_native(
    args: argparse.Namespace,
    store: EvidenceStore,
    name: str,
    command: list[str],
    *,
    timeout: float | None = None,
    allow_error: bool = False,
) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = capture.text if capture.text else capture.error + "\n"
    stripped = strip_cmdv1_text(text) if capture.text else text
    stripped = redact(stripped)
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, stripped.rstrip() + "\n")
    data = asdict(capture)
    data["text"] = redact(data.get("text") or "")
    if len(data["text"]) > 4096:
        data["text_sha256_like"] = "omitted-large-text"
        data["text"] = data["text"][:4096] + "\n[truncated in manifest]\n"
    data["file"] = rel
    data["ok"] = bool(capture.ok or allow_error)
    data["raw_ok"] = bool(capture.ok)
    return data


def read_step_text(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = str(step.get("file") or "")
    if not rel:
        return ""
    path = store.run_dir / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def step_text(store: EvidenceStore, steps: list[dict[str, Any]], name: str) -> str:
    for step in steps:
        if step.get("name") == name:
            return read_step_text(store, step)
    return ""


def parse_prefixed(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(PREFIX) or "=" not in line:
            continue
        key, value = line[len(PREFIX):].split("=", 1)
        values[key] = value
    return values


def helper_command(args: argparse.Namespace) -> list[str]:
    return [
        "run",
        args.toybox,
        "timeout",
        "10",
        args.helper,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--mode",
        MODE,
        "--target-profile",
        "system-toybox",
        "--capture-mode",
        "none",
        "--timeout-sec",
        "3",
        ALLOW_FLAG,
    ]


def common_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    return [
        capture_native(args, store, "hide", ["hide"], timeout=10.0),
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "netservice-status", ["netservice", "status"], timeout=10.0),
        capture_native(args, store, "helper-sha", ["run", args.toybox, "sha256sum", args.helper], timeout=15.0),
        capture_native(args, store, "helper-usage", ["run", args.helper], timeout=15.0, allow_error=True),
    ]


def run_live_steps(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> None:
    steps.append(capture_native(args, store, "gpiochip-devnode-open-proof", helper_command(args), timeout=args.timeout))
    steps.append(capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0))
    steps.append(capture_native(args, store, "post-netservice-status", ["netservice", "status"], timeout=10.0))


def analyze(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    helper_sha_text = step_text(store, steps, "helper-sha")
    helper_usage_text = step_text(store, steps, "helper-usage")
    live_text = step_text(store, steps, "gpiochip-devnode-open-proof")
    selftest_text = step_text(store, steps, "selftest")
    post_selftest_text = step_text(store, steps, "post-selftest")
    values = parse_prefixed(live_text)
    zero_markers = {
        "gpio_line_request_executed": values.get("gpio_line_request_executed") == "0",
        "pmic_write_executed": values.get("pmic_write_executed") == "0",
        "esoc_ioctl_executed": values.get("esoc_ioctl_executed") == "0",
        "pm_actor_executed": values.get("pm_actor_executed") == "0",
        "cnss_daemon_start_executed": values.get("cnss_daemon_start_executed") == "0",
        "wifi_hal_start_executed": values.get("wifi_hal_start_executed") == "0",
        "scan_connect_linkup": values.get("scan_connect_linkup") == "0",
        "credentials": values.get("credentials") == "0",
        "dhcp_routing": values.get("dhcp_routing") == "0",
        "external_ping": values.get("external_ping") == "0",
    }
    return {
        "helper_sha_ok": args.helper_sha256 in helper_sha_text,
        "helper_marker_ok": args.helper_marker in helper_usage_text,
        "helper_mode_ok": MODE in helper_usage_text and ALLOW_FLAG in helper_usage_text,
        "selftest_fail0": "fail=0" in selftest_text,
        "post_selftest_fail0": "fail=0" in post_selftest_text,
        "live_output_present": bool(values),
        "preflight_values": values,
        "sysfs_dev_match": values.get("expected_dev_match") == "1",
        "sysfs_label_match": values.get("expected_label_match") == "1",
        "sysfs_base_match": values.get("expected_base_match") == "1",
        "sysfs_ngpio_match": values.get("expected_ngpio_match") == "1",
        "mknod_attempted": values.get("mknod_attempted") == "1",
        "mknod_ok": values.get("mknod_ok") == "1",
        "open_attempted": values.get("open_attempted") == "1",
        "open_ok": values.get("open_ok") == "1",
        "chipinfo_executed": values.get("gpio_get_chipinfo_executed") == "1",
        "chipinfo_ok": values.get("gpio_get_chipinfo_ok") == "1",
        "cleanup_attempted": values.get("cleanup_attempted") == "1",
        "cleanup_ok": values.get("cleanup_ok") == "1",
        "ready": values.get("devnode_open_preflight_ready") == "1",
        "result": values.get("result", ""),
        "chip_name": values.get("chip_name", ""),
        "chip_label": values.get("chip_label", ""),
        "chip_lines": values.get("chip_lines", ""),
        "temp_node_path": values.get("temp_node_path", ""),
        "zero_markers": zero_markers,
        "all_zero_markers_ok": all(zero_markers.values()),
    }


def build_checks(command: str, args: argparse.Namespace, analysis: dict[str, Any], steps: list[dict[str, Any]]) -> list[Check]:
    step_ok = {str(step.get("name")): bool(step.get("ok")) for step in steps}
    checks = [
        Check("approval-gate", "pass" if command != "run" or approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} assume_yes={args.assume_yes}", "provide exact approval phrase before live run"),
        Check("native-clean", "pass" if step_ok.get("selftest") and analysis["selftest_fail0"] else "blocked", "blocker", "selftest fail0 before run", "fix native health first"),
        Check("helper-v262", "pass" if analysis["helper_sha_ok"] and analysis["helper_marker_ok"] and analysis["helper_mode_ok"] else "blocked", "blocker", f"sha={analysis['helper_sha_ok']} marker={analysis['helper_marker_ok']} mode={analysis['helper_mode_ok']}", "deploy V1258 helper v262 first"),
    ]
    if command == "run":
        checks.extend([
            Check("live-command", "pass" if step_ok.get("gpiochip-devnode-open-proof") and analysis["live_output_present"] else "blocked", "blocker", "helper produced prefixed live output", "inspect helper command output"),
            Check("sysfs-contract", "pass" if analysis["sysfs_dev_match"] and analysis["sysfs_label_match"] and analysis["sysfs_base_match"] and analysis["sysfs_ngpio_match"] else "blocked", "blocker", f"dev={analysis['sysfs_dev_match']} label={analysis['sysfs_label_match']} base={analysis['sysfs_base_match']} ngpio={analysis['sysfs_ngpio_match']}", "refresh gpiochip mapping before any mknod/open retry"),
            Check("devnode-open-proof", "pass" if analysis["ready"] else "blocked", "blocker", f"mknod={analysis['mknod_ok']} open={analysis['open_ok']} chipinfo={analysis['chipinfo_ok']} cleanup={analysis['cleanup_ok']} result={analysis['result']}", "do not proceed to GPIO line request until devnode-open proof is ready"),
            Check("zero-action-markers", "pass" if analysis["all_zero_markers_ok"] else "blocked", "blocker", json.dumps(analysis["zero_markers"], sort_keys=True), "stop if any forbidden action marker is nonzero or missing"),
            Check("post-selftest", "pass" if analysis["post_selftest_fail0"] else "blocked", "blocker", f"fail0={analysis['post_selftest_fail0']}", "recheck device health"),
        ])
    return checks


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.status not in {"pass", "warn"}]
    if command == "plan":
        return ("v1259-gpiochip-devnode-open-plan-ready", True, "plan-only; no device command executed", "run preflight then approved V1259 live proof")
    if blockers:
        return ("v1259-gpiochip-devnode-open-blocked", False, "blocked by " + ", ".join(blockers), "fix blockers before continuing")
    if command == "preflight":
        return ("v1259-gpiochip-devnode-open-ready", True, "helper v262 and native health ready for bounded devnode-open proof", "run approved V1259 live proof")
    if analysis["ready"] and analysis["all_zero_markers_ok"]:
        return ("v1259-gpiochip-devnode-open-pass", True, "temporary gpiochip devnode opened read-only and chipinfo ioctl passed with cleanup", "next gate may plan bounded PMIC GPIO9 line request without eSoC/daemon/Wi-Fi")
    return ("v1259-gpiochip-devnode-open-incomplete", True, "live proof completed but readiness is incomplete", "inspect helper output before next gate")


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["helper_sha_ok", analysis["helper_sha_ok"]],
        ["helper_mode_ok", analysis["helper_mode_ok"]],
        ["sysfs_dev_match", analysis["sysfs_dev_match"]],
        ["sysfs_label_match", analysis["sysfs_label_match"]],
        ["sysfs_base_match", analysis["sysfs_base_match"]],
        ["sysfs_ngpio_match", analysis["sysfs_ngpio_match"]],
        ["mknod_ok", analysis["mknod_ok"]],
        ["open_ok", analysis["open_ok"]],
        ["chipinfo_ok", analysis["chipinfo_ok"]],
        ["cleanup_ok", analysis["cleanup_ok"]],
        ["ready", analysis["ready"]],
        ["chip_name", analysis["chip_name"]],
        ["chip_label", analysis["chip_label"]],
        ["chip_lines", analysis["chip_lines"]],
        ["all_zero_markers_ok", analysis["all_zero_markers_ok"]],
    ]
    check_rows = [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]
    step_rows = [[s["name"], "PASS" if s["ok"] else "FAIL", s["rc"], s["status"], s["file"]] for s in manifest["steps"]]
    return "\n".join([
        "# V1259 GPIOChip Devnode-open Live",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], check_rows),
        "",
        "## Steps",
        "",
        markdown_table(["step", "ok", "rc", "status", "file"], step_rows),
        "",
        "## Safety",
        "",
        "- temporary devnode-open proof only",
        "- no GPIO line request, PMIC write, eSoC ioctl, daemon start, Wi-Fi bring-up, credentials, DHCP/routes, or external ping",
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    store = EvidenceStore(repo_path(args.out_dir))
    steps: list[dict[str, Any]] = []
    if args.command != "plan":
        steps = common_steps(args, store)
    if args.command == "run" and approved(args):
        run_live_steps(args, store, steps)
    analysis = analyze(args, store, steps)
    checks = build_checks(args.command, args, analysis, steps)
    decision, pass_ok, reason, next_step = decide(args.command, checks, analysis)
    manifest: dict[str, Any] = {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "helper": args.helper,
        "helper_expected_sha256": args.helper_sha256,
        "mode": MODE,
        "allow_flag": ALLOW_FLAG,
        "approval_phrase_matched": args.approval_phrase == APPROVAL_PHRASE,
        "assume_yes": args.assume_yes,
        "device_mutations": args.command == "run" and approved(args),
        "devnode_created_temporarily": analysis["mknod_ok"],
        "gpio_line_request_executed": False,
        "pmic_write_executed": False,
        "esoc_ioctl_executed": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "credentials_used": False,
        "dhcp_routing_executed": False,
        "external_ping_executed": False,
        "steps": steps,
        "checks": [asdict(check) for check in checks],
        "analysis": analysis,
        "required_approval_phrase": APPROVAL_PHRASE,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    LATEST_POINTER.parent.mkdir(parents=True, exist_ok=True)
    LATEST_POINTER.write_text(str(store.run_dir) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"devnode_created_temporarily: {manifest['devnode_created_temporarily']}")
    print(f"gpio_line_request_executed: {manifest['gpio_line_request_executed']}")
    print(f"pmic_write_executed: {manifest['pmic_write_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"evidence: {repo_path(args.out_dir)}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
