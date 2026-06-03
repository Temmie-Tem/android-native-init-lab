#!/usr/bin/env python3
"""V1854 fail-closed wrapper for the future SDX50M bridge gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CYCLE = "V1854"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1854-sdx50m-bridge-fail-closed-wrapper"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1854_SDX50M_BRIDGE_FAIL_CLOSED_WRAPPER_2026-06-03.md"
)
V1852_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1852-sdx50m-bridge-gate-scaffold"
    / "manifest.json"
)
V1853_MANIFEST = (
    REPO_ROOT
    / "tmp"
    / "wifi"
    / "v1853-sdx50m-bridge-image-readiness"
    / "manifest.json"
)


FORBIDDEN_ACTIONS = (
    "device_command",
    "flash",
    "reboot",
    "stage_properties",
    "start_actors",
    "direct_subsys_esoc0_open",
    "boot_wlan",
    "restart_pd_request",
    "force_rc1",
    "fake_online",
    "pmic_gpio_gdsc_write",
    "esoc_ioctl_notify",
    "boot_done_spoof",
    "pci_rescan",
    "platform_bind_unbind",
    "wifi_hal_start",
    "scan_connect",
    "credential_use",
    "dhcp_route",
    "external_ping",
)


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"missing input manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("dry-run", "live"),
        default="dry-run",
        help="Only dry-run is supported in V1854. live is intentionally fail-closed.",
    )
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def collect_inputs() -> dict[str, Any]:
    v1852 = load_json(V1852_MANIFEST)
    v1853 = load_json(V1853_MANIFEST)
    readiness = (v1853.get("details") or {}).get("v1846_image") or {}
    handoff = (v1853.get("details") or {}).get("v1847_handoff") or {}
    scaffold = (v1853.get("details") or {}).get("v1852_scaffold") or {}
    scaffold_spec = ((v1852.get("details") or {}).get("scaffold_spec") or {})
    return {
        "v1852": {
            "path": rel(V1852_MANIFEST),
            "decision": v1852.get("decision", ""),
            "label": v1852.get("label", ""),
            "pass": bool(v1852.get("pass")),
            "mode": scaffold_spec.get("mode", ""),
            "live_execution_implemented": bool(scaffold_spec.get("live_execution_implemented")),
            "promotion_rule": scaffold_spec.get("future_gate_promotion_rule", ""),
        },
        "v1853": {
            "path": rel(V1853_MANIFEST),
            "decision": v1853.get("decision", ""),
            "label": v1853.get("label", ""),
            "pass": bool(v1853.get("pass")),
            "boot_image": readiness.get("boot_image", ""),
            "boot_sha256_ok": bool(readiness.get("boot_sha256_ok")),
            "helper_marker": readiness.get("helper_marker", ""),
            "baseline_path": handoff.get("open_context_path", ""),
            "baseline_lower_mdm3": handoff.get("lower_mdm3_states", ""),
            "baseline_service69": bool(handoff.get("lower_service69_progress")),
            "baseline_wlan0": bool(handoff.get("lower_wlan0_present")),
            "scaffold_label": scaffold.get("label", ""),
        },
    }


def wrapper_contract(requested_mode: str) -> dict[str, Any]:
    return {
        "cycle": CYCLE,
        "requested_mode": requested_mode,
        "supported_modes": ["dry-run"],
        "live_mode_supported": False,
        "requires_new_cycle_for_live": True,
        "implemented_live_runner": False,
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "executed_actions": {action: False for action in FORBIDDEN_ACTIONS},
        "promotion_requirements": [
            "WLFW service 69 observed",
            "wlan0 observed",
            "rollback verified to v724",
            "no credential, DHCP, route, or external ping before lower publication",
        ],
        "dry_run_outputs": [
            "input readiness check",
            "fail-closed live denial check",
            "next candidate selection",
        ],
    }


def classify(inputs: dict[str, Any], contract: dict[str, Any]) -> tuple[str, str, str, bool, int]:
    requested_mode = contract["requested_mode"]
    no_actions = not any(contract["executed_actions"].values())
    inputs_ready = (
        inputs["v1852"]["pass"]
        and inputs["v1852"]["label"] == "sdx50m-bridge-gate-scaffold-dry-run-ready"
        and inputs["v1852"]["mode"] == "dry-run-only"
        and not inputs["v1852"]["live_execution_implemented"]
        and inputs["v1853"]["pass"]
        and inputs["v1853"]["label"] == "bridge-test-image-ready-no-rebuild"
        and inputs["v1853"]["boot_sha256_ok"]
        and inputs["v1853"]["baseline_path"] == "/dev/subsys_modem"
        and inputs["v1853"]["baseline_lower_mdm3"] == "OFFLINING"
        and not inputs["v1853"]["baseline_service69"]
        and not inputs["v1853"]["baseline_wlan0"]
    )
    if requested_mode != "dry-run":
        return (
            "live-mode-denied",
            "v1854-live-mode-denied-fail-closed",
            "V1854 intentionally has no live runner; a later reviewed cycle must add live execution explicitly",
            False,
            2,
        )
    if not no_actions:
        return (
            "forbidden-action-review",
            "v1854-forbidden-action-review",
            "Wrapper contract claims a forbidden action was executed",
            False,
            1,
        )
    if not inputs_ready:
        return (
            "input-readiness-review",
            "v1854-input-readiness-review",
            "V1852/V1853 readiness inputs are missing or no longer match dry-run assumptions",
            False,
            1,
        )
    return (
        "sdx50m-bridge-wrapper-fail-closed-ready",
        "v1854-sdx50m-bridge-wrapper-fail-closed-ready-host-pass",
        "Fail-closed wrapper is ready: only dry-run is supported, live mode is denied, and Wi-Fi connect remains blocked until WLFW service 69 and wlan0 are observed",
        True,
        0,
    )


def render_report(result: dict[str, Any]) -> str:
    inputs = result["details"]["inputs"]
    contract = result["details"]["contract"]
    return "\n".join([
        "# Native Init V1854 SDX50M Bridge Fail-Closed Wrapper",
        "",
        "## Summary",
        "",
        f"- Cycle: `{CYCLE}`",
        "- Type: host-only fail-closed wrapper for a future SDX50M bridge gate",
        f"- Requested mode: `{contract['requested_mode']}`",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Inputs",
        "",
        f"- V1852: `{inputs['v1852']['decision']}` / `{inputs['v1852']['label']}` mode `{inputs['v1852']['mode']}`",
        f"- V1853: `{inputs['v1853']['decision']}` / `{inputs['v1853']['label']}` boot_sha_ok `{inputs['v1853']['boot_sha256_ok']}`",
        f"- baseline path/lower: `{inputs['v1853']['baseline_path']}` / `{inputs['v1853']['baseline_lower_mdm3']}` / service69 `{inputs['v1853']['baseline_service69']}` / wlan0 `{inputs['v1853']['baseline_wlan0']}`",
        "",
        "## Fail-Closed Contract",
        "",
        f"- supported modes: `{contract['supported_modes']}`",
        f"- live supported / implemented: `{contract['live_mode_supported']}` / `{contract['implemented_live_runner']}`",
        f"- requires new cycle for live: `{contract['requires_new_cycle_for_live']}`",
        f"- forbidden actions: `{contract['forbidden_actions']}`",
        f"- executed actions: `{contract['executed_actions']}`",
        f"- promotion requirements: `{contract['promotion_requirements']}`",
        "",
        "## Interpretation",
        "",
        "- V1854 is deliberately not a live SDX50M run. It makes accidental live promotion impossible in this unit.",
        "- Passing V1854 means the next code path remains dry-run-only; `--mode live` is a negative test and must fail closed.",
        "- Wi-Fi connect and ping remain blocked until lower publication proves WLFW service 69 and `wlan0` exist.",
        "",
        "## Safety Scope",
        "",
        "Host-only. This wrapper did not issue live device commands, flash, reboot, stage properties, start actors, open `/dev/subsys_esoc0`, start `boot_wlan`, issue restart-PD request, force RC1, fake ONLINE state, write PMIC/GPIO/GDSC controls, perform eSoC notify, BOOT_DONE spoof, PCI rescan, platform bind/unbind, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, or external ping.",
        "",
        "## Next",
        "",
        "- Do not proceed to Wi-Fi HAL/scan/connect unless WLFW service 69 and `wlan0` are present.",
        "- Next candidate is a separately reviewed live-gate design delta, not a hidden switch in this wrapper.",
        "",
    ])


def write_outputs(out_dir: Path, report_path: Path, result: dict[str, Any]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    result["out_dir"] = rel(out_dir)
    result["report"] = rel(report_path)
    (out_dir / "manifest.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(render_report(result), encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = args.out_dir if args.out_dir.is_absolute() else REPO_ROOT / args.out_dir
    report_path = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    inputs = collect_inputs()
    contract = wrapper_contract(args.mode)
    label, decision, reason, passed, rc = classify(inputs, contract)
    result = {
        "cycle": CYCLE,
        "decision": decision,
        "label": label,
        "pass": passed,
        "reason": reason,
        "out_dir": rel(out_dir),
        "report": rel(report_path),
        "details": {
            "inputs": inputs,
            "contract": contract,
        },
    }
    write_outputs(out_dir, report_path, result)
    print(json.dumps({key: result[key] for key in ("decision", "label", "pass", "reason", "out_dir", "report")}, indent=2))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
