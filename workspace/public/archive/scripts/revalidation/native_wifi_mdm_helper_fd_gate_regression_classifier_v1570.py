#!/usr/bin/env python3
"""V1570 host-only classifier for the service-window mdm_helper /dev/esoc-0 fd gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1570-mdm-helper-fd-gate-classifier"
DEFAULT_REPORT = REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1570_MDM_HELPER_FD_GATE_CLASSIFIER_2026-06-02.md"
DEFAULT_V1569 = REPO_ROOT / "tmp" / "wifi" / "v1569-service-window-result-handoff" / "manifest.json"
INPUTS = {
    "android_mdm_helper_strace_v1158": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1158_ANDROID_MDM_HELPER_EXTENDED_STRACE_CAPTURE_2026-05-27.md",
    "native_reduced_positive_v1228": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1228_MDM_HELPER_EARLY_COMPACT_TRACE_LIVE_2026-05-31.md",
    "service_window_prior_negative_v1008": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1008_SERVICE_WINDOW_FD_POLL_LIVE_2026-05-26.md",
    "service_window_delta_v1009": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1009_V911_V1008_CONTRACT_COMPARATOR_2026-05-26.md",
    "current_v1569_report": REPO_ROOT / "docs" / "reports" / "NATIVE_INIT_V1569_SERVICE_WINDOW_RESULT_HANDOFF_2026-06-02.md",
    "helper_source": REPO_ROOT / "stage3" / "linux_init" / "helpers" / "a90_android_execns_probe.c",
}


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def contains(path: Path, needle: str) -> bool:
    return needle in read_text(path)


def classify(args: argparse.Namespace) -> dict[str, Any]:
    v1569 = load_json(args.v1569_manifest)
    progress = v1569.get("wifi_progress", {})
    checks: dict[str, Any] = {
        "v1569_handoff_and_rollback_ok": bool(v1569.get("handoff_pass") and v1569.get("rollback", {}).get("ok")),
        "v1569_result_file_seen": bool(progress.get("helper_result_file_seen")),
        "v1569_contract_seen": bool(progress.get("helper_result_contract_seen")),
        "v1569_no_esoc_fd": progress.get("helper_result_mdm_helper_esoc0_fd_count") == "0",
        "v1569_trigger_not_attempted": progress.get("helper_result_final_result") == "subsys-trigger-not-attempted-no-mdm-helper-esoc-fd",
        "android_v1158_mdm_helper_esoc_fd": contains(INPUTS["android_mdm_helper_strace_v1158"], 'openat(..., "/dev/esoc-0", O_RDONLY|O_NONBLOCK) = 5') and contains(INPUTS["android_mdm_helper_strace_v1158"], "fd 5:    /dev/esoc-0"),
        "native_v1228_mdm_helper_esoc_fd": contains(INPUTS["native_reduced_positive_v1228"], "max `/dev/esoc-0` fd count | `1`") and contains(INPUTS["native_reduced_positive_v1228"], "ESOC_WAIT_FOR_REQ"),
        "prior_service_window_same_negative": contains(INPUTS["service_window_prior_negative_v1008"], "subsys-trigger-not-attempted-no-mdm-helper-esoc-fd") and contains(INPUTS["service_window_prior_negative_v1008"], "mdm_helper_esoc0_fd_count: 0"),
        "prior_delta_positive_vs_negative": contains(INPUTS["service_window_delta_v1009"], "window=1 final=1") and contains(INPUTS["service_window_delta_v1009"], "seen=0 max=0"),
        "helper_has_service_window_route": contains(INPUTS["helper_source"], "run_wifi_companion_android_wifi_service_window_guarded"),
        "helper_has_mdm_helper_positive_modes": contains(INPUTS["helper_source"], "wifi-companion-mdm-helper-runtime-contract-capture") and contains(INPUTS["helper_source"], "wifi-companion-mdm-helper-cnss-before-subsys-trigger-capture"),
    }
    required = all(checks.values())
    decision = "v1570-select-mdm-helper-launch-contract-delta" if required else "v1570-mdm-helper-fd-gate-classifier-blocked"
    reason = (
        "V1569 reproduces the service-window no-fd gate with complete result output while Android and reduced native paths prove mdm_helper can hold /dev/esoc-0; next work should compare mdm_helper launch contract, not retry RC1 or Wi-Fi connect"
        if required else
        "Missing evidence for the mdm_helper fd-gate delta; inspect inputs before planning another live gate"
    )
    next_gate = (
        "V1571 source/build-only: add a service-window mdm_helper launch-contract comparator that records mdm_helper argv/env/properties/dev-node/context, compares against known positive mdm-helper modes, and only then decides whether to start a bounded live fd acquisition gate"
        if required else
        "Repair missing host evidence before selecting a live gate"
    )
    return {
        "cycle": "V1570",
        "decision": decision,
        "pass": required,
        "reason": reason,
        "inputs": {name: rel(path) for name, path in INPUTS.items()},
        "v1569_manifest": rel(args.v1569_manifest),
        "checks": checks,
        "next_gate": next_gate,
        "safety": {
            "host_only": True,
            "device_command": False,
            "flash": False,
            "partition_write": False,
            "wifi_scan_connect": False,
            "credentials": False,
            "dhcp_routes_external_ping": False,
            "pmic_gpio_gdsc_write": False,
            "esoc_notify_boot_done": False,
            "global_pci_rescan": False,
            "platform_bind_unbind": False,
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    lines = [
        "# Native Init V1570 MDM Helper FD Gate Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1570`",
        "- Type: host-only mdm_helper fd-gate regression classifier",
        f"- Decision: `{result['decision']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inputs",
        "",
    ]
    for name, path in result["inputs"].items():
        lines.append(f"- `{name}`: `{path}`")
    lines.extend([
        f"- `v1569_manifest`: `{result['v1569_manifest']}`",
        "",
        "## Checks",
        "",
    ])
    for key, value in checks.items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend([
        "",
        "## Interpretation",
        "",
        "V1569 is not an RC1/LTSSM failure in the active service-window route. It is a pre-RC1 fd-gate failure: `mdm_helper` starts but does not hold `/dev/esoc-0`, so the reviewed scoped `/dev/subsys_esoc0` trigger is not attempted.",
        "",
        "This is a known delta rather than a one-off: Android V1158 and reduced native V1228 prove `/dev/esoc-0` ownership is achievable, while V1008/V1009 and V1569 show the Android service-window route still misses that ownership predicate.",
        "",
        "## Next Gate",
        "",
        result["next_gate"],
        "",
        "## Safety Scope",
        "",
        "This classifier is host-only. It performs no device command, flash, reboot, partition write, Wi-Fi scan/connect, credential handling, DHCP/routes, external ping, PMIC/GPIO/GDSC write, blind eSoC notify/`BOOT_DONE` spoof, global PCI rescan, or platform bind/unbind.",
        "",
    ])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1569-manifest", type=Path, default=DEFAULT_V1569)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    result = classify(args)
    result["out_dir"] = rel(args.out_dir)
    store.write_json("manifest.json", result)
    write_private_text(args.report_path, render_report(result))
    print(json.dumps({"decision": result["decision"], "pass": result["pass"], "out_dir": rel(args.out_dir)}, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
