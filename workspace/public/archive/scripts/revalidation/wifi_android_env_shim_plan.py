#!/usr/bin/env python3
"""Build a native Android-env shim plan for future CNSS experiments."""

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
DEFAULT_V217_NATIVE_MANIFEST = Path("tmp/wifi/v217-icnss-debug-recovery-inventory-native/manifest.json")
DEFAULT_V218_MANIFEST = Path("tmp/wifi/v218-cnss-daemon-dryrun/manifest.json")
DEFAULT_V218_NATIVE_MANIFEST = Path("tmp/wifi/v218-cnss-daemon-dryrun-native/manifest.json")

ACTIVE_PATTERNS = (
    re.compile(r"\b(?:cnss-daemon|cnss_diag|wificond|wpa_supplicant|hostapd)\b", re.IGNORECASE),
    re.compile(r"\bctl\.(?:start|restart)\b|\bclass_start\b", re.IGNORECASE),
    re.compile(r"\brfkill\s+(?:un)?block\b", re.IGNORECASE),
    re.compile(r"\bip\s+link\s+set\b.*\bup\b", re.IGNORECASE),
    re.compile(r"\biw\b.*\b(scan|connect|set)\b", re.IGNORECASE),
    re.compile(r">\s*/sys/", re.IGNORECASE),
    re.compile(r"\bmount\b|\bumount\b", re.IGNORECASE),
)

NO_DEVICE_COMMANDS: tuple[tuple[str, list[str]], ...] = ()


def default_out_dir() -> Path:
    return REPO_ROOT / "tmp" / "wifi" / "v219-native-android-env-shim"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=default_out_dir())
    parser.add_argument("--v216-manifest", type=Path, default=DEFAULT_V216_MANIFEST)
    parser.add_argument("--v217-native-manifest", type=Path, default=DEFAULT_V217_NATIVE_MANIFEST)
    parser.add_argument("--v218-manifest", type=Path, default=DEFAULT_V218_MANIFEST)
    parser.add_argument("--v218-native-manifest", type=Path, default=DEFAULT_V218_NATIVE_MANIFEST)
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


def service_names(v216: dict[str, Any]) -> set[str]:
    return {
        str(service.get("name"))
        for service in v216.get("graph", {}).get("services", [])
        if isinstance(service, dict) and service.get("name")
    }


def daemon_blockers(v218: dict[str, Any]) -> set[str]:
    blockers: set[str] = set()
    for daemon in v218.get("daemons", []):
        if isinstance(daemon, dict):
            blockers.update(str(blocker) for blocker in daemon.get("blockers", []))
    return blockers


def requirement(category: str,
                item: str,
                status: str,
                evidence: str,
                action: str,
                risk: str) -> dict[str, str]:
    return {
        "category": category,
        "item": item,
        "status": status,
        "evidence": evidence,
        "action": action,
        "risk": risk,
    }


def build_matrix(v216: dict[str, Any], v217_native: dict[str, Any], v218: dict[str, Any], v218_native: dict[str, Any]) -> list[dict[str, str]]:
    services = service_names(v216)
    blockers = daemon_blockers(v218)
    v218_decision = str(v218.get("decision", "missing"))
    v217_decision = str(v217_native.get("decision", "missing"))
    native_captures = v218_native.get("captures", [])
    native_ok = sum(1 for capture in native_captures if isinstance(capture, dict) and capture.get("ok"))

    rows = [
        requirement(
            "mount-path",
            "temporary read-only vendor visibility",
            "available",
            f"v218={v218_decision}; v210 binary visibility inherited",
            "use v209/v210 ro,noload model or host-visible vendor root; no persistent mount",
            "medium",
        ),
        requirement(
            "mount-path",
            "/system/vendor -> /vendor compatibility",
            "shim-required",
            "cnss-daemon executable is /system/vendor/bin/cnss-daemon",
            "later shim must provide path alias or explicit executable path translation",
            "medium",
        ),
        requirement(
            "mount-path",
            "host-visible vendor root for readelf",
            "host-evidence-required",
            "v218 blocker elf-inspection-no-host-vendor-root",
            "collect or mount vendor read-only on host/device before service experiment",
            "low",
        ),
        requirement(
            "property",
            "Android property service",
            "blocked",
            "v219 scope denies real property service recreation",
            "use static property manifest only; no setprop/ctl mutation",
            "high",
        ),
        requirement(
            "property",
            "init.svc service state model",
            "available",
            f"modeled services={','.join(sorted(services & {'cnss-daemon','cnss_diag'}))}",
            "use as evidence only; do not claim running native state",
            "low",
        ),
        requirement(
            "socket-ipc",
            "binder/hwbinder service publication",
            "out-of-scope",
            "CNSS daemon dry-run does not require publishing Wi-Fi HAL services",
            "do not start hwservicemanager/servicemanager in Wi-Fi bring-up path",
            "high",
        ),
        requirement(
            "socket-ipc",
            "QMI/PDR/SSR interaction",
            "blocked",
            f"v217={v217_decision}; reboot-only recovery blocker present={str('reboot-only-icnss-recovery-known' in blockers).lower()}",
            "do not write QMI/PDR/recovery controls before v221 opt-in plan",
            "high",
        ),
        requirement(
            "user-capability",
            "NET_ADMIN for cnss-daemon",
            "shim-required",
            "v216/v218 model shows NET_ADMIN",
            "later experiment must choose bounded root execution or native user/group emulation",
            "high",
        ),
        requirement(
            "user-capability",
            "Android groups system/inet/net_admin/wifi/diag",
            "shim-required",
            "v216/v210 service metadata includes Android groups",
            "map to root-only temporary execution or explicit group table; no persistent passwd/group mutation",
            "medium",
        ),
        requirement(
            "logging-evidence",
            "private daemon stdout/stderr logs",
            "shim-required",
            "future execution would be root-control evidence",
            "write under private 0700/0600 evidence directory",
            "medium",
        ),
        requirement(
            "logging-evidence",
            "before/after health bundle",
            "shim-required",
            f"v218 native read-only captures ok={native_ok}/{len(native_captures)}",
            "capture ICNSS, dmesg, netdev, rfkill, wiphy, mounts, firmware path, process state",
            "medium",
        ),
        requirement(
            "recovery-rollback",
            "ICNSS recovery if broken",
            "blocked",
            "v217 found state-only inventory and dangerous bind/unbind/driver_override",
            "treat reboot as only proven recovery path",
            "high",
        ),
        requirement(
            "recovery-rollback",
            "ACM/NCM rescue control",
            "available",
            "current workflow uses bridge/NCM fallback",
            "must verify before and after any later mutating experiment",
            "high",
        ),
        requirement(
            "security",
            "Wi-Fi credentials and /data/misc/wifi",
            "blocked",
            "pre-connect phases must avoid credential material",
            "do not collect or persist credentials; test AP policy deferred to v224",
            "high",
        ),
    ]
    return rows


