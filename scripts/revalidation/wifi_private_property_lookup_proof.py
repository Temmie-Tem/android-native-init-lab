#!/usr/bin/env python3
"""Plan/refuse a private Android property lookup proof.

v320 is intentionally fail-closed until the v317 live private property namespace
proof has passed.  The implemented path here is host-only planning/refusal
evidence.  It does not start Android daemons, does not create global property
runtime paths, and does not execute Wi-Fi bring-up actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path, strip_cmdv1_text
from a90ctl import ProtocolResult, run_cmdv1_command
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v320-private-property-lookup-proof")
DEFAULT_V312 = Path("tmp/wifi/v312-private-property-runtime-layout/manifest.json")
DEFAULT_V317 = Path("tmp/wifi/v317-private-property-namespace-proof/manifest.json")
DEFAULT_V319_REPORT = Path("docs/reports/NATIVE_INIT_V319_SERIAL_TRANSFER_APPEND_2026-05-19.md")
APPROVAL_PHRASE = "approve v320 private property lookup proof only; no daemon start and no Wi-Fi bring-up"
REMOTE_V317_WORKDIR = "/mnt/sdext/a90/private-property-v317"
PRIVATE_PROP_ROOT = REMOTE_V317_WORKDIR + "/dev/__properties__"
EXPECTED_NATIVE_BUILD = "A90 Linux init 0.9.61 (v319)"
DEFAULT_HELPER_PATH = "/cache/bin/a90_android_execns_probe"
ALLOWED_LOOKUP_KEYS = {
    "ro.build.version.sdk",
    "ro.build.version.release",
    "ro.product.vendor.device",
    "ro.board.platform",
    "ro.product.name",
    "ro.hardware",
    "ro.vendor.build.version.sdk",
}


@dataclass
class LookupCheck:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]


@dataclass
class LookupKey:
    key: str
    expected_value: str
    context: str
    prop_type: str
    source: str


@dataclass
class HelperLookupResult:
    key: str
    expected_value: str
    observed_value: str
    status: str
    rc: int | None
    protocol_status: str
    command: list[str]
    text: str
    error: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v312-manifest", type=Path, default=DEFAULT_V312)
    parser.add_argument("--v317-manifest", type=Path, default=DEFAULT_V317)
    parser.add_argument("--v319-report", type=Path, default=DEFAULT_V319_REPORT)
    parser.add_argument("--approval-phrase", default="")
    parser.add_argument("--allow-device-mutation", action="store_true")
    parser.add_argument("--assume-yes", action="store_true")
    parser.add_argument("--bridge-host", default="127.0.0.1")
    parser.add_argument("--bridge-port", type=int, default=54321)
    parser.add_argument("--bridge-timeout", type=float, default=90.0)
    parser.add_argument("--helper-path", default=DEFAULT_HELPER_PATH)
    parser.add_argument("--helper-timeout-sec", type=int, default=10)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    subparsers.add_parser("cleanup")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def path_present(path: Path) -> tuple[bool, str]:
    resolved = repo_path(path)
    return resolved.exists(), str(resolved)


def selected_lookup_keys(v312: dict[str, Any]) -> list[LookupKey]:
    keys: list[LookupKey] = []
    for item in v312.get("mappings", []):
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        value = str(item.get("value") or "")
        context = str(item.get("context") or "")
        if not key or not value or not context:
            continue
        if key not in ALLOWED_LOOKUP_KEYS:
            continue
        if str(item.get("status") or "") != "pass":
            continue
        keys.append(LookupKey(
            key=key,
            expected_value=value,
            context=context,
            prop_type=str(item.get("prop_type") or ""),
            source=str(item.get("source") or ""),
        ))
    return keys


def build_checks(args: argparse.Namespace,
                 v312: dict[str, Any],
                 v317: dict[str, Any],
                 v319_report_present: bool,
                 v319_report_path: str,
                 keys: list[LookupKey]) -> list[LookupCheck]:
    approval_ok = (
        args.approval_phrase == APPROVAL_PHRASE
        and args.allow_device_mutation
        and args.assume_yes
    )
    v312_ok = (
        v312.get("present")
        and v312.get("decision") == "private-property-layout-dryrun-ready"
        and bool(v312.get("pass"))
    )
    v317_ok = (
        v317.get("present")
        and v317.get("decision") == "private-property-namespace-proof-pass"
        and bool(v317.get("pass"))
    )
    return [
        LookupCheck(
            "v319-native-baseline",
            "pass" if v319_report_present else "blocked",
            "blocker",
            f"expected={EXPECTED_NATIVE_BUILD} report_present={v319_report_present}",
            [v319_report_path],
        ),
        LookupCheck(
            "v312-property-layout",
            "pass" if v312_ok else "blocked",
            "blocker",
            f"decision={v312.get('decision')} pass={v312.get('pass')}",
            [str(v312.get("path", ""))],
        ),
        LookupCheck(
            "lookup-key-selection",
            "pass" if keys else "blocked",
            "blocker",
            f"selected_keys={len(keys)}",
            [item.key for item in keys],
        ),
        LookupCheck(
            "v317-live-proof",
            "pass" if v317_ok else "blocked",
            "blocker",
            f"decision={v317.get('decision')} pass={v317.get('pass')} present={v317.get('present')}",
            [str(v317.get("path", ""))],
        ),
        LookupCheck(
            "approval-gate",
            "pass" if approval_ok else "needs-operator",
            "approval",
            f"phrase_match={args.approval_phrase == APPROVAL_PHRASE} allow_device_mutation={args.allow_device_mutation} assume_yes={args.assume_yes}",
            [APPROVAL_PHRASE],
        ),
    ]


def decide(command: str, checks: list[LookupCheck]) -> tuple[str, bool, str, str]:
    if command == "cleanup":
        return (
            "private-property-lookup-cleanup-not-needed",
            True,
            "v320 live path has not created a private workspace yet",
            "wait for v317 live proof before implementing v320 live lookup",
        )

    blockers = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if "v317-live-proof" in blockers:
        return (
            "private-property-lookup-blocked-v317-missing",
            False,
            "v317 live proof has not passed, so private property lookup must not run",
            "run v317 only after exact v317 approval phrase",
        )
    if blockers:
        return (
            "private-property-lookup-plan-blocked",
            False,
            "blocked checks: " + ", ".join(blockers),
            "repair prerequisite evidence before v320 implementation",
        )
    if command == "plan":
        return (
            "private-property-lookup-plan-ready",
            True,
            "all prerequisites are present; live run still requires approval and helper implementation",
            "implement helper property-lookup mode and run after exact v320 approval phrase",
        )

    approval = [check.name for check in checks if check.severity == "approval" and check.status != "pass"]
    if approval:
        return (
            "private-property-lookup-approval-required",
            False,
            "exact v320 approval phrase and mutation flags are required",
            "provide the exact v320 approval phrase only after reviewing the live operation boundary",
        )
    return (
        "private-property-lookup-ready-to-run-helper",
        True,
        "all gates passed; read-only helper lookup may execute",
        "run helper property-lookup mode and compare values",
    )


def helper_command(args: argparse.Namespace, key: str) -> list[str]:
    return [
        "run",
        args.helper_path,
        "--system-root",
        "/mnt/system/system",
        "--vendor-block",
        "/dev/block/sda29",
        "--vendor-fstype",
        "ext4",
        "--target-profile",
        "system-getprop",
        "--mode",
        "property-lookup",
        "--null-device-mode",
        "dev-null",
        "--property-root",
        PRIVATE_PROP_ROOT,
        "--property-key",
        key,
        "--timeout-sec",
        str(args.helper_timeout_sec),
    ]


def extract_execns_stdout(text: str) -> str:
    stripped = strip_cmdv1_text(text)
    begin = "A90_EXECNS_STDOUT_BEGIN"
    end = "A90_EXECNS_STDOUT_END"
    if begin not in stripped or end not in stripped:
        return ""
    body = stripped.split(begin, 1)[1].split(end, 1)[0]
    return body.strip()


def run_helper_lookup(args: argparse.Namespace, keys: list[LookupKey]) -> list[HelperLookupResult]:
    results: list[HelperLookupResult] = []
    for item in keys:
        command = helper_command(args, item.key)
        try:
            capture: ProtocolResult = run_cmdv1_command(
                args.bridge_host,
                args.bridge_port,
                args.bridge_timeout,
                command,
                retry_unsafe=False,
            )
            observed = extract_execns_stdout(capture.text)
            status = "pass" if capture.rc == 0 and capture.status == "ok" and observed == item.expected_value else "mismatch"
            results.append(HelperLookupResult(
                key=item.key,
                expected_value=item.expected_value,
                observed_value=observed,
                status=status,
                rc=capture.rc,
                protocol_status=capture.status,
                command=command,
                text=capture.text,
                error="",
            ))
        except Exception as exc:  # noqa: BLE001 - proof records failure evidence
            results.append(HelperLookupResult(
                key=item.key,
                expected_value=item.expected_value,
                observed_value="",
                status="error",
                rc=None,
                protocol_status="missing",
                command=command,
                text="",
                error=str(exc),
            ))
    return results


def decide_after_helper(results: list[HelperLookupResult]) -> tuple[str, bool, str, str]:
    if not results:
        return (
            "private-property-lookup-getprop-empty",
            False,
            "no helper lookup results were produced",
            "check lookup key selection and helper deployment",
        )
    if all(item.status == "pass" for item in results):
        return (
            "private-property-lookup-getprop-pass",
            True,
            f"{len(results)} allowlisted properties matched expected v312 values",
            "proceed to bounded CNSS pre-start environment probe planning",
        )
    if any(item.status == "error" for item in results):
        return (
            "private-property-lookup-helper-error",
            False,
            "one or more helper executions failed",
            "inspect helper lookup captures before retry",
        )
    return (
        "private-property-lookup-getprop-mismatch",
        False,
        "getprop ran but observed values did not match expected v312 values",
        "compare private property layout and bionic property lookup behavior",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v312 = load_json(args.v312_manifest)
    v317 = load_json(args.v317_manifest)
    v319_report_present, v319_report_path = path_present(args.v319_report)
    keys = selected_lookup_keys(v312)
    checks = build_checks(args, v312, v317, v319_report_present, v319_report_path, keys)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "command": args.command,
        "host": collect_host_metadata(),
        "native_baseline": EXPECTED_NATIVE_BUILD,
        "remote_v317_workdir": REMOTE_V317_WORKDIR,
        "private_property_root": PRIVATE_PROP_ROOT,
        "inputs": {
            "v312": {"path": v312.get("path"), "present": bool(v312.get("present")), "decision": v312.get("decision"), "pass": v312.get("pass")},
            "v317": {"path": v317.get("path"), "present": bool(v317.get("present")), "decision": v317.get("decision"), "pass": v317.get("pass")},
            "v319_report": {"path": v319_report_path, "present": v319_report_present},
        },
        "checks": [asdict(check) for check in checks],
        "lookup_keys": [asdict(item) for item in keys],
        "planned_device_helper": {
            "binary": args.helper_path,
            "mode": "property-lookup",
            "target_profile": "system-getprop",
            "target": "/system/bin/getprop",
            "namespace": "private mount namespace only",
            "property_root_visible_as": "/dev/__properties__",
        },
        "planned_device_commands": [helper_command(args, item.key) for item in keys],
        "helper_lookup_results": [],
        "required_approval_phrase": APPROVAL_PHRASE,
        "device_commands_executed": False,
        "device_mutations": False,
        "explicitly_not_approved": [
            "global /dev/__properties__ replacement or bind mount",
            "global /dev/socket/property_service creation",
            "property mutation or setprop-like writes",
            "service-manager or hwservicemanager start",
            "Wi-Fi HAL, wificond, supplicant, hostapd, CNSS, or diag daemon start",
            "Wi-Fi scan/connect/link-up/credential/DHCP/routing",
            "rfkill write, module load/unload, firmware mutation, or partition write",
            "public network listener creation",
        ],
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [[item["name"], item["status"], item["severity"], item["detail"], "<br>".join(item["evidence"])] for item in manifest["checks"]]
    key_rows = [[item["key"], item["expected_value"], item["context"], item["prop_type"]] for item in manifest["lookup_keys"]]
    input_rows = [[name, str(item["present"]), str(item.get("decision")), str(item.get("pass")), str(item["path"])] for name, item in manifest["inputs"].items()]
    helper_rows = [
        [
            item["key"],
            item["status"],
            item["expected_value"],
            item["observed_value"],
            str(item["rc"]),
            item["protocol_status"],
            item["error"],
        ]
        for item in manifest.get("helper_lookup_results", [])
    ]
    command_rows = [
        [str(index), " ".join(command)]
        for index, command in enumerate(manifest.get("planned_device_commands", []), start=1)
    ]
    return "\n".join([
        "# v320 Private Property Lookup Proof",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- pass: `{manifest['pass']}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- device_mutations: `{manifest['device_mutations']}`",
        "",
        "## Inputs",
        "",
        markdown_table(["name", "present", "decision", "pass", "path"], input_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "evidence"], check_rows),
        "",
        "## Lookup Keys",
        "",
        markdown_table(["key", "expected", "context", "type"], key_rows),
        "",
        "## Planned Device Commands",
        "",
        markdown_table(["#", "command"], command_rows),
        "",
        "## Helper Lookup Results",
        "",
        markdown_table(["key", "status", "expected", "observed", "rc", "protocol", "error"], helper_rows),
        "",
        "## Required Approval Phrase",
        "",
        f"`{manifest['required_approval_phrase']}`",
        "",
        "## Explicitly Not Approved",
        "",
        "\n".join(f"- {item}" for item in manifest["explicitly_not_approved"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    if manifest["decision"] == "private-property-lookup-ready-to-run-helper" and args.command == "run":
        helper_results = run_helper_lookup(
            args,
            [LookupKey(**item) for item in manifest["lookup_keys"]],
        )
        decision, pass_ok, reason, next_step = decide_after_helper(helper_results)
        manifest["helper_lookup_results"] = [asdict(item) for item in helper_results]
        manifest["decision"] = decision
        manifest["pass"] = pass_ok
        manifest["reason"] = reason
        manifest["next_step"] = next_step
        manifest["device_commands_executed"] = True
        manifest["device_mutations"] = True
    store = EvidenceStore(repo_path(args.out_dir))
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
