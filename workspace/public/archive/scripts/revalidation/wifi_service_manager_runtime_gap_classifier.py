#!/usr/bin/env python3
"""Classify V376 service-manager start-only runtime gaps.

This is host-only. It reads V376 evidence and identifies the first actionable
runtime blocker before any HAL start-only approval packet is considered.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v378-service-manager-runtime-gap-classifier")
DEFAULT_V376 = Path("tmp/wifi/v376-approved-run-20260520-022612/manifest.json")
BINDER_OPEN_RE = re.compile(r"Binder driver .*could not be opened|Binder driver could not be opened", re.IGNORECASE)


@dataclass
class TargetGap:
    target: str
    helper_result: str
    helper_reason: str
    file: str
    child_signal: str
    binder_open_failed: bool
    dev_properties_missing: bool
    data_missing: bool
    signal_abort: bool
    stderr_sigabrt: bool
    ptrace_exec_stop: bool
    ptrace_crash_stop: bool
    ptrace_siginfo_signo: str
    postflight_safe: bool
    evidence: list[str]


@dataclass
class ClassifierCaseResult:
    name: str
    status: str
    decision: str
    expected_decision: str
    pass_value: bool
    expected_pass: bool
    missing_fragments: list[str]
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v376-manifest", type=Path, default=DEFAULT_V376)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("classify")
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


def read_observation_text(manifest: dict[str, Any], observation: dict[str, Any]) -> str:
    manifest_path = Path(str(manifest.get("path") or ""))
    file_value = str(observation.get("file") or "")
    if not file_value or not manifest_path:
        return ""
    evidence_path = manifest_path.parent / file_value
    if not evidence_path.exists():
        return ""
    return evidence_path.read_text(encoding="utf-8", errors="replace")


def key_value(text: str, key: str) -> str:
    prefix = key + "="
    for raw_line in text.splitlines():
        if raw_line.startswith(prefix):
            return raw_line[len(prefix):].strip()
    return ""


def context_missing(text: str, context_key: str) -> bool:
    return key_value(text, f"{context_key}.exists") == "0"


def classify_targets(manifest: dict[str, Any]) -> list[TargetGap]:
    gaps: list[TargetGap] = []
    observations = manifest.get("observations")
    if not isinstance(observations, list):
        return gaps
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        text = read_observation_text(manifest, observation)
        evidence: list[str] = []
        for raw_line in text.splitlines():
            if (
                "Binder driver" in raw_line
                or raw_line.startswith("child_signal=")
                or raw_line.startswith("service_manager_start.signal=")
                or raw_line.startswith("service_manager_start.reason=")
                or raw_line.startswith("service_manager_start.capture_")
                or raw_line.startswith("context.dev_properties.exists=")
                or raw_line.startswith("context.data.exists=")
                or raw_line.startswith("capture.exec_stop=")
                or raw_line.startswith("capture.crash_stop=")
                or raw_line.startswith("capture.crash.siginfo.")
                or "SIGABRT" in raw_line
                or "Fatal signal 6" in raw_line
            ):
                evidence.append(raw_line.strip())
        child_signal = key_value(text, "child_signal") or key_value(text, "service_manager_start.signal")
        gaps.append(TargetGap(
            target=str(observation.get("target_profile") or "unknown"),
            helper_result=str(observation.get("helper_result") or "missing"),
            helper_reason=str(observation.get("helper_reason") or ""),
            file=str(observation.get("file") or ""),
            child_signal=child_signal,
            binder_open_failed=bool(BINDER_OPEN_RE.search(text)),
            dev_properties_missing=context_missing(text, "context.dev_properties"),
            data_missing=context_missing(text, "context.data"),
            signal_abort=child_signal == "6",
            stderr_sigabrt="SIGABRT" in text or "Fatal signal 6" in text,
            ptrace_exec_stop=key_value(text, "capture.exec_stop") == "1" or key_value(text, "service_manager_start.capture_exec") == "1",
            ptrace_crash_stop=key_value(text, "capture.crash_stop") == "1" or key_value(text, "service_manager_start.capture_crash") == "1",
            ptrace_siginfo_signo=key_value(text, "capture.crash.siginfo.signo"),
            postflight_safe=bool(observation.get("postflight_safe")),
            evidence=evidence[:12],
        ))
    return gaps


def decide(manifest: dict[str, Any], gaps: list[TargetGap]) -> tuple[str, bool, str, str, list[str]]:
    if not manifest.get("present"):
        return (
            "service-manager-runtime-gap-classifier-awaiting-v376",
            True,
            "V376 approved manifest is absent",
            "run V376 approved live before classification",
            ["v376-approved-manifest"],
        )
    decision = str(manifest.get("decision") or "")
    if decision != "service-manager-start-only-live-runtime-gap":
        return (
            "service-manager-runtime-gap-classifier-not-needed",
            True,
            f"V376 decision is not runtime-gap: {decision}",
            "route V376 result through V377",
            [],
        )
    if not gaps:
        return (
            "service-manager-runtime-gap-classifier-missing-observations",
            False,
            "V376 runtime-gap manifest has no observation details",
            "inspect V376 evidence files",
            ["missing-observations"],
        )
    unsafe = [gap.target for gap in gaps if not gap.postflight_safe]
    if unsafe:
        return (
            "service-manager-runtime-gap-classifier-unsafe-postflight",
            False,
            "postflight safety missing for: " + ", ".join(unsafe),
            "recover/inspect before any repair",
            ["postflight-safety"],
        )
    binder_failed = [gap.target for gap in gaps if gap.binder_open_failed]
    if binder_failed and len(binder_failed) == len(gaps):
        return (
            "service-manager-runtime-gap-binder-devnode-required",
            True,
            "all start-only targets aborted because Binder device open failed",
            "implement private Binder devnode provisioning inside helper namespace, then rerun V376",
            ["private-binder-devnodes"],
        )
    property_missing = [gap.target for gap in gaps if gap.dev_properties_missing]
    if property_missing:
        return (
            "service-manager-runtime-gap-property-runtime-required",
            True,
            "property runtime is missing for: " + ", ".join(property_missing),
            "plan private property area materialization before HAL work",
            ["property-runtime"],
        )
    servicemanager_captured = [
        gap for gap in gaps
        if gap.target == "system-servicemanager"
        and gap.ptrace_crash_stop
        and (gap.signal_abort or gap.ptrace_siginfo_signo == "6")
        and not gap.binder_open_failed
        and not gap.dev_properties_missing
    ]
    if servicemanager_captured:
        return (
            "service-manager-runtime-gap-servicemanager-sigabrt-captured",
            True,
            "servicemanager SIGABRT was captured by ptrace-lite crash evidence",
            "inspect captured siginfo/register/maps/status evidence before runtime repair",
            ["servicemanager-sigabrt-evidence"],
        )
    servicemanager_abort = [
        gap for gap in gaps
        if gap.target == "system-servicemanager"
        and gap.signal_abort
        and gap.stderr_sigabrt
        and not gap.binder_open_failed
        and not gap.dev_properties_missing
    ]
    hwservicemanager_pass = any(
        gap.target == "system-hwservicemanager"
        and gap.helper_result == "start-only-pass"
        and gap.postflight_safe
        for gap in gaps
    )
    if servicemanager_abort and hwservicemanager_pass:
        return (
            "service-manager-runtime-gap-servicemanager-sigabrt-capture-required",
            True,
            "servicemanager aborts with SIGABRT while hwservicemanager survives the bounded window",
            "add service-manager ptrace-lite/tombstone evidence capture before HAL work",
            ["servicemanager-sigabrt-capture"],
        )
    return (
        "service-manager-runtime-gap-manual-review",
        False,
        "runtime-gap did not match known classes",
        "inspect helper stdout/stderr manually",
        ["manual-review"],
    )


def build_manifest(args: argparse.Namespace, v376: dict[str, Any]) -> dict[str, Any]:
    gaps = classify_targets(v376)
    decision, pass_ok, reason, next_step, blockers = decide(v376, gaps)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "v376_manifest": {
            "path": v376.get("path"),
            "present": v376.get("present"),
            "decision": v376.get("decision"),
            "pass": v376.get("pass"),
            "daemon_start_executed": v376.get("daemon_start_executed"),
            "wifi_bringup_executed": v376.get("wifi_bringup_executed"),
        },
        "target_gaps": [asdict(gap) for gap in gaps],
        "remaining_blockers": blockers,
        "device_commands_executed": False,
        "device_mutations": False,
        "explicitly_not_approved": [
            "Wi-Fi HAL start",
            "CNSS/diag start",
            "wificond/supplicant/hostapd start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, driver bind/unbind, firmware mutation, Android partition write",
        ],
    }


def synthetic_manifest(decision: str, observations: list[dict[str, Any]] | None,
                       files: dict[str, str] | None = None,
                       postflight_safe: bool = True) -> dict[str, Any]:
    payload = {
        "present": True,
        "path": "synthetic/manifest.json",
        "decision": decision,
        "pass": True,
        "daemon_start_executed": bool(observations),
        "wifi_bringup_executed": False,
        "observations": observations or [],
        "_files": files or {},
        "_postflight_safe": postflight_safe,
    }
    return payload


def synthetic_gap_text(stderr: str, dev_properties_missing: bool = True, data_missing: bool = True) -> str:
    return "\n".join([
        "child_signal=6",
        "service_manager_start.signal=6",
        "service_manager_start.reason=child-exited-before-observe-window",
        f"context.dev_properties.exists={'0' if dev_properties_missing else '1'}",
        f"context.data.exists={'0' if data_missing else '1'}",
        "A90_EXECNS_STDERR_BEGIN",
        stderr,
        "A90_EXECNS_STDERR_END",
    ])


def read_observation_text_synthetic(manifest: dict[str, Any], observation: dict[str, Any]) -> str:
    files = manifest.get("_files")
    if isinstance(files, dict):
        return str(files.get(str(observation.get("file") or ""), ""))
    return read_observation_text(manifest, observation)


def classify_targets_synthetic(manifest: dict[str, Any]) -> list[TargetGap]:
    if "_files" not in manifest:
        return classify_targets(manifest)
    gaps: list[TargetGap] = []
    observations = manifest.get("observations")
    if not isinstance(observations, list):
        return gaps
    for observation in observations:
        text = read_observation_text_synthetic(manifest, observation)
        child_signal = key_value(text, "child_signal") or key_value(text, "service_manager_start.signal")
        gaps.append(TargetGap(
            target=str(observation.get("target_profile") or "unknown"),
            helper_result=str(observation.get("helper_result") or "missing"),
            helper_reason=str(observation.get("helper_reason") or ""),
            file=str(observation.get("file") or ""),
            child_signal=child_signal,
            binder_open_failed=bool(BINDER_OPEN_RE.search(text)),
            dev_properties_missing=context_missing(text, "context.dev_properties"),
            data_missing=context_missing(text, "context.data"),
            signal_abort=child_signal == "6",
            stderr_sigabrt="SIGABRT" in text or "Fatal signal 6" in text,
            ptrace_exec_stop=key_value(text, "capture.exec_stop") == "1" or key_value(text, "service_manager_start.capture_exec") == "1",
            ptrace_crash_stop=key_value(text, "capture.crash_stop") == "1" or key_value(text, "service_manager_start.capture_crash") == "1",
            ptrace_siginfo_signo=key_value(text, "capture.crash.siginfo.signo"),
            postflight_safe=bool(observation.get("postflight_safe", manifest.get("_postflight_safe", True))),
            evidence=[line for line in text.splitlines() if "Binder driver" in line or "SIGABRT" in line or line.startswith("child_signal=") or line.startswith("capture.")][:12],
        ))
    return gaps


def build_manifest_for_regression(args: argparse.Namespace, v376: dict[str, Any]) -> dict[str, Any]:
    gaps = classify_targets_synthetic(v376)
    decision, pass_ok, reason, next_step, blockers = decide(v376, gaps)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "target_gaps": [asdict(gap) for gap in gaps],
        "remaining_blockers": blockers,
        "device_commands_executed": False,
        "device_mutations": False,
    }


def synthetic_cases() -> list[tuple[str, dict[str, Any], str, bool, tuple[str, ...]]]:
    obs = [
        {"target_profile": "system-servicemanager", "helper_result": "start-only-runtime-gap", "helper_reason": "child-exited-before-observe-window", "file": "svc.txt", "postflight_safe": True},
        {"target_profile": "system-hwservicemanager", "helper_result": "start-only-runtime-gap", "helper_reason": "child-exited-before-observe-window", "file": "hwsvc.txt", "postflight_safe": True},
    ]
    files = {
        "svc.txt": synthetic_gap_text("Binder driver '/dev/binder' could not be opened.  Terminating."),
        "hwsvc.txt": synthetic_gap_text("Binder driver could not be opened. Terminating."),
    }
    prop_files = {
        "svc.txt": synthetic_gap_text("property area missing", dev_properties_missing=True),
        "hwsvc.txt": synthetic_gap_text("property area missing", dev_properties_missing=True),
    }
    sigabrt_obs = [
        {"target_profile": "system-servicemanager", "helper_result": "start-only-runtime-gap", "helper_reason": "child-exited-before-observe-window", "file": "svc.txt", "postflight_safe": True},
        {"target_profile": "system-hwservicemanager", "helper_result": "start-only-pass", "helper_reason": "observed-until-timeout-clean-stop", "file": "hwsvc.txt", "postflight_safe": True},
    ]
    sigabrt_files = {
        "svc.txt": synthetic_gap_text("libc: Fatal signal 6 (SIGABRT), code -1", dev_properties_missing=False, data_missing=False),
        "hwsvc.txt": "child_signal=15\nservice_manager_start.signal=15\nservice_manager_start.reason=observed-until-timeout-clean-stop\ncontext.dev_properties.exists=1\ncontext.data.exists=1\n",
    }
    captured_files = {
        "svc.txt": "\n".join([
            synthetic_gap_text("libc: Fatal signal 6 (SIGABRT), code -1", dev_properties_missing=False, data_missing=False),
            "capture.exec_stop=1",
            "capture.crash_stop=1",
            "capture.crash.siginfo.signo=6",
            "capture.crash.siginfo.code=-1",
            "service_manager_start.capture_exec=1",
            "service_manager_start.capture_crash=1",
        ]),
        "hwsvc.txt": sigabrt_files["hwsvc.txt"],
    }
    return [
        ("missing", {"present": False, "path": ""}, "service-manager-runtime-gap-classifier-awaiting-v376", True, ("v376-approved-manifest",)),
        ("not-needed", synthetic_manifest("service-manager-start-only-live-pass", obs, files), "service-manager-runtime-gap-classifier-not-needed", True, ()),
        ("missing-observations", synthetic_manifest("service-manager-start-only-live-runtime-gap", []), "service-manager-runtime-gap-classifier-missing-observations", False, ("missing-observations",)),
        ("binder-required", synthetic_manifest("service-manager-start-only-live-runtime-gap", obs, files), "service-manager-runtime-gap-binder-devnode-required", True, ("private-binder-devnodes",)),
        ("property-required", synthetic_manifest("service-manager-start-only-live-runtime-gap", obs, prop_files), "service-manager-runtime-gap-property-runtime-required", True, ("property-runtime",)),
        ("servicemanager-sigabrt-captured", synthetic_manifest("service-manager-start-only-live-runtime-gap", sigabrt_obs, captured_files), "service-manager-runtime-gap-servicemanager-sigabrt-captured", True, ("servicemanager-sigabrt-evidence",)),
        ("servicemanager-sigabrt", synthetic_manifest("service-manager-start-only-live-runtime-gap", sigabrt_obs, sigabrt_files), "service-manager-runtime-gap-servicemanager-sigabrt-capture-required", True, ("servicemanager-sigabrt-capture",)),
        ("unsafe", synthetic_manifest("service-manager-start-only-live-runtime-gap", [{**obs[0], "postflight_safe": False}], files), "service-manager-runtime-gap-classifier-unsafe-postflight", False, ("postflight-safety",)),
    ]


def run_regression(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    results: list[ClassifierCaseResult] = []
    for name, v376, expected_decision, expected_pass, expected_blockers in synthetic_cases():
        manifest = build_manifest_for_regression(args, v376)
        path = store.write_json(f"cases/{name}.json", manifest)
        blockers = tuple(str(item) for item in manifest.get("remaining_blockers", []))
        missing = [item for item in expected_blockers if item not in blockers]
        ok = (
            manifest.get("decision") == expected_decision
            and bool(manifest.get("pass")) is expected_pass
            and not missing
            and not bool(manifest.get("device_commands_executed"))
            and not bool(manifest.get("device_mutations"))
        )
        results.append(ClassifierCaseResult(
            name=name,
            status="pass" if ok else "blocked",
            decision=str(manifest.get("decision")),
            expected_decision=expected_decision,
            pass_value=bool(manifest.get("pass")),
            expected_pass=expected_pass,
            missing_fragments=missing,
            detail=f"case_manifest={path}",
        ))
    failed = [item.name for item in results if item.status != "pass"]
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "decision": "service-manager-runtime-gap-classifier-regression-pass" if not failed else "service-manager-runtime-gap-classifier-regression-failed",
        "pass": not failed,
        "reason": "all classifier cases passed" if not failed else "failed cases: " + ", ".join(failed),
        "next_step": "classify live V376 runtime gap",
        "host": collect_host_metadata(),
        "results": [asdict(item) for item in results],
        "device_commands_executed": False,
        "device_mutations": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    if "results" in manifest:
        rows = [[item["name"], item["status"], item["decision"], str(item["pass_value"]), item["detail"]] for item in manifest["results"]]
        body = markdown_table(["case", "status", "decision", "pass", "detail"], rows)
    else:
        rows = [
            [
                item["target"],
                item["helper_result"],
                item["helper_reason"],
                item["child_signal"],
                str(item["binder_open_failed"]),
                str(item["dev_properties_missing"]),
                str(item["signal_abort"]),
                str(item["stderr_sigabrt"]),
                str(item["ptrace_exec_stop"]),
                str(item["ptrace_crash_stop"]),
                str(item["postflight_safe"]),
            ]
            for item in manifest["target_gaps"]
        ]
        body = markdown_table(["target", "result", "reason", "signal", "binder_open_failed", "props_missing", "signal_abort", "stderr_sigabrt", "ptrace_exec", "ptrace_crash", "safe"], rows)
    return "\n".join([
        "# V378 Service-Manager Runtime Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Details",
        "",
        body,
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    if args.command == "regression":
        manifest = run_regression(args, store)
    else:
        manifest = build_manifest(args, load_json(args.v376_manifest))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
