#!/usr/bin/env python3
"""Generate a controlled CNSS start-only experiment plan without execution."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import REPO_ROOT, collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_V216_MANIFEST = Path("tmp/wifi/v216-service-replay-model/manifest.json")
DEFAULT_V221_MANIFEST = Path("tmp/wifi/v221-host-vendor-elf-library-evidence/manifest.json")
DEFAULT_V222_MANIFEST = Path("tmp/wifi/v222-vendor-root-evidence-export/manifest.json")
DEFAULT_V223_MANIFEST = Path("tmp/wifi/v223-recovery-rollback-policy/manifest.json")
DEFAULT_V224_MANIFEST = Path("tmp/wifi/v224-android-env-shim-materialize/manifest.json")
DEFAULT_V225_MANIFEST = Path("tmp/wifi/v225-exposure-security-gate-v3/manifest.json")
DEFAULT_V227_MANIFEST = Path("tmp/wifi/v227-android-core-system-library-evidence/manifest.json")

EXPECTED_DECISIONS = {
    "v216": "replay-model-ready",
    "v221": "elf-evidence-ready",
    "v222": "vendor-root-ready",
    "v223": "reboot-recovery-accepted",
    "v224": "shim-dryrun-ready",
    "v225": "cnss-start-plan-approved",
    "v227": "system-root-ready",
}

TARGET_SERVICES = ("cnss-daemon", "cnss_diag")
ACTIVE_PATTERNS = (
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r"\b(?:iw|wpa_cli)\b.*\b(scan|connect|set_network|enable_network)\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\b(?:dhcpcd|udhcpc|dnsmasq|hostapd)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r">\s*/sys/|>\s*/proc/sys/|>\s*/config/", re.IGNORECASE),
)

# v228 is a planner only. These are deliberately empty to make accidental live
# command introduction fail during validation.
NO_DEVICE_COMMANDS: tuple[tuple[str, list[str]], ...] = ()


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v228-controlled-cnss-start-plan"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216_MANIFEST)
    parser.add_argument("--v221-manifest", type=Path, default=DEFAULT_V221_MANIFEST)
    parser.add_argument("--v222-manifest", type=Path, default=DEFAULT_V222_MANIFEST)
    parser.add_argument("--v223-manifest", type=Path, default=DEFAULT_V223_MANIFEST)
    parser.add_argument("--v224-manifest", type=Path, default=DEFAULT_V224_MANIFEST)
    parser.add_argument("--v225-manifest", type=Path, default=DEFAULT_V225_MANIFEST)
    parser.add_argument("--v227-manifest", type=Path, default=DEFAULT_V227_MANIFEST)
    return parser.parse_args()


def validate_no_live_commands() -> None:
    command_text = "\n".join(" ".join(argv) for _, argv in NO_DEVICE_COMMANDS)
    for pattern in ACTIVE_PATTERNS:
        if pattern.search(command_text):
            raise AssertionError(f"active command pattern present in v228 planner: {pattern.pattern}")


def load_json(path: Path) -> dict[str, Any]:
    full_path = repo_path(path)
    if not full_path.exists():
        return {"missing": True, "path": str(full_path)}
    data = json.loads(full_path.read_text(encoding="utf-8"))
    data["_manifest_path"] = str(full_path)
    return data


def manifest_decision(manifest: dict[str, Any]) -> str:
    if manifest.get("missing"):
        return "missing"
    return str(manifest.get("decision", "unknown"))


def build_prerequisites(manifests: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, expected in EXPECTED_DECISIONS.items():
        manifest = manifests[key]
        actual = manifest_decision(manifest)
        ok = bool(manifest.get("pass")) and actual == expected
        rows.append(
            {
                "name": key,
                "expected_decision": expected,
                "actual_decision": actual,
                "pass": ok,
                "manifest": manifest.get("_manifest_path", manifest.get("path", "")),
                "reason": manifest.get("reason", ""),
            }
        )
    return rows


def service_from_v216(v216: dict[str, Any], name: str) -> dict[str, Any]:
    for service in v216.get("graph", {}).get("services", []):
        if isinstance(service, dict) and service.get("name") == name:
            return service
    return {"name": name, "missing": True}


def service_from_v221(v221: dict[str, Any], name: str) -> dict[str, Any]:
    for daemon in v221.get("daemons", []):
        if isinstance(daemon, dict) and daemon.get("name") == name:
            return daemon
    return {"name": name, "missing": True}


def service_model(v216: dict[str, Any], v221: dict[str, Any]) -> list[dict[str, Any]]:
    services: list[dict[str, Any]] = []
    for name in TARGET_SERVICES:
        from_v216 = service_from_v216(v216, name)
        from_v221 = service_from_v221(v221, name)
        services.append(
            {
                "name": name,
                "phase": "phase1-primary" if name == "cnss-daemon" else "phase2-optional-diagnostic",
                "binary": from_v221.get("executable") or from_v216.get("executable", ""),
                "vendor_relative_path": from_v221.get("vendor_relative_path", ""),
                "args": from_v221.get("args") or from_v216.get("args", []),
                "user": from_v221.get("user") or from_v216.get("user", ""),
                "groups": from_v221.get("groups") or from_v216.get("groups", []),
                "capabilities": from_v221.get("capabilities") or from_v216.get("capabilities", []),
                "classes": from_v221.get("classes") or from_v216.get("classes", []),
                "flags": from_v221.get("flags") or from_v216.get("flags", []),
                "android_state": from_v216.get("android_state", ""),
                "android_pid": from_v216.get("android_pid", ""),
                "source": from_v216.get("source", ""),
                "inspection": from_v221.get("inspection", ""),
                "unresolved_libraries": from_v221.get("unresolved_libraries", []),
            }
        )
    return services


def validate_service_model(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    by_name = {service["name"]: service for service in services}
    daemon = by_name.get("cnss-daemon", {})
    diag = by_name.get("cnss_diag", {})
    checks.append(
        {
            "name": "cnss-daemon-present",
            "pass": daemon.get("binary") == "/system/vendor/bin/cnss-daemon",
            "detail": str(daemon.get("binary", "")),
        }
    )
    checks.append(
        {
            "name": "cnss-daemon-args",
            "pass": daemon.get("args") == ["-n", "-l"],
            "detail": " ".join(daemon.get("args", [])),
        }
    )
    checks.append(
        {
            "name": "cnss-daemon-net-admin-explicit",
            "pass": "NET_ADMIN" in daemon.get("capabilities", []),
            "detail": ",".join(daemon.get("capabilities", [])),
        }
    )
    checks.append(
        {
            "name": "cnss-daemon-elf-closed",
            "pass": daemon.get("inspection") == "ok" and not daemon.get("unresolved_libraries"),
            "detail": str(daemon.get("inspection", "")),
        }
    )
    checks.append(
        {
            "name": "cnss-diag-present",
            "pass": diag.get("binary") == "/system/vendor/bin/cnss_diag",
            "detail": str(diag.get("binary", "")),
        }
    )
    checks.append(
        {
            "name": "cnss-diag-phase2-only",
            "pass": diag.get("phase") == "phase2-optional-diagnostic",
            "detail": "diagnostic sidecar must not run before primary daemon start-only passes",
        }
    )
    checks.append(
        {
            "name": "cnss-diag-elf-closed",
            "pass": diag.get("inspection") == "ok" and not diag.get("unresolved_libraries"),
            "detail": str(diag.get("inspection", "")),
        }
    )
    return checks


def build_command_allowlist(services: list[dict[str, Any]]) -> dict[str, Any]:
    daemon = next(service for service in services if service["name"] == "cnss-daemon")
    diag = next(service for service in services if service["name"] == "cnss_diag")
    return {
        "mode": "structured-allowlist-only",
        "planner_live_commands": [],
        "read_only_preflight_commands": [
            ["version"],
            ["status"],
            ["bootstatus"],
            ["selftest", "verbose"],
            ["wifiinv", "full"],
            ["kernelinv", "summary"],
            ["netservice", "status"],
            ["logpath"],
            ["longsoak", "status", "verbose"],
        ],
        "future_structured_actions": [
            {
                "name": "stage-temporary-runtime-root",
                "allowed_in_v228": False,
                "allowed_in_v229_with_confirmation": True,
                "description": "prepare /tmp/a90-v229-* read-only alias tree from v222/v227 evidence",
            },
            {
                "name": "spawn-cnss-daemon-start-only",
                "allowed_in_v228": False,
                "allowed_in_v229_with_confirmation": True,
                "binary": daemon["binary"],
                "argv": daemon["args"],
                "timeout_sec": 10,
                "hard_timeout_sec": 30,
                "requires_capabilities": daemon["capabilities"],
                "phase": daemon["phase"],
            },
            {
                "name": "spawn-cnss-diag-diagnostic-only",
                "allowed_in_v228": False,
                "allowed_in_v229_with_confirmation": False,
                "binary": diag["binary"],
                "argv": diag["args"],
                "phase": diag["phase"],
                "condition": "only after cnss-daemon start-only passes and a separate confirmation enables phase2",
            },
            {
                "name": "stop-cnss-process-group",
                "allowed_in_v228": False,
                "allowed_in_v229_with_confirmation": True,
                "signals": ["SIGTERM", "SIGKILL"],
                "description": "bounded stop/reap by tracked pid/process group only",
            },
        ],
        "denied_patterns": [
            "rfkill unblock/block",
            "ip link set <wifi-iface> up",
            "iw scan/connect/set",
            "wpa_supplicant/hostapd/wificond/Wi-Fi HAL start",
            "DHCP/routing/NAT/DNS changes",
            "credential path reads/writes",
            "generic ICNSS unbind/bind/driver_override writes",
            "persistent system/vendor/data writes",
            "free-form run passthrough for CNSS experiment",
        ],
    }


def build_start_plan(services: list[dict[str, Any]], v224: dict[str, Any]) -> dict[str, Any]:
    materialization = v224.get("materialization", {}) if isinstance(v224.get("materialization"), dict) else {}
    artifacts = materialization.get("artifacts", {}) if isinstance(materialization.get("artifacts"), dict) else {}
    return {
        "decision_scope": "plan-only-no-daemon-execution",
        "version_after_plan": "v229 should implement planner/runner with explicit operator confirmation",
        "phases": [
            {
                "name": "preflight",
                "action": "collect read-only native status and prerequisite manifest decisions",
                "must_pass": True,
            },
            {
                "name": "stage-runtime",
                "action": "prepare temporary read-only runtime alias tree from vendor/system evidence roots",
                "must_pass": True,
                "source_artifacts": sorted(artifacts.keys()),
            },
            {
                "name": "start-cnss-daemon",
                "action": "structured spawn of cnss-daemon only; no scan/connect/link-up",
                "service": next(service for service in services if service["name"] == "cnss-daemon"),
                "default_timeout_sec": 10,
                "hard_timeout_sec": 30,
            },
            {
                "name": "observe",
                "action": "capture process, native log, dmesg excerpts, Wi-Fi inventory deltas",
                "must_detect": ["process pid or clean runtime gap", "no credential access", "no active scan/connect"],
            },
            {
                "name": "stop",
                "action": "SIGTERM then SIGKILL process group, reap, verify no stale daemon",
                "must_pass": True,
            },
            {
                "name": "postflight",
                "action": "repeat read-only inventory and mark reboot-required if state is not restored",
                "must_pass": True,
            },
        ],
        "phase2_candidate": next(service for service in services if service["name"] == "cnss_diag"),
    }


def build_rollback_policy(v223: dict[str, Any]) -> dict[str, Any]:
    policy = v223.get("policy", {}) if isinstance(v223.get("policy"), dict) else {}
    return {
        "source_decision": v223.get("decision"),
        "accepted_recovery": [
            item for item in policy.get("recovery_primitives", []) if item.get("status") == "accepted"
        ],
        "denied_recovery": [
            item for item in policy.get("recovery_primitives", []) if item.get("status") == "denied"
        ],
        "stop_conditions": policy.get("stop_conditions", []),
        "post_reboot_verification": policy.get("post_reboot_verification", []),
        "normal_stop": [
            "SIGTERM tracked process group",
            "bounded wait",
            "SIGKILL if still alive",
            "reap and verify no stale cnss-daemon/cnss_diag",
            "repeat read-only inventory",
        ],
        "failure_policy": "mark reboot-required; do not use generic ICNSS unbind/bind",
    }


def build_exposure_boundary(v225: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_decision": v225.get("decision"),
        "gate": v225.get("gate", {}),
        "exposure_matrix": v225.get("exposure_matrix", []),
        "allowed_boundary": "USB-local/host-local operator workflow only",
        "wireless_client_reachability": "denied",
        "credential_collection": "denied",
        "listener_broadening": "denied",
        "routing_or_firewall_mutation": "denied",
    }


def decide(prerequisites: list[dict[str, Any]], service_checks: list[dict[str, Any]]) -> tuple[str, str, bool]:
    missing = [item["name"] for item in prerequisites if item["actual_decision"] == "missing"]
    regressed = [item["name"] for item in prerequisites if item["actual_decision"] != "missing" and not item["pass"]]
    service_failures = [item["name"] for item in service_checks if not item["pass"]]
    if missing:
        return "start-plan-blocked", f"missing prerequisite manifests: {', '.join(missing)}", False
    if regressed:
        return "start-plan-blocked", f"prerequisite decisions regressed: {', '.join(regressed)}", False
    if service_failures:
        return "manual-review-required", f"service model checks failed: {', '.join(service_failures)}", False
    return "cnss-start-plan-ready", "controlled CNSS start-only plan is ready; no daemon execution performed", True


def build_summary(manifest: dict[str, Any]) -> str:
    prereq_rows = [
        [item["name"], item["expected_decision"], item["actual_decision"], "PASS" if item["pass"] else "FAIL"]
        for item in manifest["prerequisites"]
    ]
    service_rows = [
        [
            item["name"],
            item["phase"],
            item["binary"],
            " ".join(item.get("args", [])),
            ",".join(item.get("capabilities", [])) or "none",
        ]
        for item in manifest["services"]
    ]
    check_rows = [[item["name"], "PASS" if item["pass"] else "FAIL", item["detail"]] for item in manifest["service_checks"]]
    lines = [
        "# v228 Controlled CNSS Start-Only Plan",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        "- live daemon execution: `none`",
        "",
        "## Prerequisites",
        "",
        markdown_table(["name", "expected", "actual", "status"], prereq_rows),
        "",
        "## Service Model",
        "",
        markdown_table(["service", "phase", "binary", "args", "capabilities"], service_rows),
        "",
        "## Service Checks",
        "",
        markdown_table(["check", "status", "detail"], check_rows),
        "",
        "## Guardrails",
        "",
    ]
    for guardrail in manifest["guardrails"]:
        lines.append(f"- {guardrail}")
    lines.extend(
        [
            "",
            "## Next Step",
            "",
            "- Implement v229 controlled CNSS start planner/runner with explicit operator confirmation.",
            "- Keep scan/connect/credential/routing out of scope until start-only passes cleanly.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_live_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)
    manifests = {
        "v216": load_json(args.v216_manifest),
        "v221": load_json(args.v221_manifest),
        "v222": load_json(args.v222_manifest),
        "v223": load_json(args.v223_manifest),
        "v224": load_json(args.v224_manifest),
        "v225": load_json(args.v225_manifest),
        "v227": load_json(args.v227_manifest),
    }
    prerequisites = build_prerequisites(manifests)
    services = service_model(manifests["v216"], manifests["v221"])
    service_checks = validate_service_model(services)
    command_allowlist = build_command_allowlist(services)
    start_plan = build_start_plan(services, manifests["v224"])
    rollback_policy = build_rollback_policy(manifests["v223"])
    exposure_boundary = build_exposure_boundary(manifests["v225"])
    decision, reason, pass_ok = decide(prerequisites, service_checks)
    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "mode": "controlled-cnss-start-only-plan",
        "inputs": {
            "v216_manifest": str(repo_path(args.v216_manifest)),
            "v221_manifest": str(repo_path(args.v221_manifest)),
            "v222_manifest": str(repo_path(args.v222_manifest)),
            "v223_manifest": str(repo_path(args.v223_manifest)),
            "v224_manifest": str(repo_path(args.v224_manifest)),
            "v225_manifest": str(repo_path(args.v225_manifest)),
            "v227_manifest": str(repo_path(args.v227_manifest)),
        },
        "prerequisites": prerequisites,
        "services": services,
        "service_checks": service_checks,
        "command_allowlist": command_allowlist,
        "start_plan": start_plan,
        "rollback_policy": rollback_policy,
        "exposure_boundary": exposure_boundary,
        "guardrails": [
            "v228 planner performs no live device commands",
            "no CNSS daemon execution in v228",
            "no rfkill write, link-up, scan, connect, DHCP, routing, NAT, or DNS changes",
            "no credential path access",
            "no persistent system/vendor/data writes",
            "future v229 execution must use explicit operator confirmation",
            "reboot remains the only accepted recovery primitive if state cannot be restored",
        ],
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("start-plan.json", start_plan)
    store.write_json("command-allowlist.json", command_allowlist)
    store.write_json("rollback-policy.json", rollback_policy)
    store.write_json("exposure-boundary.json", exposure_boundary)
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
