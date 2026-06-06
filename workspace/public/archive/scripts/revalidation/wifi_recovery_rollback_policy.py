#!/usr/bin/env python3
"""Generate a read-only ICNSS recovery/rollback policy from existing evidence."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V214_MANIFEST = Path("tmp/wifi/v214-icnss-reprobe/manifest.json")
DEFAULT_V214_REPORT = Path("docs/reports/NATIVE_INIT_V214_ICNSS_REPROBE_EXECUTION_2026-05-13.md")
DEFAULT_V217_NATIVE_MANIFEST = Path("tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json")
DEFAULT_V220_MANIFEST = Path("tmp/wifi/v220-bringup-gate-v2/manifest.json")
DEFAULT_V222_MANIFEST = Path("tmp/wifi/v222-vendor-root-evidence-export/manifest.json")

ACTIVE_PATTERNS = (
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r"\breboot\b|\bpoweroff\b", re.IGNORECASE),
    re.compile(r">\s*/sys/|>\s*/proc/sys/|>\s*/config/", re.IGNORECASE),
)

NO_DEVICE_COMMANDS: tuple[tuple[str, list[str]], ...] = ()


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v223-recovery-rollback-policy"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v214-manifest", type=Path, default=DEFAULT_V214_MANIFEST)
    parser.add_argument("--v214-report", type=Path, default=DEFAULT_V214_REPORT)
    parser.add_argument("--v217-native-manifest", type=Path, default=DEFAULT_V217_NATIVE_MANIFEST)
    parser.add_argument("--v220-manifest", type=Path, default=DEFAULT_V220_MANIFEST)
    parser.add_argument("--v222-manifest", type=Path, default=DEFAULT_V222_MANIFEST)
    return parser.parse_args()


def validate_no_active_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv in NO_DEVICE_COMMANDS)
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"active command pattern present: {pattern.pattern}")


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def load_text(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path), "text": ""}
    return {"missing": False, "path": str(full_path), "text": full_path.read_text(encoding="utf-8", errors="replace")}


def gate_item(manifest: dict[str, Any], name: str) -> dict[str, str]:
    gate = manifest.get("gate")
    if not isinstance(gate, dict):
        return {}
    for item in gate.get("items", []):
        if isinstance(item, dict) and item.get("name") == name:
            return {str(key): str(value) for key, value in item.items()}
    return {}


def v214_post_reboot_evidence(report: dict[str, Any]) -> dict[str, Any]:
    text = str(report.get("text") or "")
    checks = {
        "has_post_reboot_section": "Post-reboot recovery check" in text,
        "driver_icnss": "DRIVER=icnss" in text,
        "bound_path_present": "/sys/bus/platform/drivers/icnss contains 18800000.qcom,icnss" in text,
        "firmware_path_restored": "firmware_class.path = /vendor/firmware_mnt/image" in text,
        "recovery_hash_present": "tmp/wifi/v214-post-reboot-recovery.txt" in text,
    }
    return {
        "source": report.get("path"),
        "missing": bool(report.get("missing")),
        "checks": checks,
        "complete": all(checks.values()),
    }


def build_policy(v214: dict[str, Any],
                 v214_report: dict[str, Any],
                 v217: dict[str, Any],
                 v220: dict[str, Any],
                 v222: dict[str, Any]) -> dict[str, Any]:
    post_reboot = v214_post_reboot_evidence(v214_report)
    icnss_gate = gate_item(v220, "icnss_recovery")
    risk_summary = v217.get("risk_summary") if isinstance(v217.get("risk_summary"), dict) else {}
    dangerous_writes = int(risk_summary.get("write-only-dangerous", 0)) + int(risk_summary.get("writable-unknown", 0))

    return {
        "recovery_primitives": [
            {
                "name": "native_reboot",
                "status": "accepted",
                "reason": "v214 post-reboot evidence restored ICNSS bound state",
                "requires_manual_or_explicit_runner": True,
            },
            {
                "name": "generic_icnss_unbind_bind",
                "status": "denied",
                "reason": "v214 bind/rebind failed and left driver state broken until reboot",
            },
            {
                "name": "driver_override",
                "status": "denied",
                "reason": "v217 classifies driver_override as dangerous recovery surface",
            },
            {
                "name": "unreviewed_sysfs_debugfs_configfs_write",
                "status": "denied",
                "reason": "v217 found unsafe writable/recovery controls",
            },
        ],
        "stop_conditions": [
            "ICNSS is not bound after a temporary experiment",
            "firmware_class.path rollback/readback mismatches expected value",
            "serial/ACM rescue bridge is unavailable",
            "NCM rescue path is unavailable when the experiment depends on NCM",
            "test daemon cannot be stopped or reaped",
            "unexpected WLAN netdev or rfkill state appears",
            "kernel log contains ICNSS probe/recovery failure markers",
        ],
        "preflight_requirements": [
            "version",
            "status",
            "bootstatus",
            "selftest verbose",
            "netservice status",
            "wifiinv full or current Wi-Fi inventory equivalent",
            "v222/v221 vendor evidence status if daemon execution is later proposed",
        ],
        "post_reboot_verification": [
            "bridge reconnects",
            "version matches expected native init",
            "ICNSS bound state is restored",
            "firmware path rollback state is expected",
            "no stale test daemon remains",
            "longsoak/log evidence remains readable",
        ],
        "input_evidence": {
            "v214_decision": v214.get("decision"),
            "v214_pass": v214.get("pass"),
            "v214_post_reboot": post_reboot,
            "v217_decision": v217.get("decision"),
            "v217_risk_summary": risk_summary,
            "v217_unsafe_write_count": dangerous_writes,
            "v220_decision": v220.get("decision"),
            "v220_icnss_recovery_gate": icnss_gate,
            "v222_decision": v222.get("decision"),
            "v222_source_root_status": v222.get("source_root_status"),
        },
    }


def decide(policy: dict[str, Any],
           v214: dict[str, Any],
           v217: dict[str, Any],
           v220: dict[str, Any],
           v222: dict[str, Any]) -> tuple[str, str, bool]:
    evidence = policy["input_evidence"]
    expected = {
        "v214": v214.get("decision") == "icnss-rebind-failed",
        "v217": v217.get("decision") == "state-only-inventory",
        "v220": v220.get("decision") == "no-go",
        "v222": v222.get("decision") in {"export-source-required", "vendor-root-ready"},
    }
    if not all(expected.values()):
        bad = ", ".join(name for name, ok in expected.items() if not ok)
        return "manual-review-required", f"unexpected prerequisite decision: {bad}", False
    if evidence["v220_icnss_recovery_gate"].get("status") != "blocked":
        return "manual-review-required", "v220 icnss_recovery gate is not blocked as expected", False
    if not evidence["v214_post_reboot"]["complete"]:
        return "active-mutation-blocked", "post-reboot recovery evidence is incomplete", False
    if int(evidence["v217_unsafe_write_count"]) <= 0:
        return "manual-review-required", "v217 no longer shows unsafe recovery controls; policy needs review", False
    return "reboot-recovery-accepted", "reboot is the only accepted recovery primitive for later opt-in mutation planning", True


def build_summary(manifest: dict[str, Any]) -> str:
    policy = manifest["policy"]
    primitive_rows = [
        [item["name"], item["status"], item["reason"]]
        for item in policy["recovery_primitives"]
    ]
    evidence = policy["input_evidence"]
    evidence_rows = [
        ["v214 decision", str(evidence["v214_decision"])],
        ["v214 post reboot complete", str(evidence["v214_post_reboot"]["complete"])],
        ["v217 decision", str(evidence["v217_decision"])],
        ["v217 unsafe write count", str(evidence["v217_unsafe_write_count"])],
        ["v220 decision", str(evidence["v220_decision"])],
        ["v220 icnss gate", str(evidence["v220_icnss_recovery_gate"].get("status"))],
        ["v222 decision", str(evidence["v222_decision"])],
        ["v222 source root", str(evidence["v222_source_root_status"])],
    ]
    lines = [
        "# v223 Recovery / Rollback Policy",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        "",
        "## Evidence Summary",
        "",
        markdown_table(["item", "value"], evidence_rows),
        "",
        "## Recovery Primitives",
        "",
        markdown_table(["name", "status", "reason"], primitive_rows),
        "",
        "## Stop Conditions",
        "",
    ]
    for item in policy["stop_conditions"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Preflight Requirements", ""])
    for item in policy["preflight_requirements"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Post-Reboot Verification", ""])
    for item in policy["post_reboot_verification"]:
        lines.append(f"- {item}")
    lines.extend([
        "",
        "## Guardrails",
        "",
    ])
    for guardrail in manifest["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- This policy does not approve Wi-Fi scan/connect or daemon execution.",
        "- `reboot-recovery-accepted` only means future opt-in mutation plans may rely on reboot as the last-resort recovery path.",
        "- Generic ICNSS unbind/bind remains denied.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    store = EvidenceStore(repo_path(args.out_dir))

    v214 = load_json(args.v214_manifest)
    v214_report = load_text(args.v214_report)
    v217 = load_json(args.v217_native_manifest)
    v220 = load_json(args.v220_manifest)
    v222 = load_json(args.v222_manifest)

    policy = build_policy(v214, v214_report, v217, v220, v222)
    decision, reason, pass_ok = decide(policy, v214, v217, v220, v222)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "recovery-rollback-policy",
        "inputs": {
            "v214_manifest": str(repo_path(args.v214_manifest)),
            "v214_report": str(repo_path(args.v214_report)),
            "v217_native_manifest": str(repo_path(args.v217_native_manifest)),
            "v220_manifest": str(repo_path(args.v220_manifest)),
            "v222_manifest": str(repo_path(args.v222_manifest)),
        },
        "policy": policy,
        "guardrails": [
            "no live device commands by default",
            "no reboot execution",
            "no ICNSS sysfs/debugfs/configfs writes",
            "no daemon execution",
            "no rfkill write",
            "no link-up",
            "no scan/connect",
            "no firmware path mutation",
            "no NCM/ACM/tcpctl state changes",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("recovery-policy.json", policy)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={repo_path(args.out_dir)} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
