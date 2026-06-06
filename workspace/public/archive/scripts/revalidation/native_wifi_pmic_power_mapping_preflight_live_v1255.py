#!/usr/bin/env python3
"""V1255 temporary-debugfs PMIC GPIO mapping read-only preflight.

This runs the deployed helper v261 mapping preflight with debugfs mounted only
when absent.  The live scope is read-only observation plus temporary debugfs
mount/umount cleanup.
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
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v1255-pmic-power-mapping-preflight-live")
LATEST_POINTER = Path("tmp/wifi/latest-v1255-pmic-power-mapping-preflight-live.txt")
DEFAULT_HELPER = "/cache/bin/a90_android_execns_probe"
DEFAULT_TOYBOX = "/cache/bin/toybox"
DEFAULT_BUSYBOX = "/cache/bin/busybox"
DEFAULT_HELPER_SHA256 = "37947e378f4743a6661a03ee36dfc95ddf5ce9cd79acec0862a28a4564573a7c"
DEFAULT_HELPER_MARKER = "a90_android_execns_probe v261"
DEBUGFS_ROOT = "/sys/kernel/debug"
MODE = "wifi-companion-pmic-power-surface-write-gate-preflight"
APPROVAL_PHRASE = (
    "approve v1255 temporary debugfs read-only PMIC GPIO mapping preflight only; "
    "no PMIC write, no eSoC ioctl, no daemon start and no Wi-Fi bring-up"
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
    parser.add_argument("--busybox", default=DEFAULT_BUSYBOX)
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


def parse_prefixed(text: str, prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith(prefix) or "=" not in line:
            continue
        key, value = line[len(prefix):].split("=", 1)
        values[key] = value
    return values


def debugfs_mounted(text: str) -> bool:
    return re.search(rf"\s{re.escape(DEBUGFS_ROOT)}\s+debugfs\s", text) is not None


def proc_mounts_command(args: argparse.Namespace) -> list[str]:
    return ["run", args.toybox, "cat", "/proc/mounts"]


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
        "--allow-pmic-power-write-gate-preflight",
    ]


def preflight_steps(args: argparse.Namespace, store: EvidenceStore) -> list[dict[str, Any]]:
    return [
        capture_native(args, store, "hide", ["hide"], timeout=10.0),
        capture_native(args, store, "version", ["version"], timeout=10.0),
        capture_native(args, store, "selftest", ["selftest", "verbose"], timeout=15.0),
        capture_native(args, store, "netservice-status", ["netservice", "status"], timeout=10.0),
        capture_native(args, store, "helper-sha", ["run", args.toybox, "sha256sum", args.helper], timeout=15.0),
        capture_native(args, store, "helper-usage", ["run", args.helper], timeout=15.0),
        capture_native(args, store, "debugfs-mounts-before", proc_mounts_command(args), timeout=15.0),
    ]


def run_debugfs_steps(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]]) -> dict[str, Any]:
    mounted_before = debugfs_mounted(step_text(store, steps, "debugfs-mounts-before"))
    mounted_by_v1255 = False
    if not mounted_before:
        mount_step = capture_native(
            args,
            store,
            "debugfs-mount",
            ["run", args.busybox, "mount", "-t", "debugfs", "debugfs", DEBUGFS_ROOT],
            timeout=20.0,
        )
        steps.append(mount_step)
        mounted_by_v1255 = bool(mount_step.get("raw_ok"))
    steps.append(capture_native(args, store, "debugfs-mounts-during", proc_mounts_command(args), timeout=15.0))
    steps.append(capture_native(args, store, "pmic-power-mapping-preflight", helper_command(args), timeout=args.timeout))
    if mounted_by_v1255:
        steps.append(
            capture_native(
                args,
                store,
                "debugfs-umount",
                ["run", args.busybox, "umount", DEBUGFS_ROOT],
                timeout=20.0,
                allow_error=True,
            )
        )
    steps.append(capture_native(args, store, "debugfs-mounts-after", proc_mounts_command(args), timeout=15.0))
    steps.append(capture_native(args, store, "post-selftest", ["selftest", "verbose"], timeout=15.0))
    steps.append(capture_native(args, store, "post-netservice-status", ["netservice", "status"], timeout=10.0))
    return {"mounted_before": mounted_before, "mounted_by_v1255": mounted_by_v1255}


def analyze(args: argparse.Namespace, store: EvidenceStore, steps: list[dict[str, Any]], mount_info: dict[str, Any]) -> dict[str, Any]:
    helper_sha_text = step_text(store, steps, "helper-sha")
    helper_usage_text = step_text(store, steps, "helper-usage")
    live_text = step_text(store, steps, "pmic-power-mapping-preflight")
    mounts_during = step_text(store, steps, "debugfs-mounts-during")
    mounts_after = step_text(store, steps, "debugfs-mounts-after")
    post_selftest_text = step_text(store, steps, "post-selftest")
    values = parse_prefixed(live_text, "pmic_power_write_gate_preflight.")
    zero_markers = {
        "mutation_attempted": values.get("mutation_attempted") == "0",
        "write_gate_implemented": values.get("write_gate_implemented") == "0",
        "gpio_line_request_executed": values.get("gpio_line_request_executed") == "0",
        "esoc_ioctl_executed": values.get("esoc_ioctl_executed") == "0",
        "pm_actor_executed": values.get("pm_actor_executed") == "0",
        "cnss_daemon_start_executed": values.get("cnss_daemon_start_executed") == "0",
        "wifi_hal_start_executed": values.get("wifi_hal_start_executed") == "0",
        "scan_connect_linkup": values.get("scan_connect_linkup") == "0",
        "credentials": values.get("credentials") == "0",
        "dhcp_routing": values.get("dhcp_routing") == "0",
        "external_ping": values.get("external_ping") == "0",
    }
    mounted_before = bool(mount_info.get("mounted_before"))
    mounted_after = debugfs_mounted(mounts_after)
    return {
        "helper_sha_ok": args.helper_sha256 in helper_sha_text,
        "helper_marker_ok": args.helper_marker in helper_usage_text,
        "helper_mode_ok": MODE in helper_usage_text,
        "mounted_before": mounted_before,
        "mounted_by_v1255": bool(mount_info.get("mounted_by_v1255")),
        "mounted_during": debugfs_mounted(mounts_during),
        "mounted_after": mounted_after,
        "cleanup_ok": mounted_before or not mounted_after,
        "live_output_present": bool(values),
        "preflight_values": values,
        "zero_markers": zero_markers,
        "all_zero_markers_ok": all(zero_markers.values()),
        "debugfs_pinctrl_present": values.get("debugfs_pinctrl_present") == "1",
        "debugfs_regulator_present": values.get("debugfs_regulator_present") == "1",
        "pmic_soft_reset_seen": values.get("pmic_soft_reset_seen") == "1",
        "pcie1_gdsc_seen": values.get("pcie1_gdsc_seen") == "1",
        "pcie0_gdsc_seen": values.get("pcie0_gdsc_seen") == "1",
        "read_contract_ready": values.get("read_contract_ready") == "1",
        "native_reproduction_candidate": values.get("native_reproduction_candidate") == "1",
        "gpiochip_candidate_seen": values.get("gpiochip_candidate_seen") == "1",
        "gpiochip_candidate_path": values.get("gpiochip_candidate_path", ""),
        "gpiochip_candidate_name": values.get("gpiochip_candidate_name", ""),
        "gpiochip_candidate_label": values.get("gpiochip_candidate_label", ""),
        "gpiochip_candidate_lines": values.get("gpiochip_candidate_lines", ""),
        "gpiochip_debugfs_line_seen": values.get("gpiochip_debugfs_line_seen") == "1",
        "gpiochip_debugfs_line": values.get("gpiochip_debugfs_line", ""),
        "gpiochip_global_base": values.get("gpiochip_global_base", ""),
        "gpiochip_global_end": values.get("gpiochip_global_end", ""),
        "gpiochip_expected_offset": values.get("gpiochip_expected_offset", ""),
        "gpiochip_identity_match": values.get("gpiochip_identity_match") == "1",
        "gpiochip_offset_match": values.get("gpiochip_offset_match") == "1",
        "gpiochip_mapping_ready": values.get("gpiochip_mapping_ready") == "1",
        "mapping_preflight_ready": values.get("mapping_preflight_ready") == "1",
        "mdm3_state": values.get("mdm3_state", ""),
        "mdm_status_count_total": values.get("mdm_status_count_total", ""),
        "result": values.get("result", ""),
        "post_selftest_fail0": "fail=0" in post_selftest_text,
    }


def build_checks(args: argparse.Namespace, command: str, analysis: dict[str, Any], steps: list[dict[str, Any]]) -> list[Check]:
    step_ok = {str(step.get("name")): bool(step.get("ok")) for step in steps}
    checks = [
        Check("approval-gate", "pass" if command != "run" or approved(args) else "needs-operator", "approval", f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} assume_yes={args.assume_yes}", "provide exact approval phrase before live run"),
        Check("remote-helper-v261", "pass" if analysis["helper_sha_ok"] and analysis["helper_marker_ok"] and analysis["helper_mode_ok"] else "blocked", "blocker", f"sha={analysis['helper_sha_ok']} marker={analysis['helper_marker_ok']} mode={analysis['helper_mode_ok']}", "deploy V1254 helper v261 first"),
        Check("native-clean", "pass" if step_ok.get("selftest") else "blocked", "blocker", "selftest command completed", "fix native health before live preflight"),
    ]
    if command == "run":
        checks.extend([
            Check("debugfs-mounted", "pass" if analysis["mounted_during"] else "blocked", "blocker", f"before={analysis['mounted_before']} by_v1255={analysis['mounted_by_v1255']} during={analysis['mounted_during']}", "inspect debugfs mount command"),
            Check("live-command", "pass" if step_ok.get("pmic-power-mapping-preflight") and analysis["live_output_present"] else "blocked", "blocker", f"result={analysis['result']} output_present={analysis['live_output_present']}", "inspect helper output"),
            Check("zero-action-markers", "pass" if analysis["all_zero_markers_ok"] else "blocked", "blocker", json.dumps(analysis["zero_markers"], sort_keys=True), "stop and inspect before any further live action"),
            Check("debugfs-cleanup", "pass" if analysis["cleanup_ok"] else "blocked", "blocker", f"before={analysis['mounted_before']} after={analysis['mounted_after']}", "unmount debugfs if V1255 mounted it"),
            Check("post-selftest", "pass" if analysis["post_selftest_fail0"] else "blocked", "blocker", f"fail0={analysis['post_selftest_fail0']}", "recheck device health"),
        ])
    return checks


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    blockers = [check.name for check in checks if check.status not in {"pass", "warn"}]
    if command == "plan":
        return (
            "v1255-pmic-power-mapping-preflight-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V1255 preflight then approved temporary-debugfs read-only mapping gate",
        )
    if blockers:
        return (
            "v1255-pmic-power-mapping-preflight-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "fix blockers before continuing",
        )
    if command == "preflight":
        return (
            "v1255-pmic-power-mapping-preflight-ready",
            True,
            "remote helper v261 and native health are ready for temporary-debugfs read-surface preflight",
            "run approved V1255 temporary-debugfs mapping gate",
        )
    if analysis["mapping_preflight_ready"]:
        return (
            "v1255-pmic-gpio-mapping-ready",
            True,
            "debugfs read surface confirms PMIC gpiochip mapping is ready and no forbidden action executed",
            "design the isolated bounded line-hold proof only after a separate source/plan cycle",
        )
    if analysis["native_reproduction_candidate"]:
        return (
            "v1255-pmic-gpio-mapping-incomplete",
            True,
            "debugfs read surface completed, but helper did not classify PMIC gpiochip mapping as ready",
            "inspect gpiochip mapping fields before deciding the next gate",
        )
    return (
        "v1255-pmic-gpio-read-surface-incomplete",
        True,
        "temporary debugfs gate executed safely but PMIC GPIO mapping read contract remains incomplete",
        "inspect helper fields and debugfs mount surface before any line-hold proof design",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    rows = [
        ["decision", manifest["decision"]],
        ["pass", manifest["pass"]],
        ["mounted_before", analysis["mounted_before"]],
        ["mounted_by_v1255", analysis["mounted_by_v1255"]],
        ["mounted_during", analysis["mounted_during"]],
        ["mounted_after", analysis["mounted_after"]],
        ["cleanup_ok", analysis["cleanup_ok"]],
        ["debugfs_pinctrl_present", analysis["debugfs_pinctrl_present"]],
        ["debugfs_regulator_present", analysis["debugfs_regulator_present"]],
        ["pmic_soft_reset_seen", analysis["pmic_soft_reset_seen"]],
        ["pcie1_gdsc_seen", analysis["pcie1_gdsc_seen"]],
        ["pcie0_gdsc_seen", analysis["pcie0_gdsc_seen"]],
        ["read_contract_ready", analysis["read_contract_ready"]],
        ["native_reproduction_candidate", analysis["native_reproduction_candidate"]],
        ["gpiochip_candidate_seen", analysis["gpiochip_candidate_seen"]],
        ["gpiochip_candidate_path", analysis["gpiochip_candidate_path"]],
        ["gpiochip_candidate_name", analysis["gpiochip_candidate_name"]],
        ["gpiochip_candidate_label", analysis["gpiochip_candidate_label"]],
        ["gpiochip_candidate_lines", analysis["gpiochip_candidate_lines"]],
        ["gpiochip_debugfs_line_seen", analysis["gpiochip_debugfs_line_seen"]],
        ["gpiochip_debugfs_line", analysis["gpiochip_debugfs_line"]],
        ["gpiochip_global_base", analysis["gpiochip_global_base"]],
        ["gpiochip_global_end", analysis["gpiochip_global_end"]],
        ["gpiochip_expected_offset", analysis["gpiochip_expected_offset"]],
        ["gpiochip_identity_match", analysis["gpiochip_identity_match"]],
        ["gpiochip_offset_match", analysis["gpiochip_offset_match"]],
        ["gpiochip_mapping_ready", analysis["gpiochip_mapping_ready"]],
        ["mapping_preflight_ready", analysis["mapping_preflight_ready"]],
        ["mdm3_state", analysis["mdm3_state"]],
        ["mdm_status_count_total", analysis["mdm_status_count_total"]],
        ["live_result", analysis["result"]],
    ]
    return "\n".join([
        "# V1255 PMIC GPIO Mapping Preflight Live",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Summary",
        "",
        markdown_table(["field", "value"], rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[c["name"], c["status"], c["severity"], c["detail"], c["next_step"]] for c in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- temporary debugfs mount is the only live environment change, and it is cleaned up when V1255 mounted it",
        "- no PMIC/GPIO/debugfs/regulator write, eSoC ioctl, PM actor, CNSS actor, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, reboot, flash, boot image write, or partition write",
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("native")
    steps: list[dict[str, Any]] = []
    mount_info: dict[str, Any] = {}
    if args.command != "plan":
        steps.extend(preflight_steps(args, store))
        if args.command == "run" and approved(args):
            mount_info = run_debugfs_steps(args, store, steps)
    analysis = analyze(args, store, steps, mount_info)
    checks = build_checks(args, args.command, analysis, steps)
    decision, passed, reason, next_step = decide(args.command, checks, analysis)
    manifest = {
        "cycle": "v1255",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "out_dir": str(store.run_dir),
        "approval_phrase": args.approval_phrase if args.command == "run" else "",
        "host": collect_host_metadata(),
        "steps": steps,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": args.command != "plan",
        "temporary_debugfs_mount_executed": bool(mount_info.get("mounted_by_v1255")),
        "debugfs_mounted_before": bool(mount_info.get("mounted_before")),
        "debugfs_mounted_after": bool(analysis.get("mounted_after")),
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