def decide(matrix: list[dict[str, str]], v218: dict[str, Any]) -> tuple[str, str, bool]:
    if v218.get("decision") not in {"daemon-dryrun-ready", "daemon-dryrun-partial"}:
        return "manual-review-required", "v218 dry-run decision is not usable for shim planning", False
    statuses = {row["status"] for row in matrix}
    if "blocked" in statuses:
        return "shim-plan-partial", "bounded shim areas are mapped, but recovery/property/QMI blockers remain", True
    if "host-evidence-required" in statuses or "shim-required" in statuses:
        return "shim-plan-partial", "shim scope is bounded but additional host evidence and policy are required", True
    return "shim-plan-ready", "shim scope is bounded enough for v220 gate design", True


def build_summary(manifest: dict[str, Any]) -> str:
    rows = [
        [row["category"], row["item"], row["status"], row["action"], row["risk"]]
        for row in manifest["shim_matrix"]
    ]
    lines = [
        "# v219 Native Android-Env Shim Plan",
        "",
        f"- generated: `{manifest['created']}`",
        f"- result: `{'PASS' if manifest['pass'] else 'FAIL'}`",
        f"- decision: `{manifest['decision']}`",
        f"- reason: `{manifest['reason']}`",
        "",
        "## Shim Matrix",
        "",
        markdown_table(["category", "item", "status", "action", "risk"], rows),
        "",
        "## Allow List",
        "",
    ]
    lines.extend(f"- {item}" for item in manifest["allow_list"])
    lines.extend(["", "## Deny List", ""])
    lines.extend(f"- {item}" for item in manifest["deny_list"])
    lines.extend([
        "",
        "## Interpretation",
        "",
        "- This plan does not approve daemon execution.",
        "- v220 can consume the matrix as preflight gate input.",
        "- Active CNSS/Wi-Fi work remains blocked until later explicit opt-in gates.",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    validate_no_active_commands()
    out_dir = repo_path(args.out_dir)
    store = EvidenceStore(out_dir)

    v216 = load_json(args.v216_manifest)
    v217_native = load_json(args.v217_native_manifest)
    v218 = load_json(args.v218_manifest)
    v218_native = load_json(args.v218_native_manifest)
    matrix = build_matrix(v216, v217_native, v218, v218_native)
    decision, reason, pass_ok = decide(matrix, v218)

    manifest = {
        "created": dt.datetime.now(dt.timezone.utc).isoformat(),
        "pass": pass_ok,
        "decision": decision,
        "reason": reason,
        "inputs": {
            "v216_manifest": str(repo_path(args.v216_manifest)),
            "v217_native_manifest": str(repo_path(args.v217_native_manifest)),
            "v218_manifest": str(repo_path(args.v218_manifest)),
            "v218_native_manifest": str(repo_path(args.v218_native_manifest)),
        },
        "shim_matrix": matrix,
        "allow_list": [
            "temporary read-only vendor visibility",
            "host-side readelf/library inspection on private evidence copy",
            "static property manifest modeling",
            "private daemon stdout/stderr evidence path in future opt-in experiment",
            "before/after read-only ICNSS/netdev/rfkill/wiphy/dmesg captures",
            "ACM/NCM rescue channel validation",
        ],
        "deny_list": [
            "daemon execution in v219",
            "Android property mutation",
            "ctl.start or class_start",
            "binder/hwbinder service publication",
            "writable vendor/system/data mount",
            "ICNSS bind/unbind/driver_override",
            "rfkill write, link-up, scan, connect",
            "credential collection from /data/misc/wifi",
        ],
        "source_decisions": {
            "v216": v216.get("decision"),
            "v217_native": v217_native.get("decision"),
            "v218": v218.get("decision"),
            "v218_native": v218_native.get("decision"),
        },
        "host_metadata": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_json("shim-matrix.json", {"shim_matrix": matrix})
    store.write_text("summary.md", build_summary(manifest))
    print(f"{'PASS' if pass_ok else 'FAIL'} out_dir={out_dir} decision={decision} reason={reason}")
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
