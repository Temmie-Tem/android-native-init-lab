#!/usr/bin/env python3
"""V864 host-only PeripheralManager init-contract helper support classifier.

This classifier compares V861/V862/V863 evidence against the current helper
source. It does not contact the device, deploy helpers, start services, use
Wi-Fi credentials, scan/connect, run DHCP/routes, ping externally, touch eSoC,
write sysfs/debugfs/GPIO/subsystem nodes, load modules, or write boot/partitions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v864-pm-init-contract-support")
DEFAULT_V861_MANIFEST = Path("tmp/wifi/v861-pm-service-domain-parity-live-r2/manifest.json")
DEFAULT_V862_MANIFEST = Path("tmp/wifi/v862-android-init-service-contract/manifest.json")
DEFAULT_V863_MANIFEST = Path("tmp/wifi/v863-pm-proxy-helper-rc-live/manifest.json")
DEFAULT_HELPER_SOURCE = Path("stage3/linux_init/helpers/a90_android_execns_probe.c")

EXPECTED_V861_DECISION = "v861-exec-target-accepted-current-kernel-no-subsys-hold"
EXPECTED_V862_DECISION = "v862-init-contract-classified-pm-proxy-helper-content-needed"
EXPECTED_V863_DECISION = "v863-pm-proxy-helper-contract-captured"

SERVICE_REQUIREMENTS = {
    "per_proxy_helper_child": {
        "description": "helper can launch vendor.per_proxy_helper /vendor/bin/pm_proxy_helper as a distinct oneshot child",
        "required_markers": ["/vendor/bin/pm_proxy_helper", "per_proxy_helper"],
    },
    "per_proxy_helper_selinux_context": {
        "description": "helper maps /vendor/bin/pm_proxy_helper to the Android per_proxy_helper SELinux domain",
        "required_markers": ["/vendor/bin/pm_proxy_helper", "per_proxy_helper:s0"],
    },
    "per_mgr_ioprio_rt4": {
        "description": "helper applies and records Android init ioprio rt 4 for vendor.per_mgr",
        "required_markers": ["SYS_ioprio_set", "IOPRIO_CLASS_RT", "ioprio"],
    },
    "per_proxy_property_start": {
        "description": "helper models init.svc.vendor.per_mgr=running before starting vendor.per_proxy",
        "required_markers": ["init.svc.vendor.per_mgr", "per_proxy"],
    },
    "per_proxy_shutdown_stop": {
        "description": "helper models shutdown stop semantics for vendor.per_proxy cleanup",
        "required_markers": ["sys.shutdown.requested", "per_proxy"],
    },
    "runtime_domain_capture": {
        "description": "helper captures requested exec target, runtime attr/current, and mismatch state for PM children",
        "required_markers": ["attr_current", "selinux_exec.target_context", "vendor_per_mgr"],
    },
    "subsystem_fd_capture": {
        "description": "helper captures /dev/subsys_esoc0 and /dev/subsys_modem fd targets for PM children",
        "required_markers": ["subsys_esoc0", "subsys_modem", "fd_links"],
    },
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_bytes().decode("utf-8", errors="replace")


def load_json(path: Path) -> dict[str, Any]:
    text = read_text(path)
    if not text:
        return {}
    return json.loads(text)


def run_host(command: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        command,
        cwd=repo_path(Path(".")),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    return result.returncode, result.stdout


def marker_present(source: str, marker: str) -> bool:
    return marker in source


def support_matrix(source: str) -> dict[str, dict[str, Any]]:
    matrix: dict[str, dict[str, Any]] = {}
    for name, spec in SERVICE_REQUIREMENTS.items():
        markers = {marker: marker_present(source, marker) for marker in spec["required_markers"]}
        matrix[name] = {
            "description": spec["description"],
            "supported": all(markers.values()),
            "markers": markers,
            "missing_markers": [marker for marker, present in markers.items() if not present],
        }
    return matrix


def get_child(v861: dict[str, Any], name: str) -> dict[str, Any]:
    children = (((v861.get("analysis") or {}).get("helper") or {}).get("children") or {})
    child = children.get(name) or {}
    return child if isinstance(child, dict) else {}


def evidence_summary(v861: dict[str, Any], v862: dict[str, Any], v863: dict[str, Any]) -> dict[str, Any]:
    helper = ((v861.get("analysis") or {}).get("helper") or {})
    return {
        "v861": {
            "decision": v861.get("decision", ""),
            "pass": v861.get("pass"),
            "property_denials_total": ((helper.get("property_denials") or {}).get("total")),
            "per_mgr_child": get_child(v861, "per_mgr"),
            "per_proxy_child": get_child(v861, "per_proxy"),
            "per_mgr_holds_subsys_esoc0": bool(helper.get("per_mgr_holds_subsys_esoc0")),
            "per_mgr_holds_subsys_modem": bool(helper.get("per_mgr_holds_subsys_modem")),
        },
        "v862": {
            "decision": v862.get("decision", ""),
            "pass": v862.get("pass"),
            "android_init_contract": v862.get("android_init_contract") or {},
            "gaps": v862.get("gaps") or {},
            "helper_contract": v862.get("helper_contract") or {},
        },
        "v863": {
            "decision": v863.get("decision", ""),
            "pass": v863.get("pass"),
            "service_contract": v863.get("service_contract") or {},
            "cleanup_ok": v863.get("cleanup_ok"),
        },
    }


def prerequisite_checks(v861: dict[str, Any], v862: dict[str, Any], v863: dict[str, Any], helper_source: str) -> list[dict[str, Any]]:
    return [
        {
            "name": "v861-domain-parity-evidence",
            "pass": v861.get("decision") == EXPECTED_V861_DECISION and bool(v861.get("pass")),
            "expected": EXPECTED_V861_DECISION,
            "actual": str(v861.get("decision", "")),
        },
        {
            "name": "v862-init-contract-evidence",
            "pass": v862.get("decision") == EXPECTED_V862_DECISION and bool(v862.get("pass")),
            "expected": EXPECTED_V862_DECISION,
            "actual": str(v862.get("decision", "")),
        },
        {
            "name": "v863-pm-proxy-helper-rc-evidence",
            "pass": v863.get("decision") == EXPECTED_V863_DECISION and bool(v863.get("pass")),
            "expected": EXPECTED_V863_DECISION,
            "actual": str(v863.get("decision", "")),
        },
        {
            "name": "helper-source-readable",
            "pass": bool(helper_source),
            "expected": str(DEFAULT_HELPER_SOURCE),
            "actual": "read" if helper_source else "missing",
        },
    ]


def implementation_gaps(matrix: dict[str, dict[str, Any]], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    v861 = evidence["v861"]
    v862_gaps = evidence["v862"].get("gaps") or {}
    v863_service = evidence["v863"].get("service_contract") or {}

    if v863_service.get("path") == "/vendor/bin/pm_proxy_helper" and not matrix["per_proxy_helper_child"]["supported"]:
        gaps.append({
            "name": "missing-per-proxy-helper-child-model",
            "source": "V863",
            "detail": "Android starts vendor.per_proxy_helper from post-fs-data, but helper source has no explicit child model.",
            "fix": "add a distinct per_proxy_helper child that runs /vendor/bin/pm_proxy_helper once and captures exit/fd/domain evidence",
        })
    if not matrix["per_proxy_helper_selinux_context"]["supported"]:
        gaps.append({
            "name": "missing-per-proxy-helper-selinux-context",
            "source": "helper-source",
            "detail": "default Android exec-context mapping covers pm-service/pm-proxy but not pm_proxy_helper.",
            "fix": "map /vendor/bin/pm_proxy_helper to the per_proxy_helper Android domain and record runtime attr/current",
        })
    if v862_gaps.get("per_mgr_ioprio_rt4_missing_in_helper") and not matrix["per_mgr_ioprio_rt4"]["supported"]:
        gaps.append({
            "name": "missing-per-mgr-ioprio-rt4",
            "source": "V862",
            "detail": "Android init gives vendor.per_mgr ioprio rt 4; helper has no ioprio_set model.",
            "fix": "call SYS_ioprio_set with realtime class 4 for the per_mgr child and record rc/errno",
        })
    if v862_gaps.get("per_proxy_property_lifecycle_not_modelled") and not matrix["per_proxy_property_start"]["supported"]:
        gaps.append({
            "name": "missing-per-proxy-property-lifecycle",
            "source": "V862",
            "detail": "Android starts vendor.per_proxy only after init.svc.vendor.per_mgr=running.",
            "fix": "spawn per_proxy only after per_mgr is observable/running and emit an init.svc vendor.per_mgr lifecycle marker",
        })
    if v862_gaps.get("per_proxy_shutdown_stop_not_modelled") and not matrix["per_proxy_shutdown_stop"]["supported"]:
        gaps.append({
            "name": "missing-per-proxy-shutdown-stop",
            "source": "V862",
            "detail": "Android stops vendor.per_proxy during sys.shutdown.requested handling.",
            "fix": "ensure bounded cleanup stops per_proxy explicitly and records shutdown-stop semantics without setting sys.shutdown.requested",
        })
    if v862_gaps.get("runtime_domain_still_kernel"):
        gaps.append({
            "name": "runtime-domain-still-kernel",
            "source": "V861",
            "detail": "V861 requested vendor_per_mgr exec targets but runtime attr/current stayed kernel.",
            "fix": "V865/V867 must keep recording target/current/exec contexts and block mdm_helper escalation if current stays kernel",
        })
    if not v861.get("per_mgr_holds_subsys_esoc0") or not v861.get("per_mgr_holds_subsys_modem"):
        gaps.append({
            "name": "subsystem-fd-hold-absent",
            "source": "V861",
            "detail": "pm-service did not hold /dev/subsys_esoc0 or /dev/subsys_modem under direct execution.",
            "fix": "V867 must prove whether init-equivalent PM lifecycle changes fd ownership before any mdm_helper/ks start",
        })
    return gaps


def decide(checks: list[dict[str, Any]], gaps: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    failed = [check for check in checks if not check["pass"]]
    if failed:
        return (
            "v864-prerequisite-evidence-missing",
            False,
            "missing prerequisite evidence: " + ", ".join(check["name"] for check in failed),
            "restore or regenerate V861/V862/V863 evidence before implementation",
        )
    if gaps:
        return (
            "v864-init-contract-wrapper-needed",
            True,
            "current helper does not yet model the complete Android PeripheralManager init contract",
            "implement V865 helper support; do not start new actors until build/static checks pass",
        )
    return (
        "v864-helper-support-already-complete-review-required",
        True,
        "no source-level contract gaps found; manual review required before live actor escalation",
        "write V867 live gate only after manually confirming helper support covers V862/V863 contracts",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    v861 = load_json(args.v861_manifest)
    v862 = load_json(args.v862_manifest)
    v863 = load_json(args.v863_manifest)
    helper_source = read_text(args.helper_source)
    matrix = support_matrix(helper_source)
    evidence = evidence_summary(v861, v862, v863)
    checks = prerequisite_checks(v861, v862, v863, helper_source)
    gaps = implementation_gaps(matrix, evidence)
    decision, pass_ok, reason, next_step = decide(checks, gaps)
    _, git_head = run_host(["git", "rev-parse", "--short", "HEAD"])
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "next_step": next_step,
        "inputs": {
            "v861_manifest": str(args.v861_manifest),
            "v862_manifest": str(args.v862_manifest),
            "v863_manifest": str(args.v863_manifest),
            "helper_source": str(args.helper_source),
        },
        "host": collect_host_metadata(),
        "git_head_checked": git_head.strip(),
        "prerequisite_checks": checks,
        "evidence_summary": evidence,
        "helper_support_matrix": matrix,
        "implementation_gaps": gaps,
        "v865_required_changes": [gap["fix"] for gap in gaps],
        "hard_gates": {
            "device_contact_executed": False,
            "helper_deploy_executed": False,
            "daemon_start_executed": False,
            "mdm_helper_start_executed": False,
            "ks_start_executed": False,
            "wifi_hal_start_executed": False,
            "scan_connect_executed": False,
            "credential_use_executed": False,
            "dhcp_route_executed": False,
            "external_ping_executed": False,
            "raw_esoc_ioctl_executed": False,
            "gpio_write_executed": False,
            "sysfs_write_executed": False,
            "debugfs_write_executed": False,
            "subsystem_write_executed": False,
            "module_load_unload_executed": False,
            "boot_or_partition_write_executed": False,
        },
    }


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        escaped = [str(cell).replace("|", "\\|").replace("\n", "<br>") for cell in row]
        lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(lines)


def write_outputs(out_dir: Path, manifest: dict[str, Any]) -> None:
    store = EvidenceStore(out_dir)
    store.write_json("manifest.json", manifest)
    support_rows = [
        [name, "yes" if item["supported"] else "no", ", ".join(item["missing_markers"])]
        for name, item in manifest["helper_support_matrix"].items()
    ]
    gap_rows = [
        [gap["name"], gap["source"], gap["fix"]]
        for gap in manifest["implementation_gaps"]
    ]
    check_rows = [
        [check["name"], "PASS" if check["pass"] else "FAIL", check["actual"]]
        for check in manifest["prerequisite_checks"]
    ]
    lines = [
        "# V864 PeripheralManager Init Contract Support",
        "",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next: {manifest['next_step']}",
        "",
        "## Prerequisites",
        "",
        markdown_table(["Check", "Result", "Actual"], check_rows),
        "",
        "## Helper Support Matrix",
        "",
        markdown_table(["Requirement", "Supported", "Missing Markers"], support_rows),
        "",
        "## Implementation Gaps",
        "",
        markdown_table(["Gap", "Source", "Required Fix"], gap_rows or [["none", "-", "manual review before live gate"]]),
        "",
        "## Guardrails",
        "",
    ]
    for name, value in manifest["hard_gates"].items():
        lines.append(f"- `{name}`: `{value}`")
    store.write_text("summary.md", "\n".join(lines) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v861-manifest", type=Path, default=DEFAULT_V861_MANIFEST)
    parser.add_argument("--v862-manifest", type=Path, default=DEFAULT_V862_MANIFEST)
    parser.add_argument("--v863-manifest", type=Path, default=DEFAULT_V863_MANIFEST)
    parser.add_argument("--helper-source", type=Path, default=DEFAULT_HELPER_SOURCE)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = repo_path(args.out_dir)
    manifest = build_manifest(args)
    write_outputs(out_dir, manifest)
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"manifest: {out_dir / 'manifest.json'}")
    print(f"summary: {out_dir / 'summary.md'}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
