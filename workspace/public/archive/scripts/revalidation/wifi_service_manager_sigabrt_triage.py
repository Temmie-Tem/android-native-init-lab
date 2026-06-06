#!/usr/bin/env python3
"""Host-only V388 servicemanager SIGABRT evidence triage.

This reads an approved service-manager start-only live manifest and determines
whether the captured SIGABRT is already actionable or whether the next helper
needs more crash context. It performs no bridge command and no device mutation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v388-servicemanager-sigabrt-triage")
DEFAULT_MANIFEST = Path("tmp/wifi/v387-approved-live-20260520-060136/manifest.json")

AOSP_REFERENCES = [
    {
        "name": "servicemanager main",
        "url": "https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-release/cmds/servicemanager/main.cpp",
        "relevant_sites": [
            "ProcessState::initWithDriver(driver)",
            "LOG_ALWAYS_FATAL_IF(binder_fd < 0, \"Failed to setupPolling: %d\", binder_fd)",
            "LOG_ALWAYS_FATAL_IF(ret != 1, \"Failed to add binder FD to Looper\")",
            "timerfd_create/timerfd_settime/addFd fatal checks",
        ],
    },
    {
        "name": "libbinder ProcessState",
        "url": "https://android.googlesource.com/platform/frameworks/native/+/refs/heads/android11-release/libs/binder/ProcessState.cpp",
        "relevant_sites": [
            "open_driver(driver): open/ioctl(BINDER_VERSION)/ioctl(BINDER_SET_MAX_THREADS)",
            "mmap binder transaction memory",
            "LOG_ALWAYS_FATAL_IF(mDriverFD < 0, \"Binder driver '%s' could not be opened.  Terminating.\")",
        ],
    },
]


@dataclass
class EvidenceFinding:
    name: str
    status: str
    detail: str
    evidence: list[str]
    implication: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("analyze")
    subparsers.add_parser("regression")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def read_observation_text(manifest: dict[str, Any], target: str) -> tuple[str, str]:
    manifest_path = Path(str(manifest.get("path") or ""))
    observations = manifest.get("observations")
    if not isinstance(observations, list):
        return "", ""
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        if observation.get("target_profile") != target:
            continue
        file_value = str(observation.get("file") or "")
        if not file_value or not manifest_path:
            return "", file_value
        evidence_path = manifest_path.parent / file_value
        if not evidence_path.exists():
            return "", file_value
        return evidence_path.read_text(encoding="utf-8", errors="replace"), file_value
    return "", ""


def key_value(text: str, key: str) -> str:
    prefix = key + "="
    for raw_line in text.splitlines():
        if raw_line.startswith(prefix):
            return raw_line[len(prefix):].strip()
    return ""


def contains_line(text: str, fragment: str) -> bool:
    return any(fragment in line for line in text.splitlines())


def matching_lines(text: str, fragments: tuple[str, ...], limit: int = 12) -> list[str]:
    rows: list[str] = []
    for line in text.splitlines():
        if any(fragment in line for fragment in fragments):
            rows.append(line.strip())
        if len(rows) >= limit:
            break
    return rows


def status_for(condition: bool, pass_name: str = "present", fail_name: str = "missing") -> str:
    return pass_name if condition else fail_name


def build_findings(manifest: dict[str, Any], text: str, evidence_file: str) -> list[EvidenceFinding]:
    findings: list[EvidenceFinding] = []
    observations = manifest.get("observations") if isinstance(manifest.get("observations"), list) else []
    service_obs = next(
        (item for item in observations if isinstance(item, dict) and item.get("target_profile") == "system-servicemanager"),
        {},
    )
    postflight_safe = bool(service_obs.get("postflight_safe"))
    helper_result = str(service_obs.get("helper_result") or "")

    crash_sig = key_value(text, "capture.crash.siginfo.signo")
    service_signal = key_value(text, "service_manager_start.signal")
    stderr_has_sigabrt = "Fatal signal 6" in text or "SIGABRT" in text
    findings.append(EvidenceFinding(
        "sigabrt-captured",
        status_for(crash_sig == "6" or service_signal == "6" or stderr_has_sigabrt, "pass", "blocked"),
        f"helper_result={helper_result} service_signal={service_signal or 'missing'} siginfo_signo={crash_sig or 'missing'}",
        matching_lines(text, (
            "capture.crash.siginfo.signo=",
            "service_manager_start.signal=",
            "Fatal signal 6",
            "SIGABRT",
        )),
        "confirms the remaining blocker is a userspace abort, not the V386 cleanup failure",
    ))
    findings.append(EvidenceFinding(
        "postflight-safe",
        status_for(postflight_safe, "pass", "blocked"),
        f"postflight_safe={postflight_safe}",
        matching_lines(text, (
            "service_manager_start.reaped=",
            "service_manager_start.residual_cleared=",
            "service_manager_start.postflight_safe=",
        )),
        "allows continued bounded analysis without reboot recovery work",
    ))

    binder_context = matching_lines(text, (
        "context.dev_binder.",
        "context.dev_hwbinder.",
        "context.dev_vndbinder.",
    ), limit=24)
    binder_node_present = key_value(text, "context.dev_binder.exists") == "1"
    binder_open_message = "Binder driver" in text or "could not be opened" in text
    findings.append(EvidenceFinding(
        "binder-node-materialized",
        status_for(binder_node_present, "pass", "blocked"),
        f"context.dev_binder.exists={key_value(text, 'context.dev_binder.exists') or 'missing'} open_failure_message={binder_open_message}",
        binder_context,
        "proves the private namespace has a /dev/binder node, but does not prove open/ioctl/mmap success",
    ))

    property_present = key_value(text, "context.dev_properties.exists") == "1"
    findings.append(EvidenceFinding(
        "property-root-materialized",
        status_for(property_present, "pass", "blocked"),
        f"context.dev_properties.exists={key_value(text, 'context.dev_properties.exists') or 'missing'}",
        matching_lines(text, ("context.dev_properties.", "property_root="), limit=12),
        "reduces likelihood of a simple missing property directory blocker",
    ))

    selinux_null_present = key_value(text, "context.selinux_null.exists") == "1"
    findings.append(EvidenceFinding(
        "selinux-null-materialized",
        status_for(selinux_null_present, "pass", "blocked"),
        f"context.selinux_null.exists={key_value(text, 'context.selinux_null.exists') or 'missing'}",
        matching_lines(text, ("context.selinux_null.", "null_device_mode="), limit=12),
        "reduces likelihood of the earlier bionic /sys/fs/selinux/null early-abort class",
    ))

    abort_message_present = any(
        fragment in text
        for fragment in (
            "Abort message:",
            "Binder driver '/dev/binder' could not be opened",
            "Failed to setupPolling",
            "Failed to add binder FD to Looper",
            "Failed to timerfd_create",
            "Failed to timerfd_settime",
        )
    )
    findings.append(EvidenceFinding(
        "abort-message",
        status_for(abort_message_present, "present", "missing"),
        "current stderr has only the generic libc fatal signal line" if not abort_message_present else "abort message fragment found",
        matching_lines(text, (
            "Abort message:",
            "Binder driver",
            "Failed to setupPolling",
            "Failed to add binder FD",
            "Failed to timerfd",
            "A90_EXECNS_STDERR_BEGIN",
            "libc: Fatal signal",
        ), limit=10),
        "without the abort message, AOSP fatal-site selection remains unproven",
    ))

    register_values_present = contains_line(text, "capture.crash.regset.nt_prstatus.x0=")
    findings.append(EvidenceFinding(
        "register-values",
        status_for(register_values_present, "present", "missing"),
        f"regset_bytes={key_value(text, 'capture.crash.regset.nt_prstatus.bytes') or 'missing'}",
        matching_lines(text, ("capture.crash.regset.nt_prstatus",), limit=8),
        "current compact capture proves register block size only; it cannot map PC/LR to a fatal site",
    ))

    stack_capture_present = "capture.crash.stack" in text or "capture.crash.abort_message" in text
    findings.append(EvidenceFinding(
        "stack-or-abort-memory",
        status_for(stack_capture_present, "present", "missing"),
        f"evidence_file={evidence_file}",
        matching_lines(text, ("capture.crash.stack", "capture.crash.abort_message", "capture.crash.maps."), limit=10),
        "next helper should capture bounded stack/abort-message memory while ptrace-stopped",
    ))
    return findings


def decide(manifest: dict[str, Any], text: str, findings: list[EvidenceFinding]) -> tuple[str, bool, str, str, list[str]]:
    if not manifest.get("present"):
        return (
            "servicemanager-sigabrt-triage-awaiting-manifest",
            False,
            "input manifest is missing",
            "run approved service-manager start-only smoke first",
            ["approved-live-manifest"],
        )
    if not text:
        return (
            "servicemanager-sigabrt-triage-missing-evidence",
            False,
            "system-servicemanager evidence file is missing",
            "inspect live evidence layout",
            ["servicemanager-run-evidence"],
        )
    by_name = {finding.name: finding for finding in findings}
    if by_name["sigabrt-captured"].status != "pass":
        return (
            "servicemanager-sigabrt-triage-not-applicable",
            True,
            "servicemanager SIGABRT was not captured in this evidence",
            "route result through the runtime-gap classifier",
            [],
        )
    if by_name["postflight-safe"].status != "pass":
        return (
            "servicemanager-sigabrt-triage-unsafe-postflight",
            False,
            "servicemanager cleanup is not proven safe",
            "repair lifecycle cleanup before runtime triage",
            ["postflight-safe"],
        )
    if by_name["abort-message"].status == "present" and by_name["register-values"].status == "present":
        return (
            "servicemanager-sigabrt-triage-actionable",
            True,
            "abort message and register values are present",
            "map the fatal site and implement the targeted runtime repair",
            ["fatal-site-mapping"],
        )
    if by_name["abort-message"].status == "missing" and by_name["register-values"].status == "missing":
        return (
            "servicemanager-sigabrt-triage-needs-enhanced-crash-capture",
            True,
            "SIGABRT is captured but abort message and register values are missing",
            "add a bounded ptrace crash capture that records abort message/stack bytes and selected register values",
            ["abort-message-capture", "register-value-capture"],
        )
    return (
        "servicemanager-sigabrt-triage-partial-evidence",
        True,
        "SIGABRT triage has partial fatal-site evidence",
        "fill the missing crash context before runtime repair",
        [
            finding.name
            for finding in (by_name["abort-message"], by_name["register-values"], by_name["stack-or-abort-memory"])
            if finding.status == "missing"
        ],
    )


def render_summary(manifest: dict[str, Any]) -> str:
    finding_rows = [
        [finding["name"], finding["status"], finding["detail"], finding["implication"]]
        for finding in manifest["findings"]
    ]
    reference_rows = [
        [ref["name"], ref["url"], "; ".join(ref["relevant_sites"])]
        for ref in manifest["aosp_references"]
    ]
    return "\n".join([
        "# V388 Servicemanager SIGABRT Triage",
        "",
        f"- generated: `{manifest['generated_at']}`",
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
        markdown_table(["name", "status", "detail", "implication"], finding_rows),
        "",
        "## AOSP References",
        "",
        markdown_table(["name", "url", "relevant sites"], reference_rows),
        "",
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    live = load_json(args.manifest)
    text, evidence_file = read_observation_text(live, "system-servicemanager")
    findings = build_findings(live, text, evidence_file) if live.get("present") else []
    decision, pass_ok, reason, next_step, blockers = decide(live, text, findings)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "remaining_blockers": blockers,
        "host": collect_host_metadata(),
        "input_manifest": str(repo_path(args.manifest)),
        "input_manifest_present": bool(live.get("present")),
        "source_live_decision": live.get("decision"),
        "servicemanager_evidence_file": evidence_file,
        "findings": [asdict(finding) for finding in findings],
        "aosp_references": AOSP_REFERENCES,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
        "explicitly_not_approved": [
            "service-manager, hwservicemanager, vndservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def regression_manifest(args: argparse.Namespace) -> dict[str, Any]:
    sample = {
        "present": True,
        "path": "sample/manifest.json",
        "decision": "service-manager-start-only-live-runtime-gap",
        "observations": [
            {
                "target_profile": "system-servicemanager",
                "helper_result": "start-only-runtime-gap",
                "helper_reason": "child-exited-before-observe-window",
                "file": "svc.txt",
                "postflight_safe": True,
            },
        ],
    }
    sample_text = "\n".join([
        "context.dev_binder.exists=1",
        "context.dev_properties.exists=1",
        "context.selinux_null.exists=1",
        "capture.crash.siginfo.signo=6",
        "capture.crash.regset.nt_prstatus.bytes=272",
        "service_manager_start.signal=6",
        "service_manager_start.reaped=1",
        "service_manager_start.residual_cleared=1",
        "service_manager_start.postflight_safe=1",
        "libc: Fatal signal 6 (SIGABRT), code -1 (SI_QUEUE)",
    ])
    findings = build_findings(sample, sample_text, "svc.txt")
    decision, pass_ok, reason, next_step, blockers = decide(sample, sample_text, findings)
    regression_pass = (
        decision == "servicemanager-sigabrt-triage-needs-enhanced-crash-capture"
        and pass_ok
        and "abort-message-capture" in blockers
        and "register-value-capture" in blockers
    )
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "servicemanager-sigabrt-triage-regression-pass" if regression_pass else "servicemanager-sigabrt-triage-regression-fail",
        "pass": regression_pass,
        "reason": f"sample decision={decision} pass={pass_ok} reason={reason}",
        "next_step": "run analyze on approved live evidence",
        "remaining_blockers": [] if regression_pass else ["regression"],
        "host": collect_host_metadata(),
        "sample_decision": decision,
        "sample_next_step": next_step,
        "sample_blockers": blockers,
        "findings": [asdict(finding) for finding in findings],
        "aosp_references": AOSP_REFERENCES,
        "device_commands_executed": False,
        "device_mutations": False,
        "daemon_start_executed": False,
        "wifi_bringup_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = regression_manifest(args) if args.command == "regression" else build_manifest(args)
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
