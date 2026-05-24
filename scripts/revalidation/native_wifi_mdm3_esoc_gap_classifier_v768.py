#!/usr/bin/env python3
"""V768 host-only mdm3/esoc gap classifier.

V767 proved the ICNSS/QCACLD instrumentation patch compiles to the target object
boundary, while final Image packaging is blocked by a Samsung RKP_CFP Python2
post-link step. V768 reconciles that with the V620/V622/V740/V764 mdm_helper and
esoc evidence. It does not contact the device, start services, write subsystem
state, build a boot image, or use Wi-Fi credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v768-mdm3-esoc-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v768-mdm3-esoc-gap-classifier.txt")

INPUTS = {
    "v620": Path("tmp/wifi/v620-dsp-mdm3-safety-classifier-current-request-20260523/manifest.json"),
    "v622": Path("tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/manifest.json"),
    "v740": Path("tmp/wifi/v740-mdm-helper-baseband-contract/manifest.json"),
    "v764": Path("tmp/wifi/v764-mdm-helper-service180-retry/manifest.json"),
    "v767": Path("tmp/wifi/v767-icnss-qcacld-full-build/manifest.json"),
}

REPORTS = {
    "v620": Path("docs/reports/NATIVE_INIT_V620_DSP_MDM3_SAFETY_CLASSIFIER_2026-05-23.md"),
    "v622": Path("docs/reports/NATIVE_INIT_V622_ANDROID_MDM_HELPER_TIMING_RECAPTURE_LIVE_2026-05-23.md"),
    "v740": Path("docs/reports/NATIVE_INIT_V740_MDM_HELPER_BASEBAND_CONTRACT_2026-05-24.md"),
    "v764": Path("docs/reports/NATIVE_INIT_V764_SERVICE180_MDM_HELPER_RETRY_2026-05-24.md"),
    "v767": Path("docs/reports/NATIVE_INIT_V767_ICNSS_QCACLD_FULL_BUILD_2026-05-25.md"),
}


@dataclass(frozen=True)
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
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "error": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "error": "not-json-object"}
    data["exists"] = True
    data["path"] = str(resolved)
    return data


def get_check(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in manifest.get("checks", []):
        if check.get("name") == name:
            return check if isinstance(check, dict) else {}
    return {}


def get_detail(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    check = get_check(manifest, name)
    detail = check.get("detail")
    return detail if isinstance(detail, dict) else {}


def add_check(checks: list[Check], name: str, status: str, severity: str, detail: str, next_step: str) -> None:
    checks.append(Check(name, status, severity, detail, next_step))


def summarize_inputs(inputs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for name, manifest in inputs.items():
        summary[name] = {
            "path": manifest.get("path"),
            "exists": manifest.get("exists", False),
            "decision": manifest.get("decision", ""),
            "pass": bool(manifest.get("pass")),
            "reason": manifest.get("reason", ""),
            "next_step": manifest.get("next_step", ""),
        }
    return summary


def classify(args: argparse.Namespace) -> dict[str, Any]:
    inputs = {name: load_json(path) for name, path in INPUTS.items()}
    v764 = inputs["v764"]
    v767 = inputs["v767"]
    v764_progression = get_detail(v764, "mdm3-wlanpd-mhi-progression")
    v764_gate = get_detail(v764, "service180-gate")
    v764_access = v764.get("v764_access") if isinstance(v764.get("v764_access"), dict) else {}
    v767_objects = (v767.get("analysis") or {}).get("instrumented_objects") or {}
    v767_failure = (v767.get("analysis") or {}).get("build_failure") or {}

    analysis: dict[str, Any] = {
        "inputs": summarize_inputs(inputs),
        "reports": {
            name: {
                "path": str(repo_path(path)),
                "exists": repo_path(path).exists(),
            }
            for name, path in REPORTS.items()
        },
        "v764_runtime": {
            "service180_gate_open": int(v764_gate.get("gate_open") or 0),
            "mdm_helper_started": int(v764_gate.get("mdm_helper_child_started") or 0),
            "markers": v764_progression.get("markers") or {},
            "lower": v764_progression.get("lower") or {},
            "access": v764_access,
            "esoc0_open_executed": bool(v764.get("esoc0_open_executed")),
            "esoc0_hold_executed": bool(v764.get("esoc0_hold_executed")),
            "subsystem_writes_executed": bool(v764.get("subsystem_writes_executed")),
        },
        "v767_instrumentation": {
            "decision": v767.get("decision", ""),
            "objects_all_exist": bool(v767_objects.get("all_exist")),
            "marker_total": int(v767_objects.get("marker_total") or 0),
            "first_error": v767_failure.get("first_error", ""),
        },
        "candidate_matrix": [],
        "forbidden_executed": {
            "device_commands": False,
            "service_manager": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credential_use": False,
            "dhcp_route": False,
            "external_ping": False,
            "boot_or_partition_write": False,
            "esoc0_open": False,
            "subsystem_write": False,
        },
    }

    v764_markers = analysis["v764_runtime"]["markers"]
    lower = analysis["v764_runtime"]["lower"]
    qmi_absent = int(v764_markers.get("wlfw") or 0) == 0 and int(v764_markers.get("bdf") or 0) == 0
    mdm3_values = lower.get("mdm3") if isinstance(lower, dict) else []
    mdm3_stuck = isinstance(mdm3_values, list) and mdm3_values and all(value == "OFFLINING" for value in mdm3_values)
    esoc_devnode_visible = bool(v764_access.get("esoc_devnode_visible"))

    analysis["candidate_matrix"] = [
        {
            "candidate": "repeat service180-gated mdm_helper",
            "classification": "reject",
            "reason": "V764 already started mdm_helper below service180 with mdm3/WLFW/BDF/wlan0 unchanged",
        },
        {
            "candidate": "raw esoc0 open or hold",
            "classification": "reject",
            "reason": "/dev/subsys_esoc0 is absent and no init-visible raw esoc0 contract was proven",
        },
        {
            "candidate": "subsystem state write or bind/unbind",
            "classification": "forbidden",
            "reason": "prior policy rejects subsystem writes and generic bind/unbind for this Wi-Fi blocker",
        },
        {
            "candidate": "repeat lower-window boot_wlan without new observability",
            "classification": "reject",
            "reason": "V750/V752 already reaches HDD/qcwlanstate but not driver-loaded/QMI/FW-ready",
        },
        {
            "candidate": "ICNSS/QCACLD instrumentation packaging",
            "classification": "select-next",
            "reason": "V767 proves target objects compile; the next blocker is RKP_CFP Python2 packaging before diagnostic boot-image handoff",
        },
    ]

    analysis["derived"] = {
        "mdm_helper_started_no_lower_progress": (
            analysis["v764_runtime"]["service180_gate_open"] == 1
            and analysis["v764_runtime"]["mdm_helper_started"] == 1
            and mdm3_stuck
            and qmi_absent
        ),
        "direct_esoc0_path_unavailable": not esoc_devnode_visible,
        "instrumentation_compile_proven": (
            analysis["v767_instrumentation"]["objects_all_exist"]
            and analysis["v767_instrumentation"]["marker_total"] == 19
        ),
        "rkp_cfp_packaging_blocker": "SyntaxError" in analysis["v767_instrumentation"]["first_error"],
    }
    return analysis


def build_checks(manifest: dict[str, Any]) -> list[Check]:
    analysis = manifest["analysis"]
    inputs = analysis["inputs"]
    checks: list[Check] = []
    expected_decisions = {
        "v620": "v620-esoc0-notifier-causality-refined",
        "v622": "v622-mdm-helper-post-notifier-not-root-trigger",
        "v740": "v740-mdm-helper-post-notifier-gated-proof-selected",
        "v764": "v764-mdm-helper-started-no-lower-progress",
        "v767": "v767-instrumented-objects-built-rkp-cfp-python2-blocked",
    }
    for name, expected in expected_decisions.items():
        item = inputs[name]
        add_check(
            checks,
            f"{name}-input",
            "pass" if item.get("exists") and item.get("pass") and item.get("decision") == expected else "blocked",
            "blocker",
            f"decision={item.get('decision')} pass={item.get('pass')} expected={expected}",
            f"rerun or refresh {name} evidence before using V768",
        )
    derived = analysis["derived"]
    add_check(
        checks,
        "mdm-helper-repeatability",
        "pass" if derived["mdm_helper_started_no_lower_progress"] else "blocked",
        "blocker",
        f"started_no_lower_progress={derived['mdm_helper_started_no_lower_progress']}",
        "do not close mdm_helper retry unless V764 proves start plus no lower progress",
    )
    add_check(
        checks,
        "direct-esoc0-safety",
        "pass" if derived["direct_esoc0_path_unavailable"] else "warn",
        "warn",
        f"direct_esoc0_path_unavailable={derived['direct_esoc0_path_unavailable']}",
        "keep raw esoc0 open/hold blocked unless a safer contract appears",
    )
    add_check(
        checks,
        "instrumentation-compile",
        "pass" if derived["instrumentation_compile_proven"] else "blocked",
        "blocker",
        f"markers=19 objects={derived['instrumentation_compile_proven']}",
        "fix V767 object compile before selecting packaging branch",
    )
    add_check(
        checks,
        "rkp-cfp-packaging-blocker",
        "pass" if derived["rkp_cfp_packaging_blocker"] else "warn",
        "warn",
        f"rkp_cfp_packaging_blocker={derived['rkp_cfp_packaging_blocker']}",
        "classify final image packaging separately from runtime mdm3/esoc branch",
    )
    return checks


def blocking(checks: list[Check]) -> list[str]:
    return [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]


def decide(command: str, checks: list[Check]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v768-mdm3-esoc-gap-classifier-plan-ready",
            True,
            "plan-only; no device command, service start, subsystem write, build, or boot image action executed",
            "run V768 host-only classifier",
        )
    blockers = blocking(checks)
    if blockers:
        return (
            "v768-mdm3-esoc-gap-classifier-blocked",
            False,
            "blocked by " + ", ".join(blockers),
            "refresh missing prerequisite evidence before choosing next Wi-Fi gate",
        )
    return (
        "v768-mdm3-esoc-gap-rerouted-to-instrumentation-packaging",
        True,
        "mdm_helper/esoc direct retry is no longer the best next step; V767 instrumentation packaging is the nearest diagnostic gate",
        "V769 should solve RKP_CFP/Python2 packaging or explicitly bypass it for a diagnostic image before any flash/live handoff",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    return "\n".join([
        "# V768 MDM3/ESOC Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- boot_or_partition_write_executed: `{manifest['boot_or_partition_write_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- credential_use_executed: `{manifest['credential_use_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [
            [check["name"], check["status"], check["severity"], check["detail"], check["next_step"]]
            for check in manifest["checks"]
        ]),
        "",
        "## Candidate Matrix",
        "",
        markdown_table(["candidate", "classification", "reason"], [
            [row["candidate"], row["classification"], row["reason"]]
            for row in analysis["candidate_matrix"]
        ]),
        "",
        "## Derived Signals",
        "",
        markdown_table(["signal", "value"], [[key, value] for key, value in analysis["derived"].items()]),
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    analysis = classify(args)
    manifest: dict[str, Any] = {
        "cycle": "v768",
        "generated_at": now_iso(),
        "command": args.command,
        "analysis": analysis,
        "device_commands_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
        "esoc0_open_executed": False,
        "subsystem_write_executed": False,
        "host": collect_host_metadata(),
    }
    checks = build_checks(manifest)
    decision, ok, reason, next_step = decide(args.command, checks)
    manifest.update({
        "checks": [asdict(check) for check in checks],
        "decision": decision,
        "pass": ok,
        "reason": reason,
        "next_step": next_step,
    })
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path(Path(".")))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"boot_or_partition_write_executed: {manifest['boot_or_partition_write_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
