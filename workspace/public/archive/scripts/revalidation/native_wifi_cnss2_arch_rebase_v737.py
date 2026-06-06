#!/usr/bin/env python3
"""V737 host-only SM8250 CNSS2 architecture rebase classifier.

This classifier reconciles the V735/V736 service-notifier interpretation with
the earlier V726/V727 SM8250 CNSS2/PCIe prerequisite model. It does not contact
the device or perform live Wi-Fi actions.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v737-cnss2-arch-rebase")
DEFAULT_V726_MANIFEST = Path("tmp/wifi/v726-cnss2-pcie-prereq/manifest.json")
DEFAULT_V727_MANIFEST = Path("tmp/wifi/v727-lower-prereq/manifest.json")
DEFAULT_V731_MANIFEST = Path("tmp/wifi/v731-firmware-mounted-modem-holder/manifest.json")
DEFAULT_V735_MANIFEST = Path("tmp/wifi/v735-current-cnss-only-observer/manifest.json")
DEFAULT_V736_MANIFEST = Path("tmp/wifi/v736-service180-to-mhi-gap/manifest.json")
DEFAULT_V721_MANIFEST = Path("tmp/wifi/v721-servreg-cnss2-delta-final/manifest.json")
DEFAULT_ANDROID_V622_MANIFEST = Path(
    "tmp/wifi/v622-android-mdm-helper-timing-handoff-live-20260523-032506/"
    "v622-android-mdm-helper-timing-recapture-run/manifest.json"
)
LATEST_POINTER = Path("tmp/wifi/latest-v737-cnss2-arch-rebase.txt")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v726-manifest", type=Path, default=DEFAULT_V726_MANIFEST)
    parser.add_argument("--v727-manifest", type=Path, default=DEFAULT_V727_MANIFEST)
    parser.add_argument("--v731-manifest", type=Path, default=DEFAULT_V731_MANIFEST)
    parser.add_argument("--v735-manifest", type=Path, default=DEFAULT_V735_MANIFEST)
    parser.add_argument("--v736-manifest", type=Path, default=DEFAULT_V736_MANIFEST)
    parser.add_argument("--v721-manifest", type=Path, default=DEFAULT_V721_MANIFEST)
    parser.add_argument("--android-v622-manifest", type=Path, default=DEFAULT_ANDROID_V622_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


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


def int_value(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return 0


def check_detail(manifest: dict[str, Any], name: str) -> dict[str, Any]:
    for check in manifest.get("checks", []):
        if check.get("name") == name:
            detail = check.get("detail")
            return detail if isinstance(detail, dict) else {}
    return {}


def check_status(manifest: dict[str, Any], name: str) -> str:
    for check in manifest.get("checks", []):
        if check.get("name") == name:
            return str(check.get("status") or "")
    return ""


def count_from_markers(manifest: dict[str, Any], name: str) -> int:
    live = manifest.get("live") or {}
    markers = (live.get("markers") or {}).get("counts") or {}
    return int_value(markers.get(name))


def summarize_v726(manifest: dict[str, Any]) -> dict[str, Any]:
    wlan = check_detail(manifest, "wlan-module-loaded")
    modem = check_detail(manifest, "modem-mpss-online")
    firmware = check_detail(manifest, "wlanmdsp-firmware-visible")
    progression = check_detail(manifest, "cnss2-mhi-wlfw-progression")
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "wlan_proc_modules": bool(wlan.get("proc_modules_has_wlan")),
        "wlan_sys_module": bool(wlan.get("sys_module_wlan_exists")),
        "mss_state": modem.get("mss_state"),
        "mdm3_state": modem.get("mdm3_state"),
        "wlanmdsp_find_hits": firmware.get("find_hits") or [],
        "wlanmdsp_stat_hits": firmware.get("stat_hits") or [],
        "progression": progression,
    }


def summarize_v727(manifest: dict[str, Any]) -> dict[str, Any]:
    current = check_detail(manifest, "current-vendor-firmware-visible")
    isolated = check_detail(manifest, "isolated-vendor-firmware-visible")
    wlan = check_detail(manifest, "wlan-static-parameter-surface")
    modem = check_detail(manifest, "modem-online")
    progression = check_detail(manifest, "mhi-wlfw-wlan0-progression")
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "current_vendor_hits": current.get("hits") or [],
        "isolated_vendor_hits": isolated.get("hits") or [],
        "wlan_proc_modules": bool(wlan.get("proc_modules_has_wlan")),
        "wlan_sys_module": bool(wlan.get("sys_module_wlan_exists")),
        "wlan_initstate": bool(wlan.get("has_initstate")),
        "wlan_refcnt": bool(wlan.get("has_refcnt")),
        "vendor_module_hits": wlan.get("vendor_lib_module_hits") or [],
        "mss_state": modem.get("mss_state"),
        "mdm3_state": modem.get("mdm3_state"),
        "progression": progression,
    }


def summarize_v731(manifest: dict[str, Any]) -> dict[str, Any]:
    firmware = check_detail(manifest, "firmware-mounted")
    holder = check_detail(manifest, "subsys-modem-holder-opened")
    mss = check_detail(manifest, "mss-online-window")
    qrtr = check_detail(manifest, "qrtr-rx-window")
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "firmware_mounted": firmware.get("mounted_hits") or {},
        "modem_blob_visible": firmware.get("modem_blob_visible") or {},
        "holder_opened": bool(holder.get("holder_opened")),
        "mss_after_holder": holder.get("mss_after_holder"),
        "mss_window": {
            "before": mss.get("before"),
            "after_holder": mss.get("after_holder"),
            "after_wait": mss.get("after_wait"),
        },
        "qrtr_rx_seen": bool(((qrtr.get("wait") or {}).get("seen")) or holder.get("qrtr_seen")),
    }


def summarize_v735(manifest: dict[str, Any]) -> dict[str, Any]:
    holder = check_detail(manifest, "modem-holder-window")
    wlan = check_detail(manifest, "wlan-static-surface")
    contract = check_detail(manifest, "cnss-only-contract")
    guard = check_detail(manifest, "qrtr-readback-guard")
    progression = check_detail(manifest, "cnss2-mhi-wlfw-progression")
    markers = progression.get("markers") or {}
    services = progression.get("qrtr_services") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "mss_window": holder.get("mss") or [],
        "mdm3_window": holder.get("mdm3") or [],
        "qrtr_rx": bool(holder.get("qrtr_rx")),
        "wlan_proc_modules": bool(wlan.get("proc_modules_has_wlan")),
        "wlan_sys_module": bool(wlan.get("sys_module_wlan_exists")),
        "wlan_firmware_visible": wlan.get("wlan_firmware_visible") or {},
        "companion_order": contract.get("order"),
        "service_manager_started": int_value(check_detail(manifest, "forbidden-helper-actions").get("service_manager")),
        "wifi_hal_started": int_value(check_detail(manifest, "forbidden-helper-actions").get("wifi_hal")),
        "service69_events": int_value(guard.get("service_events") or progression.get("readback_service_events")),
        "qrtr_services": services,
        "markers": markers,
        "service_notifier_count": count_from_markers(manifest, "service_notifier"),
        "kernel_warning": count_from_markers(manifest, "kernel_warning"),
    }


def summarize_v736(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "next_step": manifest.get("next_step"),
        "post180_gap": check_detail(manifest, "post180-gap-confirmed"),
        "qca_mhi_surface": check_detail(manifest, "qca-mhi-surface"),
    }


def summarize_v721(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "shared_publication": check_detail(manifest, "shared-lower-qmi-publication"),
        "native_gap": check_detail(manifest, "native-servreg-wlanpd-cnss2-gap"),
        "android_continuation": check_detail(manifest, "android-servreg-wlanpd-continuation"),
    }


def summarize_android(manifest: dict[str, Any]) -> dict[str, Any]:
    summary = manifest.get("android_summary") or {}
    return {
        "decision": manifest.get("decision"),
        "pass": manifest.get("pass"),
        "counts": summary.get("counts") or {},
        "deltas_ms": summary.get("deltas_ms") or {},
    }


def build_checks(args: argparse.Namespace, raw: dict[str, dict[str, Any]], summaries: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    if args.command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only classifier; no device command executed",
            "next_step": "run V737 against existing manifests",
        }]

    inputs_ready = all(item.get("exists") and not item.get("invalid") for item in raw.values())
    v726 = summaries["v726"]
    v727 = summaries["v727"]
    v731 = summaries["v731"]
    v735 = summaries["v735"]
    v736 = summaries["v736"]
    v721 = summaries["v721"]
    android = summaries["android_v622"]
    android_counts = android.get("counts") or {}
    v721_native_gap = v721.get("native_gap") or {}
    v735_markers = v735.get("markers") or {}
    return [
        {
            "name": "inputs-present",
            "status": "pass" if inputs_ready else "blocked",
            "detail": {name: item.get("path") for name, item in raw.items()},
            "next_step": "restore missing evidence or rerun the named classifier",
        },
        {
            "name": "sm8250-cnss2-model-correction-present",
            "status": "pass" if v726.get("decision") == "v726-cnss2-pcie-modem-and-wlan-module-prereq-gap-classified" and v726.get("pass") is True else "blocked",
            "detail": {
                "v726_decision": v726.get("decision"),
                "wlan_proc_modules": v726.get("wlan_proc_modules"),
                "wlan_sys_module": v726.get("wlan_sys_module"),
                "mss_state": v726.get("mss_state"),
                "mdm3_state": v726.get("mdm3_state"),
            },
            "next_step": "do not keep service180/74 as the primary CNSS2 trigger model if V726 regresses",
        },
        {
            "name": "wlan-static-not-missing-ko",
            "status": "pass" if v727.get("wlan_sys_module") and not v727.get("wlan_proc_modules") and not v727.get("vendor_module_hits") else "review",
            "detail": {
                "sys_module_wlan": v727.get("wlan_sys_module"),
                "proc_modules_wlan": v727.get("wlan_proc_modules"),
                "initstate": v727.get("wlan_initstate"),
                "refcnt": v727.get("wlan_refcnt"),
                "vendor_module_hits": v727.get("vendor_module_hits"),
            },
            "next_step": "treat wlan as static/built-in unless Android later proves a loadable wlan.ko path",
        },
        {
            "name": "vendor-wifi-firmware-namespace-gap",
            "status": "pass" if not v727.get("current_vendor_hits") and v727.get("isolated_vendor_hits") else "review",
            "detail": {
                "current_vendor_hits": v727.get("current_vendor_hits"),
                "isolated_vendor_hits": v727.get("isolated_vendor_hits"),
                "v735_wlan_firmware_visible": v735.get("wlan_firmware_visible"),
            },
            "next_step": "keep real sda29 vendor namespace in any lower companion or modem holder window",
        },
        {
            "name": "modem-holder-progresses-mss-only",
            "status": "pass" if v731.get("mss_after_holder") == "ONLINE" and "ONLINE" in v735.get("mss_window", []) and "ONLINE" not in v735.get("mdm3_window", []) else "review",
            "detail": {
                "v731_mss_after_holder": v731.get("mss_after_holder"),
                "v731_qrtr_rx_seen": v731.get("qrtr_rx_seen"),
                "v735_mss_window": v735.get("mss_window"),
                "v735_mdm3_window": v735.get("mdm3_window"),
            },
            "next_step": "separate mss ONLINE evidence from the still-missing WLAN-PD/WLFW continuation",
        },
        {
            "name": "service-publication-is-side-evidence",
            "status": "pass" if v721_native_gap.get("wlan_pd") == 0 and v721_native_gap.get("wlfw") == 0 and v721_native_gap.get("wlan0") == 0 else "review",
            "detail": {
                "v721_shared_publication": v721.get("shared_publication"),
                "v721_native_gap": v721_native_gap,
                "v735_service_notifier_count": v735.get("service_notifier_count"),
                "v736_prior_next_step": v736.get("next_step"),
            },
            "next_step": "do not route the next live unit to service74-only or HAL/connect",
        },
        {
            "name": "mhi-wlfw-wlan0-still-absent",
            "status": "pass" if int_value(v735_markers.get("mhi")) == 0 and int_value(v735_markers.get("wlfw")) == 0 and int_value(v735_markers.get("wlan0")) == 0 and v735.get("service69_events") == 0 else "blocked",
            "detail": {
                "v735_markers": {name: v735_markers.get(name, 0) for name in ("mhi", "qca6390", "wlfw", "bdf", "wlan0", "wlan_pd")},
                "v735_service69_events": v735.get("service69_events"),
                "android_counts": {name: android_counts.get(name, 0) for name in ("wlan_pd", "wlfw_start", "bdf_regdb", "bdf_bdwlan", "wlan0")},
            },
            "next_step": "instrument modem/WLAN-PD/MHI lower transition before Wi-Fi HAL or connect",
        },
    ]


def decide(args: argparse.Namespace, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v737-cnss2-arch-rebase-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V737 classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v737-cnss2-arch-rebase-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear evidence blockers before choosing the next live gate",
        )
    return (
        "v737-route-to-modem-wlan-mhi-prereq-observer",
        True,
        (
            "V736 service74-centric next step is superseded: service publication is side evidence; "
            "the actionable gap is modem/WLAN firmware namespace plus static wlan/CNSS2-to-MHI/WLFW progression"
        ),
        "plan V738 as a bounded modem+wlan/MHI prerequisite observer below HAL/connect",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    checks = [
        [check["name"], check["status"], json.dumps(check["detail"], ensure_ascii=False, sort_keys=True), check["next_step"]]
        for check in manifest.get("checks", [])
    ]
    summary_rows = []
    for name in ("v726", "v727", "v731", "v735", "v736", "v721", "android_v622"):
        item = manifest.get(f"{name}_summary") or {}
        summary_rows.append([name, str(item.get("decision")), str(item.get("pass"))])
    route_rows = [
        ["primary_trigger_model", "SM8250 CNSS2/PCIe lower prerequisite path, not service180/74 alone"],
        ["wlan_load_interpretation", "static/built-in parameter surface unless later Android evidence proves loadable wlan.ko"],
        ["required_vendor_view", "real sda29 vendor firmware namespace for wlanmdsp/bdwlan/regdb visibility"],
        ["current_progress", "mss can reach ONLINE under holder, but MHI/WLFW/service69/BDF/wlan0 remain absent"],
        ["blocked_actions", "Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping"],
    ]
    return "\n".join([
        "# V737 CNSS2 Architecture Rebase Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Inputs",
        "",
        markdown_table(["input", "decision", "pass"], summary_rows),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "detail", "next"], checks),
        "",
        "## Routing",
        "",
        markdown_table(["item", "value"], route_rows),
    ])


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    raw = {
        "v726": load_manifest(args.v726_manifest),
        "v727": load_manifest(args.v727_manifest),
        "v731": load_manifest(args.v731_manifest),
        "v735": load_manifest(args.v735_manifest),
        "v736": load_manifest(args.v736_manifest),
        "v721": load_manifest(args.v721_manifest),
        "android_v622": load_manifest(args.android_v622_manifest),
    }
    if args.command == "run":
        summaries = {
            "v726": summarize_v726(raw["v726"]),
            "v727": summarize_v727(raw["v727"]),
            "v731": summarize_v731(raw["v731"]),
            "v735": summarize_v735(raw["v735"]),
            "v736": summarize_v736(raw["v736"]),
            "v721": summarize_v721(raw["v721"]),
            "android_v622": summarize_android(raw["android_v622"]),
        }
    else:
        summaries = {name: {} for name in raw}
    checks = build_checks(args, raw, summaries)
    decision, pass_ok, reason, next_step = decide(args, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v737",
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
        **{f"{name}_summary": summary for name, summary in summaries.items()},
        "device_commands_executed": False,
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
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
