#!/usr/bin/env python3
"""V1250 read-only PMIC soft-reset preflight live gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, run_capture, strip_cmdv1_text
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1250-pmic-soft-reset-preflight-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1250-pmic-soft-reset-preflight-live.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_HELPER_SHA256 = "0313d613d95c56af5681871062b7fceb47ede3c3ef8fcff534d0eea3338eaa2f"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v260"
MODE = "wifi-companion-pmic-soft-reset-preflight"
APPROVAL_PHRASE = (
    "approve v1250 read-only PMIC soft-reset preflight only; "
    "no PMIC write, no eSoC ioctl, no daemon start and no Wi-Fi bring-up"
)


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
    parser.add_argument("--timeout", type=float, default=30.0)
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


def safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "._+-" else "-" for ch in value).strip("-") or "capture"


def capture_native(args: argparse.Namespace,
                   store: EvidenceStore,
                   name: str,
                   command: list[str],
                   *,
                   timeout: float | None = None) -> dict[str, Any]:
    capture = run_capture(args, name, command, timeout=timeout)
    text = capture.text if capture.text else capture.error + "\n"
    stripped = strip_cmdv1_text(text) if capture.text else text
    rel = f"native/{safe_name(name)}.txt"
    store.write_text(rel, stripped)
    data = asdict(capture)
    if len(data["text"]) > 4096:
        data["text_sha256_like"] = "omitted-large-text"
        data["text"] = data["text"][:4096] + "\n[truncated in manifest]\n"
    data["file"] = rel
    return data


def read_step_text(store: EvidenceStore, step: dict[str, Any]) -> str:
    rel = str(step.get("file") or "")
    if not rel:
        return ""
    path = store.run_dir / rel
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def parse_prefixed(text: str, prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(prefix) or "=" not in line:
            continue
        key, value = line[len(prefix):].split("=", 1)
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
        "--allow-pmic-soft-reset-preflight",
    ]


def preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    return [
        capture_native(args, store, "hide", ["hide"], timeout=10.0),
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "netservice-status", ["netservice", "status"], timeout=10.0),
        capture_native(args, store, "helper-sha", ["run", args.toybox, "sha256sum", args.helper], timeout=15.0),
        capture_native(args, store, "helper-usage", ["run", args.helper], timeout=15.0),
    ]


def postflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    return [
        capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "post-netservice-status", ["netservice", "status"], timeout=10.0),
    ]


def analyze(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    helper_sha_text = ""
    helper_usage_text = ""
    live_text = ""
    post_selftest_text = ""
    for step in steps:
        if step.get("name") == "helper-sha":
            helper_sha_text = read_step_text(store, step)
        elif step.get("name") == "helper-usage":
            helper_usage_text = read_step_text(store, step)
        elif step.get("name") == "pmic-soft-reset-preflight":
            live_text = read_step_text(store, step)
        elif step.get("name") == "post-selftest":
            post_selftest_text = read_step_text(store, step)
    values = parse_prefixed(live_text, "pmic_soft_reset_preflight.")
    zero_markers = {
        "mutation_attempted": values.get("mutation_attempted") == "0",
        "write_gate_implemented": values.get("write_gate_implemented") == "0",
        "write_blocked": values.get("write_blocked") == "1",
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
        "helper_mode_ok": MODE in helper_usage_text,
        "live_output_present": bool(values),
        "preflight_values": values,
        "zero_markers": zero_markers,
        "all_zero_markers_ok": all(zero_markers.values()),
        "read_contract_ready": values.get("read_contract_ready") == "1",
        "native_reproduction_candidate": values.get("native_reproduction_candidate") == "1",
        "result": values.get("result", ""),
        "post_selftest_fail0": "fail=0" in post_selftest_text,
    }


def build_checks(args: argparse.Namespace, command: str, analysis: dict[str, Any], steps: list[dict[str, Any]]) -> list[Check]:
    step_ok = {str(step.get("name")): bool(step.get("ok")) for step in steps}
    checks = [
        Check("approval-gate", "pass" if command != "run" or approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} assume_yes={args.assume_yes}", "provide exact approval phrase before live run"),
        Check("remote-helper-v260", "pass" if analysis["helper_sha_ok"] and analysis["helper_marker_ok"] and analysis["helper_mode_ok"] else "blocked", "blocker", f"sha={analysis['helper_sha_ok']} marker={analysis['helper_marker_ok']} mode={analysis['helper_mode_ok']}", "deploy V1249 helper v260 first"),
        Check("native-clean", "pass" if step_ok.get("selftest") else "blocked", "blocker", "selftest command completed", "fix native health before live preflight"),
    ]
    if command == "run":
        checks.extend([
            Check("live-command", "pass" if step_ok.get("pmic-soft-reset-preflight") and analysis["live_output_present"] else "blocked", "blocker", f"result={analysis['result']} output_present={analysis['live_output_present']}", "inspect helper output"),
            Check("zero-action-markers", "pass" if analysis["all_zero_markers_ok"] else "blocked", "blocker", json.dumps(analysis["zero_markers"], sort_keys=True), "stop and inspect before any further live action"),
            Check("post-selftest", "pass" if analysis["post_selftest_fail0"] else "blocked", "blocker", f"fail0={analysis['post_selftest_fail0']}", "recheck device health"),
        ])
    return checks


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.status not in {"pass", "warn"}]
    if command == "plan":
        return (
            "v1250-pmic-soft-reset-preflight-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1250 preflight then approved read-only live gate",
        )
    if blockers:
        return (
            "v1250-pmic-soft-reset-preflight-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blockers before continuing",
        )
    if command == "preflight":
        return (
            "v1250-pmic-soft-reset-preflight-ready",
            True,
            "remote helper v260 and native health are ready for read-only PMIC preflight",
            "run approved V1250 read-only live gate",
        )
    if analysis["native_reproduction_candidate"]:
        return (
            "v1250-pmic-soft-reset-native-reproduction-candidate",
            True,
            "read-only PMIC preflight confirms native MUX/GDSC state is a valid reproduction candidate and no forbidden action executed",
            "V1251 should design the bounded write gate, still source/plan first",
        )
    return (
        "v1250-pmic-soft-reset-readonly-classified-no-candidate",
        True,
        "read-only PMIC preflight executed safely but did not classify native as a reproduction candidate",
        "inspect preflight fields before designing any write gate",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V1250 PMIC Soft-reset Preflight Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- helper_marker_ok: `{analysis['helper_marker_ok']}`",
        f"- helper_sha_ok: `{analysis['helper_sha_ok']}`",
        f"- live_result: `{analysis['result']}`",
        f"- read_contract_ready: `{analysis['read_contract_ready']}`",
        f"- native_reproduction_candidate: `{analysis['native_reproduction_candidate']}`",
        f"- forbidden_actions_ok: `{analysis['all_zero_markers_ok']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- read-only live gate; PMIC/GPIO/debugfs/regulator writes remain blocked",
        "- no eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    if args.command != "plan":
        steps.extend(preflight_steps(args, store))
        if args.command == "run" and approved(args):
            steps.append(capture_native(args, store, "pmic-soft-reset-preflight", helper_command(args), timeout=args.timeout))
            steps.extend(postflight_steps(args, store))
    analysis = analyze(args, store, steps)
    checks = build_checks(args, args.command, analysis, steps)
    decision, passed, reason, next_step = decide(args.command, checks, analysis)
    manifest = {
        "cycle": "v1250",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "host": collect_host_metadata(),
        "steps": steps,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": args.command != "plan",
        "pmic_write_executed": False,
        "debugfs_write_executed": False,
        "regulator_write_executed": False,
        "gpio_write_executed": False,
        "esoc_ioctl_executed": False,
        "pm_actor_executed": False,
        "cnss_daemon_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "wifi_bringup_executed": False,
        "reboot_executed": False,
        "partition_write_executed": False,
        "flash_executed": False,
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir) + "\n")
    print(f"decision: {decision}")
    print(f"pass: {passed}")
    print(f"reason: {reason}")
    print(f"next: {next_step}")
    print(f"evidence: {store.run_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
