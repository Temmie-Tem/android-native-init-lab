#!/usr/bin/env python3
"""V1871 host-only reconciliation after rollbackable private SDX50M mount."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / ".git").exists())
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1871-private-mount-pm-vote-reconcile"
DEFAULT_REPORT_PATH = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1871_PRIVATE_MOUNT_PM_VOTE_RECONCILE_2026-06-03.md"
)
DEFAULT_V1870 = REPO_ROOT / "tmp" / "wifi" / "v1870-sdx50m-private-mount-summary-handoff" / "manifest.json"
DEFAULT_V1755 = REPO_ROOT / "tmp" / "wifi" / "v1755-wlan-pd-pm-vote-contract-classifier" / "manifest.json"
DEFAULT_V1753 = REPO_ROOT / "tmp" / "wifi" / "v1753-android-good-wlan-pd-firmware-request" / "manifest.json"
DEFAULT_V1736 = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"_exists": False, "_path": rel(path)}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"_exists": True, "_path": rel(path), "_json_error": str(exc)}
    if not isinstance(data, dict):
        return {"_exists": True, "_path": rel(path), "_json_error": "top-level JSON is not an object"}
    data["_exists"] = True
    data["_path"] = rel(path)
    return data


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "pass", "ok"}
    return False


def as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def summarize_v1870(manifest: dict[str, Any]) -> dict[str, Any]:
    gate = manifest.get("gate") if isinstance(manifest.get("gate"), dict) else {}
    post = manifest.get("post_rollback_verification") if isinstance(manifest.get("post_rollback_verification"), dict) else {}
    rollback = manifest.get("rollback") if isinstance(manifest.get("rollback"), dict) else {}
    return {
        "exists": as_bool(manifest.get("_exists")),
        "decision": as_text(manifest.get("decision")),
        "pass": as_bool(manifest.get("pass")),
        "rollback_ok": as_bool(rollback.get("ok")),
        "post_version_ok": as_bool(post.get("version_ok")),
        "post_selftest_fail_zero": as_bool(post.get("selftest_fail_zero")),
        "private_mount_label": as_text(gate.get("private_mount_label")),
        "private_cnss_contract_ok": as_bool(gate.get("private_cnss_contract_ok")),
        "private_cnss_bind_rc": as_text(gate.get("private_cnss_bind_rc")),
        "pm_client_register_rc": as_text(gate.get("pm_client_register_rc")),
        "pm_client_connect_rc": as_text(gate.get("pm_client_connect_rc")),
        "requested_wlanmdsp": as_text(gate.get("requested_wlanmdsp")),
        "wlfw_service69_seen": as_text(gate.get("wlfw_service69_seen")),
        "wlan0_present": as_text(gate.get("wlan0_present")),
        "raw_wlan_pd_positive": as_bool(gate.get("raw_wlan_pd_text_positive")),
        "lower_service69_progress": as_bool(gate.get("lower_service69_progress")),
        "lower_wlan0_present": as_bool(gate.get("lower_wlan0_present")),
        "safety_ok": as_bool(gate.get("safety_ok")),
    }


def summarize_v1755(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "exists": as_bool(manifest.get("_exists")),
        "decision": as_text(manifest.get("decision")),
        "pass": as_bool(manifest.get("pass")),
        "label": as_text(manifest.get("label")),
        "reason": as_text(manifest.get("reason")),
    }


def summarize_v1753(manifest: dict[str, Any]) -> dict[str, Any]:
    context = manifest.get("context") if isinstance(manifest.get("context"), dict) else {}
    context_analysis = context.get("analysis") if isinstance(context.get("analysis"), dict) else {}
    analysis = manifest.get("analysis") if isinstance(manifest.get("analysis"), dict) else context_analysis
    firmware = manifest.get("firmware_request_analysis") if isinstance(manifest.get("firmware_request_analysis"), dict) else {}
    source = firmware or analysis
    return {
        "exists": as_bool(manifest.get("_exists")),
        "decision": as_text(manifest.get("decision")),
        "pass": as_bool(manifest.get("pass")),
        "requested_wlanmdsp": as_text(source.get("requested_wlanmdsp")),
        "requested_pd_image": as_text(source.get("requested_pd_image")),
        "wlfw_seen": as_text(source.get("wlfw_seen") or source.get("wlfw_lines")),
    }


def summarize_v1736(manifest: dict[str, Any]) -> dict[str, Any]:
    gate = manifest.get("gate") if isinstance(manifest.get("gate"), dict) else {}
    return {
        "exists": as_bool(manifest.get("_exists")),
        "decision": as_text(manifest.get("decision")),
        "pass": as_bool(manifest.get("pass")),
        "service_window_label": as_text(gate.get("service_window_label") or gate.get("wlan_pd_service_window_label")),
        "non_log_label": as_text(gate.get("nonlog_label") or gate.get("non_log_label") or gate.get("wlan_pd_non_log_label")),
        "requested_wlanmdsp": as_text(gate.get("requested_wlanmdsp")),
        "wlfw_service69_seen": as_text(gate.get("wlfw_service69_seen")),
    }


def build_result(args: argparse.Namespace) -> dict[str, Any]:
    v1870_manifest = load_json(args.v1870_manifest)
    v1755_manifest = load_json(args.v1755_manifest)
    v1753_manifest = load_json(args.v1753_manifest)
    v1736_manifest = load_json(args.v1736_manifest)
    v1870 = summarize_v1870(v1870_manifest)
    v1755 = summarize_v1755(v1755_manifest)
    v1753 = summarize_v1753(v1753_manifest)
    v1736 = summarize_v1736(v1736_manifest)
    checks = {
        "v1870_private_mount_contract_closed": (
            v1870["exists"]
            and v1870["pass"]
            and v1870["rollback_ok"]
            and v1870["post_version_ok"]
            and v1870["post_selftest_fail_zero"]
            and v1870["private_cnss_contract_ok"]
            and v1870["private_mount_label"] == "private-mount-sdx50m-selected"
        ),
        "v1870_pm_client_returned": v1870["pm_client_register_rc"] == "0" and v1870["pm_client_connect_rc"] == "0",
        "v1870_firmware_request_absent": (
            v1870["requested_wlanmdsp"] == "0"
            and v1870["wlfw_service69_seen"] == "0"
            and v1870["wlan0_present"] == "0"
            and not v1870["raw_wlan_pd_positive"]
        ),
        "v1870_wifi_prereq_absent": not v1870["lower_service69_progress"] and not v1870["lower_wlan0_present"],
        "v1755_pm_vote_split_gate_fixed": (
            v1755["exists"]
            and v1755["pass"]
            and v1755["label"] == "pm-vote-contract-split-gate-needed"
        ),
        "v1753_android_good_requests_firmware": (
            v1753["exists"]
            and v1753["pass"]
            and v1753["requested_wlanmdsp"] == "1"
            and v1753["requested_pd_image"] == "1"
        ),
        "v1736_service_route_still_no_request": (
            v1736["exists"]
            and v1736["pass"]
            and v1736["requested_wlanmdsp"] == "0"
            and v1736["wlfw_service69_seen"] == "0"
        ),
        "hard_stops_preserved": v1870["safety_ok"],
    }
    pass_ok = all(checks.values())
    return {
        "cycle": "V1871",
        "type": "host-only private-mount PM-vote reconciliation",
        "decision": (
            "v1871-private-mount-does-not-close-pm-vote-gap-host-pass"
            if pass_ok
            else "v1871-private-mount-pm-vote-reconcile-review"
        ),
        "label": "private-mount-selection-closed-pm-vote-gap-open" if pass_ok else "review",
        "pass": pass_ok,
        "reason": (
            "V1870 proves the rollbackable private SDX50M mount and PM selection path, but firmware request, WLFW service 69, and wlan0 remain absent; continue with the V1755 narrow PM register/vote contract repair rather than another private-mount retry."
        ),
        "checks": checks,
        "v1870": v1870,
        "v1755": v1755,
        "v1753": v1753,
        "v1736": v1736,
        "inputs": {
            "v1870": rel(args.v1870_manifest),
            "v1755": rel(args.v1755_manifest),
            "v1753": rel(args.v1753_manifest),
            "v1736": rel(args.v1736_manifest),
        },
        "selected_next_gate": {
            "cycle": "V1872",
            "label": "pm-register-vote-contract-repair-source-build",
            "type": "source/build-only first",
            "scope": "repair the narrow peripheral-manager PM register/vote contract around the V1736 service-manager internal-modem route",
            "success_criteria": [
                "observable PM vote text or trace under the internal-modem route",
                "`requested_wlanmdsp=1` or `requested_pd_image=1` before considering WLFW/HAL work",
                "WLFW service 69 and wlan0 remain hard prerequisites before scan/connect",
            ],
        },
    }


def render_report(result: dict[str, Any]) -> str:
    checks = result["checks"]
    v1870 = result["v1870"]
    v1755 = result["v1755"]
    v1753 = result["v1753"]
    v1736 = result["v1736"]
    return "\n".join([
        "# Native Init V1871 Private Mount PM Vote Reconcile",
        "",
        "## Summary",
        "",
        "- Cycle: `V1871`",
        "- Type: host-only private-mount PM-vote reconciliation",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'REVIEW'}",
        f"- Reason: {result['reason']}",
        "- Evidence: `tmp/wifi/v1871-private-mount-pm-vote-reconcile`",
        "",
        "## Checks",
        "",
        "| check | value |",
        "|---|---:|",
        *(f"| `{key}` | `{value}` |" for key, value in checks.items()),
        "",
        "## V1870 Private Mount",
        "",
        f"- decision/pass/rollback: `{v1870['decision']}` / `{v1870['pass']}` / `{v1870['rollback_ok']}`",
        f"- private label/contract/bind: `{v1870['private_mount_label']}` / `{v1870['private_cnss_contract_ok']}` / `{v1870['private_cnss_bind_rc']}`",
        f"- PM client register/connect rc: `{v1870['pm_client_register_rc']}` / `{v1870['pm_client_connect_rc']}`",
        f"- requested_wlanmdsp/WLFW69/wlan0: `{v1870['requested_wlanmdsp']}` / `{v1870['wlfw_service69_seen']}` / `{v1870['wlan0_present']}`",
        "",
        "## PM Vote Split",
        "",
        f"- V1755 label: `{v1755['label']}`",
        f"- V1755 reason: {v1755['reason']}",
        f"- Android-good V1753 requested_wlanmdsp/requested_pd_image: `{v1753['requested_wlanmdsp']}` / `{v1753['requested_pd_image']}`",
        f"- Native V1736 requested_wlanmdsp/WLFW69: `{v1736['requested_wlanmdsp']}` / `{v1736['wlfw_service69_seen']}`",
        "",
        "## Interpretation",
        "",
        "V1870 closes the rollbackable private SDX50M mount evidence gap, but it does not close the firmware-request gate. The route still has no `wlanmdsp` request, no WLFW service 69, and no `wlan0`; therefore Wi-Fi HAL, scan/connect, credentials, DHCP/routes, and external ping remain blocked.",
        "",
        "The next information-gaining unit is the narrow V1755 PM register/vote contract repair. Another private-mount retry would only repeat a now-closed selection proof while leaving the same firmware-request absence.",
        "",
        "## Next",
        "",
        "- V1872 should be source/build-only first: repair or instrument the PM register/vote contract around the V1736 service-manager route.",
        "- Success should be an observable PM vote plus `requested_wlanmdsp=1` or `requested_pd_image=1`; only then re-check WLFW service 69 and `wlan0`.",
        "- Do not attempt Wi-Fi connect or ping until WLFW service 69 and `wlan0` are present.",
        "",
        "## Safety Scope",
        "",
        "V1871 is host-only. It does not contact the device, flash, reboot, start services, open `/dev/subsys_esoc0`, force RC1, fake ONLINE state, start Wi-Fi HAL, scan/connect, use credentials, configure DHCP/routes, perform external ping, write PMIC/GPIO/GDSC controls, perform eSoC notify/`BOOT_DONE`, run PCI rescan/platform bind-unbind, or write firmware/boot/device partitions.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--v1870-manifest", type=Path, default=DEFAULT_V1870)
    parser.add_argument("--v1755-manifest", type=Path, default=DEFAULT_V1755)
    parser.add_argument("--v1753-manifest", type=Path, default=DEFAULT_V1753)
    parser.add_argument("--v1736-manifest", type=Path, default=DEFAULT_V1736)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_result(args)
    store = EvidenceStore(args.out_dir)
    store.write_json("manifest.json", result)
    report = render_report(result)
    store.write_text("summary.md", report)
    write_private_text(args.report_path, report)
    print(json.dumps({
        "decision": result["decision"],
        "pass": result["pass"],
        "label": result["label"],
        "out_dir": rel(args.out_dir),
        "report": rel(args.report_path),
    }, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
