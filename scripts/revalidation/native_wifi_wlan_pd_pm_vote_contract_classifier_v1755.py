#!/usr/bin/env python3
"""V1755 host-only PM vote contract split classifier for WLAN-PD autoload."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from a90harness.evidence import EvidenceStore, write_private_text


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1754 = REPO_ROOT / "tmp" / "wifi" / "v1754-wlan-pd-trigger-gap-classifier" / "manifest.json"
DEFAULT_V1717 = REPO_ROOT / "tmp" / "wifi" / "v1717-cnss-pm-client-register-static" / "manifest.json"
DEFAULT_V1736 = REPO_ROOT / "tmp" / "wifi" / "v1736-wlan-pd-timestamped-observer-handoff" / "manifest.json"
DEFAULT_V1686 = REPO_ROOT / "tmp" / "wifi" / "v1686-wlan-pd-pm-trio-handoff" / "manifest.json"
DEFAULT_ANDROID = REPO_ROOT / "tmp" / "wifi" / "v1753-android-good-wlan-pd-firmware-request" / "manifest.json"
DEFAULT_OUT_DIR = REPO_ROOT / "tmp" / "wifi" / "v1755-wlan-pd-pm-vote-contract-classifier"
DEFAULT_REPORT = (
    REPO_ROOT
    / "docs"
    / "reports"
    / "NATIVE_INIT_V1755_WLAN_PD_PM_VOTE_CONTRACT_CLASSIFIER_2026-06-03.md"
)


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path, limit: int = 4_000_000) -> str:
    if not path.exists():
        return ""
    return path.read_bytes()[:limit].decode("utf-8", errors="replace")


def str_int(value: object, default: int = 0) -> int:
    try:
        return int(str(value or str(default)), 0)
    except ValueError:
        return default


def parse_key_values(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key:
            values[key] = value.strip()
    return values


def android_evidence(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    base = Path(manifest["out_dir"]) / "android-postfs-evidence" / "a90-v1753-wlan-pd-fwreq"
    logcat = read_text(base / "logcat-filtered.txt")
    patterns = {
        "pm_register": r"PerMgrSrv: .*add client cnss-daemon|cnss-daemon registered",
        "pm_vote": r"cnss-daemon voting for modem",
        "wlfw_service_request": r"wlfw_service_request: Start the pthread",
        "wlanmdsp": r"wlanmdsp\.mbn",
    }
    lines = {
        key: [line.strip() for line in logcat.splitlines() if re.search(pattern, line, re.IGNORECASE)]
        for key, pattern in patterns.items()
    }
    return {
        "manifest": display_path(manifest_path),
        "base": display_path(base),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "counts": {key: len(value) for key, value in lines.items()},
        "lines": {key: value[:8] for key, value in lines.items()},
    }


def v1736_evidence(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    base = Path(manifest["out_dir"])
    helper = read_text(base / "test-v1393-helper-result.stdout.txt")
    keys = parse_key_values(helper)
    gate = manifest.get("gate") or {}
    return {
        "manifest": display_path(manifest_path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "gate": gate,
        "peripheral_manager_enabled": keys.get("wifi_companion_start.peripheral_manager.enabled"),
        "service_manager": gate.get("service_manager"),
        "wlfw_service_request_hit_count": gate.get("wlfw_service_request_hit_count"),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp"),
        "firmware_label": gate.get("old_firmware_serve_label"),
    }


def v1686_evidence(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    base = Path(manifest["out_dir"])
    helper = read_text(base / "test-v1393-helper-result.stdout.txt")
    dmesg = read_text(base / "test-v1393-dmesg.stdout.txt")
    keys = parse_key_values(helper)
    gate = manifest.get("gate") or {}
    child_keys = {
        key: keys.get(key)
        for key in (
            "wifi_hal_composite_start.child.pm_proxy_helper.child_started",
            "wifi_hal_composite_start.child.per_mgr.child_started",
            "wifi_hal_composite_start.child.per_proxy.child_started",
            "wifi_hal_composite_child.per_mgr.ioprio.ok",
            "wifi_hal_composite_child.per_mgr.selinux_exec.target_context",
            "wifi_hal_composite_child.per_mgr.selinux_exec.ok",
            "wifi_hal_composite_child.per_proxy.selinux_exec.target_context",
            "wifi_hal_composite_child.per_proxy.selinux_exec.ok",
        )
    }
    return {
        "manifest": display_path(manifest_path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "gate": gate,
        "child_keys": child_keys,
        "binder_transaction_failed_minus22_count": len(re.findall(r"transaction failed .*?/-22", dmesg)),
        "pm_service_binder_failed": bool(re.search(r"pm-service:.*transaction failed .*?/-22", dmesg)),
        "pm_proxy_binder_failed": bool(re.search(r"pm-proxy:.*transaction failed .*?/-22", dmesg)),
        "pm_vote_text_seen": bool(re.search(r"cnss-daemon voting for modem|cnss-daemon registered", helper + "\n" + dmesg, re.IGNORECASE)),
        "wlfw_service_request_seen": gate.get("wlfw_service_request_seen"),
        "requested_wlanmdsp": gate.get("requested_wlanmdsp"),
        "label": gate.get("label"),
    }


def v1717_evidence(manifest_path: Path) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    checks = manifest.get("required_checks") or {}
    strings = manifest.get("string_checks") or {}
    return {
        "manifest": display_path(manifest_path),
        "decision": manifest.get("decision"),
        "pass": bool(manifest.get("pass")),
        "required_checks": checks,
        "string_checks": strings,
        "cnss_needed": manifest.get("cnss_needed") or [],
        "lib_needed": manifest.get("lib_needed") or [],
    }


def classify(v1754: dict[str, Any], android: dict[str, Any], static: dict[str, Any], native: dict[str, Any], pm: dict[str, Any]) -> tuple[str, bool, str, str]:
    if v1754.get("label") != "peripheral-manager-vote-delta-before-firmware-request":
        return (
            "v1755-prerequisite-v1754-label-mismatch",
            False,
            "V1754 did not identify the PM vote delta prerequisite",
            "prerequisite-mismatch",
        )
    static_checks = static["required_checks"]
    static_ok = bool(static["pass"]) and all(
        bool(static_checks.get(key))
        for key in (
            "cnss_import_connect",
            "cnss_import_register",
            "lib_export_register",
            "libbinder_needed",
            "peripheral_manager_string",
            "vndbinder_string",
        )
    )
    android_ok = android["counts"]["pm_vote"] > 0 and android["counts"]["wlanmdsp"] > 0
    native_cnss_only = (
        native["pass"]
        and str_int(native["wlfw_service_request_hit_count"]) > 0
        and str_int(native["requested_wlanmdsp"]) == 0
        and str(native["peripheral_manager_enabled"]) == "0"
    )
    pm_actor_failed = (
        pm["pass"]
        and pm["label"] == "pm-trio-child-failed"
        and pm["binder_transaction_failed_minus22_count"] > 0
        and not pm["pm_vote_text_seen"]
        and str_int(pm["wlfw_service_request_seen"]) == 0
        and str_int(pm["requested_wlanmdsp"]) == 0
    )
    if static_ok and android_ok and native_cnss_only and pm_actor_failed:
        return (
            "v1755-pm-vote-contract-split-gate-source-host-pass",
            True,
            "static CNSS PM imports, Android-good PM vote, native V1736 CNSS-only progress, and V1686 PM-trio binder failure show a split gate: repair the PM register/vote contract, not broad PM/eSoC/HAL actors",
            "pm-vote-contract-split-gate-needed",
        )
    return (
        "v1755-pm-vote-contract-classification-incomplete",
        False,
        "available PM/CNSS evidence did not satisfy the split-gate classifier",
        "incomplete",
    )


def render_report(result: dict[str, Any]) -> str:
    android = result["android"]
    native = result["v1736"]
    pm = result["v1686"]
    static = result["v1717"]
    return "\n".join([
        "# Native Init V1755 WLAN-PD PM Vote Contract Classifier",
        "",
        "## Summary",
        "",
        "- Cycle: `V1755`",
        "- Type: host/source-only PM vote contract split classifier",
        f"- Decision: `{result['decision']}`",
        f"- Label: `{result['label']}`",
        f"- Result: {'PASS' if result['pass'] else 'BLOCKED'}",
        f"- Reason: {result['reason']}",
        f"- Evidence: `{result['out_dir']}`",
        "",
        "## Android-good PM Vote Evidence",
        "",
        f"- Manifest: `{android['manifest']}`",
        f"- PM register lines: `{android['counts']['pm_register']}`",
        f"- PM vote lines: `{android['counts']['pm_vote']}`",
        f"- WLFW service request lines: `{android['counts']['wlfw_service_request']}`",
        f"- `wlanmdsp` lines: `{android['counts']['wlanmdsp']}`",
        "",
        "## Static CNSS PM Contract",
        "",
        f"- Manifest: `{static['manifest']}`",
        f"- Decision/pass: `{static['decision']}` / `{static['pass']}`",
        f"- Required checks: `{json.dumps(static['required_checks'], sort_keys=True)}`",
        f"- String checks: `{json.dumps(static['string_checks'], sort_keys=True)}`",
        "",
        "## Native V1736 CNSS-only Route",
        "",
        f"- Manifest: `{native['manifest']}`",
        f"- Decision/pass: `{native['decision']}` / `{native['pass']}`",
        f"- service-manager: `{native['service_manager']}`",
        f"- PM enabled: `{native['peripheral_manager_enabled']}`",
        f"- `wlfw_service_request` hits: `{native['wlfw_service_request_hit_count']}`",
        f"- requested `wlanmdsp`: `{native['requested_wlanmdsp']}`",
        f"- firmware label: `{native['firmware_label']}`",
        "",
        "## Native V1686 PM-trio Attempt",
        "",
        f"- Manifest: `{pm['manifest']}`",
        f"- Decision/pass: `{pm['decision']}` / `{pm['pass']}`",
        f"- PM label: `{pm['label']}`",
        f"- binder transaction `-22` count: `{pm['binder_transaction_failed_minus22_count']}`",
        f"- `pm-service` binder failed: `{pm['pm_service_binder_failed']}`",
        f"- `pm-proxy` binder failed: `{pm['pm_proxy_binder_failed']}`",
        f"- PM vote text seen: `{pm['pm_vote_text_seen']}`",
        f"- `wlfw_service_request` seen: `{pm['wlfw_service_request_seen']}`",
        f"- requested `wlanmdsp`: `{pm['requested_wlanmdsp']}`",
        f"- child keys: `{json.dumps(pm['child_keys'], sort_keys=True)}`",
        "",
        "## Interpretation",
        "",
        "- Android-good proves `cnss-daemon` registers/votes through the peripheral manager before the modem requests `wlanmdsp.mbn`.",
        "- V1717 proves `cnss-daemon` imports `pm_client_connect`/`pm_client_register` and `libperipheral_client.so` depends on `/dev/vndbinder` plus `vendor.qcom.PeripheralManager`.",
        "- V1736 proves the service-manager route can reach the WLFW worker but has PM disabled and never causes a `wlanmdsp.mbn` request.",
        "- V1686 proves broad PM-trio insertion is not sufficient: `pm-service`/`pm-proxy` hit Binder `-22`, no PM vote text appears, and the CNSS WLFW request path regresses.",
        "- The next useful gate is therefore not a broader actor march. It is a narrow PM register/vote contract repair around the V1736 internal-modem route, with success defined as observable PM vote plus `wlanmdsp.mbn` request.",
        "",
        "## Safety Scope",
        "",
        "This classifier is host/source-only and reads retained evidence plus static binary metadata. It performs no device contact, flash, reboot, Wi-Fi HAL start, scan/connect, credential use, DHCP/routes, external ping, PMIC/GPIO/GDSC write, eSoC notify/BOOT_DONE, PCI rescan, platform bind/unbind, firmware/partition write, or new actor start.",
        "",
    ])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--v1754-manifest", type=Path, default=DEFAULT_V1754)
    parser.add_argument("--v1717-manifest", type=Path, default=DEFAULT_V1717)
    parser.add_argument("--v1736-manifest", type=Path, default=DEFAULT_V1736)
    parser.add_argument("--v1686-manifest", type=Path, default=DEFAULT_V1686)
    parser.add_argument("--android-manifest", type=Path, default=DEFAULT_ANDROID)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    store = EvidenceStore(args.out_dir)
    v1754 = load_json(args.v1754_manifest)
    android = android_evidence(args.android_manifest)
    static = v1717_evidence(args.v1717_manifest)
    native = v1736_evidence(args.v1736_manifest)
    pm = v1686_evidence(args.v1686_manifest)
    decision, pass_ok, reason, label = classify(v1754, android, static, native, pm)
    result = {
        "cycle": "V1755",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "label": label,
        "v1754": {
            "manifest": display_path(args.v1754_manifest),
            "decision": v1754.get("decision"),
            "label": v1754.get("label"),
            "pass": bool(v1754.get("pass")),
        },
        "android": android,
        "v1717": static,
        "v1736": native,
        "v1686": pm,
        "out_dir": display_path(args.out_dir),
        "report_path": display_path(args.report_path),
        "safety": {
            "host_source_only": True,
            "device_contact": False,
            "flash": False,
            "wifi_hal": False,
            "scan_connect": False,
            "credentials": False,
            "dhcp_routes": False,
            "external_ping": False,
        },
    }
    store.write_json("manifest.json", result)
    report = render_report(result)
    write_private_text(store.path("summary.md"), report)
    write_private_text(args.report_path, report)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if pass_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
