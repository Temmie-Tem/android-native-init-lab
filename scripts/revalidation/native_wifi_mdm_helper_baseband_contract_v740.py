#!/usr/bin/env python3
"""V740 host-only mdm_helper/baseband contract classifier.

This classifier reconciles the older V621/V622 mdm_helper evidence with the
current V739 MDM3/WLAN-PD blocker. It does not contact the device or perform
live Wi-Fi actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v740-mdm-helper-baseband-contract")
DEFAULT_V739_MANIFEST = Path("tmp/wifi/v739-mdm3-wlanpd-delta/manifest.json")
DEFAULT_V621_MANIFEST = Path("tmp/wifi/v621-mdm-helper-contract-classifier/manifest.json")
DEFAULT_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
DEFAULT_V614_SNAPSHOT = Path(
    "tmp/wifi/v614-mdm3-trigger-path-classifier/native/vendor-init-readonly-snapshot.txt"
)
DEFAULT_V735_MANIFEST = Path("tmp/wifi/v735-current-cnss-only-observer/manifest.json")
DEFAULT_V738_MANIFEST = Path("tmp/wifi/v738-modem-wlan-mhi-observer/manifest.json")
LATEST_POINTER = Path("tmp/wifi/latest-v740-mdm-helper-baseband-contract.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v739-manifest", type=Path, default=DEFAULT_V739_MANIFEST)
    parser.add_argument("--v621-manifest", type=Path, default=DEFAULT_V621_MANIFEST)
    parser.add_argument("--v622-manifest", type=Path, default=DEFAULT_V622_MANIFEST)
    parser.add_argument("--v614-snapshot", type=Path, default=DEFAULT_V614_SNAPSHOT)
    parser.add_argument("--v735-manifest", type=Path, default=DEFAULT_V735_MANIFEST)
    parser.add_argument("--v738-manifest", type=Path, default=DEFAULT_V738_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def read_text(path: Path) -> str:
    resolved = repo_path(path)
    if not resolved.exists():
        return ""
    return resolved.read_text(encoding="utf-8", errors="replace")


def load_manifest(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"exists": False, "path": str(resolved)}
    try:
        data = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {"exists": True, "path": str(resolved), "invalid": str(exc)}
    if not isinstance(data, dict):
        return {"exists": True, "path": str(resolved), "invalid": "not-object"}
    data.setdefault("exists", True)
    data.setdefault("path", str(resolved))
    return data


def bool_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    return 0


def float_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def delta_ms(newer: float | None, older: float | None) -> float | None:
    if newer is None or older is None:
        return None
    return round(newer - older, 3)


def service_block(snapshot: str, service_name: str) -> str:
    match = re.search(rf"^service\s+{re.escape(service_name)}\s+.*(?:\n[ \t].*)*", snapshot, re.M)
    return match.group(0) if match else ""


def has_line(text: str, pattern: str) -> bool:
    return re.search(pattern, text, re.I | re.M) is not None


def static_contract(snapshot: str) -> dict[str, Any]:
    helper = service_block(snapshot, "vendor.mdm_helper")
    launcher = service_block(snapshot, "vendor.mdm_launcher")
    return {
        "mdm_helper_present": bool(helper),
        "mdm_helper_disabled": has_line(helper, r"^\s*disabled\s*$"),
        "mdm_helper_class_core": has_line(helper, r"^\s*class\s+core\s*$"),
        "mdm_helper_group": " ".join(re.findall(r"^\s*group\s+(.+)$", helper, flags=re.M)),
        "mdm_helper_shutdown_critical": has_line(helper, r"^\s*shutdown\s+critical\s*$"),
        "mdm_launcher_present": bool(launcher),
        "mdm_launcher_class_main": has_line(launcher, r"^\s*class\s+main\s*$"),
        "mdm_launcher_oneshot": has_line(launcher, r"^\s*oneshot\s*$"),
        "init_mdm_reads_ro_baseband": has_line(snapshot, r"baseband=`getprop\s+ro\.baseband`"),
        "init_mdm_accepts_mdm": has_line(snapshot, r'\[\s*"\$baseband"\s*=\s*"mdm"\s*\]'),
        "init_mdm_starts_helper": has_line(snapshot, r"\bstart\s+vendor\.mdm_helper\b"),
        "raw_esoc_path_visible": has_line(snapshot, r"/dev/esoc|/sys/(?:bus/)?(?:esoc|subsys)|subsys_esoc0|esoc0"),
        "ioctl_hint_visible": has_line(snapshot, r"\bioctl\b"),
        "wcnss_service_block_visible": bool(service_block(snapshot, "wcnss-service")),
        "wcnss_service_start_ref": has_line(snapshot, r"\bstart\s+wcnss-service\b"),
    }


def v622_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") or {}
    props = summary.get("props") or {}
    timing = summary.get("timing") or {}
    counts = summary.get("counts") or {}
    service_180 = float_value(timing.get("service_notifier_180_ms"))
    launcher = float_value(timing.get("mdm_launcher_boottime_ms"))
    helper = float_value(timing.get("mdm_helper_boottime_ms"))
    wlan_pd = float_value(timing.get("wlan_pd_ms"))
    cnss_daemon = float_value(timing.get("cnss_daemon_boottime_ms"))
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "props": {
            name: props.get(name)
            for name in (
                "ro.baseband",
                "ro.boot.baseband",
                "init.svc.vendor.mdm_launcher",
                "init.svc.vendor.mdm_helper",
                "persist.vendor.mdm_helper.fail_action",
            )
        },
        "timing": {
            "service_notifier_180_ms": service_180,
            "mdm_launcher_boottime_ms": launcher,
            "mdm_helper_boottime_ms": helper,
            "cnss_daemon_boottime_ms": cnss_daemon,
            "wlan_pd_ms": wlan_pd,
            "launcher_after_service180_ms": delta_ms(launcher, service_180),
            "helper_after_service180_ms": delta_ms(helper, service_180),
            "helper_before_wlan_pd_ms": delta_ms(wlan_pd, helper),
            "cnss_daemon_after_helper_ms": delta_ms(cnss_daemon, helper),
        },
        "counts": {
            name: bool_int(counts.get(name))
            for name in (
                "service_notifier_180",
                "service_notifier_74",
                "wlan_pd",
                "wlfw_start",
                "bdf_regdb",
                "bdf_bdwlan",
                "wlan0",
            )
        },
    }


def v739_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    v738 = manifest.get("v738_summary") or {}
    android_v590 = manifest.get("android_v590_summary") or {}
    android_v611 = manifest.get("android_v611_summary") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "android_mss": android_v590.get("mss_state") or android_v611.get("mss_state"),
        "android_mdm3": android_v590.get("mdm3_state") or android_v611.get("mdm3_state"),
        "native_mss_after_companion": v738.get("mss_after_companion"),
        "native_mdm3_after_companion": v738.get("mdm3_after_companion"),
        "native_mhi_devices_count": bool_int(v738.get("mhi_devices_count")),
        "native_service69_events": bool_int(v738.get("service69_events")),
    }


def extract_check(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in manifest.get("checks") or []:
        if check.get("name") == name:
            return check
    return {}


def v735_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    progression = extract_check(manifest, "cnss2-mhi-wlfw-progression").get("detail") or {}
    modem_window = extract_check(manifest, "modem-holder-window").get("detail") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "mss": modem_window.get("mss"),
        "mdm3": modem_window.get("mdm3"),
        "markers": progression.get("markers") or {},
        "qrtr_services": progression.get("qrtr_services") or {},
    }


def v738_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    lower = manifest.get("lower_state") or {}
    surface = manifest.get("mhi_surface") or {}
    markers = surface.get("markers") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "mss": [lower.get("mss_before"), lower.get("mss_after_holder"), lower.get("mss_after_companion")],
        "mdm3": [lower.get("mdm3_before"), lower.get("mdm3_after_holder"), lower.get("mdm3_after_companion")],
        "qrtr_services": lower.get("qrtr_services") or {},
        "markers": markers,
        "mhi_devices_count": bool_int(surface.get("mhi_devices_count")),
        "wlan0_netdev": bool(surface.get("wlan0_netdev")),
    }


def build_checks(args: argparse.Namespace, raw: dict[str, Any], summaries: dict[str, Any]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only mdm_helper/baseband contract classifier",
            "next_step": "run V740 against existing V621/V622/V739 evidence",
        }]

    inputs_ready = all(item.get("exists") and not item.get("invalid") for item in raw.values())
    static = summaries["static_contract"]
    v622 = summaries["v622"]
    v739 = summaries["v739"]
    v735 = summaries["v735"]
    v738 = summaries["v738"]
    v622_timing = v622.get("timing") or {}
    v622_props = v622.get("props") or {}
    return [
        {
            "name": "inputs-present",
            "status": "pass" if inputs_ready else "blocked",
            "detail": {name: item.get("path") for name, item in raw.items()},
            "next_step": "restore missing host evidence before classifying live mdm_helper safety",
        },
        {
            "name": "v739-active-blocker",
            "status": "pass"
            if (
                v739.get("decision") == "v739-mdm3-online-delta-active-blocker"
                and v739.get("android_mdm3") == "ONLINE"
                and v739.get("native_mdm3_after_companion") == "OFFLINING"
            )
            else "blocked",
            "detail": v739,
            "next_step": "do not spend cycles on HAL/connect until native mdm3/WLAN-PD progresses",
        },
        {
            "name": "static-mdm-helper-contract",
            "status": "pass"
            if (
                static.get("mdm_helper_present")
                and static.get("mdm_helper_disabled")
                and static.get("mdm_launcher_present")
                and static.get("mdm_launcher_oneshot")
                and static.get("init_mdm_reads_ro_baseband")
                and static.get("init_mdm_starts_helper")
            )
            else "blocked",
            "detail": static,
            "next_step": "do not use launcher unless an Android-init-compatible start command exists",
        },
        {
            "name": "android-same-boot-baseband-and-order",
            "status": "pass"
            if (
                v622_props.get("ro.baseband") == "mdm"
                and v622_props.get("init.svc.vendor.mdm_helper") == "running"
                and (v622_timing.get("helper_after_service180_ms") or 0) > 0
                and (v622_timing.get("helper_before_wlan_pd_ms") or 0) > 0
            )
            else "review",
            "detail": {
                "decision": v622.get("decision"),
                "props": v622_props,
                "timing": v622_timing,
                "counts": v622.get("counts"),
            },
            "next_step": "treat mdm_helper as post-notifier candidate, not first-notifier trigger",
        },
        {
            "name": "native-service-publication-instability",
            "status": "review"
            if bool_int((v735.get("markers") or {}).get("service_notifier")) > 0
            and all(bool_int((v738.get("qrtr_services") or {}).get(name)) == 0 for name in ("180", "74", "69"))
            else "pass",
            "detail": {
                "v735": v735,
                "v738": v738,
            },
            "next_step": "gate any mdm_helper live proof on observed service-notifier/WLAN lower window, never blind start",
        },
        {
            "name": "risk-guardrails",
            "status": "review"
            if static.get("mdm_helper_shutdown_critical")
            or "panic" in str(v622_props.get("persist.vendor.mdm_helper.fail_action", ""))
            else "pass",
            "detail": {
                "shutdown_critical": static.get("mdm_helper_shutdown_critical"),
                "fail_action": v622_props.get("persist.vendor.mdm_helper.fail_action"),
                "raw_esoc_path_visible": static.get("raw_esoc_path_visible"),
                "ioctl_hint_visible": static.get("ioctl_hint_visible"),
            },
            "next_step": "require bounded runtime, transcript capture, and reboot cleanup for any future helper proof",
        },
    ]


def decide(args: argparse.Namespace, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v740-mdm-helper-baseband-contract-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V740 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v740-mdm-helper-baseband-contract-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "refresh or repair host evidence before any live proof",
        )
    return (
        "v740-mdm-helper-post-notifier-gated-proof-selected",
        True,
        (
            "Android starts mdm_helper after service-notifier 180 but before WLAN-PD, "
            "so mdm_helper is not a first-trigger target; it is only a bounded "
            "post-notifier candidate for the native mdm3/WLAN-PD gap"
        ),
        "plan V741 as gated mdm_helper start-only proof after native lower service publication, still no HAL/connect",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    summary_rows = [
        ["static_contract", json.dumps(manifest.get("static_contract", {}), ensure_ascii=False, sort_keys=True)],
        ["v622", json.dumps(manifest.get("v622_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["v739", json.dumps(manifest.get("v739_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["v735", json.dumps(manifest.get("v735_summary", {}), ensure_ascii=False, sort_keys=True)],
        ["v738", json.dumps(manifest.get("v738_summary", {}), ensure_ascii=False, sort_keys=True)],
    ]
    return "\n".join([
        "# V740 MDM Helper/Baseband Contract Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- daemon_start_executed: `{manifest['daemon_start_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], check_rows),
        "",
        "## Evidence Summary",
        "",
        markdown_table(["item", "value"], summary_rows),
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    raw = {
        "v739": load_manifest(args.v739_manifest),
        "v621": load_manifest(args.v621_manifest),
        "v622": load_manifest(args.v622_manifest),
        "v735": load_manifest(args.v735_manifest),
        "v738": load_manifest(args.v738_manifest),
        "v614_snapshot": {
            "exists": bool(read_text(args.v614_snapshot)),
            "path": str(repo_path(args.v614_snapshot)),
        },
    }
    snapshot = read_text(args.v614_snapshot)
    if args.command == "run":
        summaries = {
            "static_contract": static_contract(snapshot),
            "v622": v622_summary(raw["v622"]),
            "v739": v739_summary(raw["v739"]),
            "v735": v735_summary(raw["v735"]),
            "v738": v738_summary(raw["v738"]),
        }
    else:
        summaries = {
            "static_contract": {},
            "v622": {},
            "v739": {},
            "v735": {},
            "v738": {},
        }
    checks = build_checks(args, raw, summaries)
    decision, pass_ok, reason, next_step = decide(args, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v740",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "out_dir": str(repo_path(args.out_dir)),
        "inputs": {
            name: {"path": item.get("path"), "decision": item.get("decision"), "pass": item.get("pass")}
            for name, item in raw.items()
        },
        "checks": checks,
        "prior_v621": {
            "decision": raw["v621"].get("decision"),
            "pass": raw["v621"].get("pass"),
            "reason": raw["v621"].get("reason"),
            "next_step": raw["v621"].get("next_step"),
        },
        **{f"{name}_summary": summary for name, summary in summaries.items() if name != "static_contract"},
        "static_contract": summaries["static_contract"],
        "device_commands_executed": False,
        "sysfs_write_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "wifi_bringup_executed": False,
        "external_ping_executed": False,
        "boot_or_partition_write_executed": False,
    }


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"daemon_start_executed: {manifest['daemon_start_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
