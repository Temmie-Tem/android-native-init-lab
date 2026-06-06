#!/usr/bin/env python3
"""V810 host-only PLD/ICNSS register-to-WLFW/FW_READY boundary classifier."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore


DEFAULT_OUT_DIR = Path("tmp/wifi/v810-register-probe-wlfw-fwready-classifier")
DEFAULT_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
DEFAULT_V809_MANIFEST = Path("tmp/wifi/v809-icnss-modules-not-initialized-source-classifier/manifest.json")
DEFAULT_V808_MANIFEST = Path("tmp/wifi/v808-overlap-companion-boot-wlan/manifest.json")
DEFAULT_V806_MANIFEST = Path("tmp/wifi/v806-wlfw-service69-live-gate/manifest.json")
DEFAULT_V805_MANIFEST = Path("tmp/wifi/v805-icnss-fw-ready-wlfw-gate-classifier/manifest.json")

ICNSS = "drivers/soc/qcom/icnss.c"
ICNSS_QMI = "drivers/soc/qcom/icnss_qmi.c"
PLD_COMMON = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_common.c"
PLD_SNOC = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/pld/src/pld_snoc.c"
HDD_DRIVER_OPS = "drivers/net/wireless/qualcomm/wcn39xx/qcacld-3.0/core/hdd/src/wlan_hdd_driver_ops.c"

READ_LIMIT_BYTES = 8 * 1024 * 1024

ANCHORS: dict[str, tuple[str, str]] = {
    "hdd_register_calls_pld": (HDD_DRIVER_OPS, r"return pld_register_driver\(&wlan_drv_ops\)"),
    "pld_register_driver": (PLD_COMMON, r"int pld_register_driver\(struct pld_driver_ops \*ops\)"),
    "pld_register_calls_snoc": (PLD_COMMON, r"pld_snoc_register_driver\(\)"),
    "pld_snoc_calls_icnss": (PLD_SNOC, r"return icnss_register_driver\(&pld_snoc_ops\)"),
    "icnss_register_driver": (ICNSS, r"int __icnss_register_driver"),
    "icnss_register_posts_event": (ICNSS, r"icnss_driver_event_post\(ICNSS_DRIVER_EVENT_REGISTER_DRIVER,"),
    "icnss_event_post": (ICNSS, r"int icnss_driver_event_post"),
    "icnss_event_post_non_sync_exit": (ICNSS, r"if \(!\(flags & ICNSS_EVENT_SYNC\)\)"),
    "icnss_event_work_register_case": (ICNSS, r"ret = icnss_driver_event_register_driver\(event->data\)"),
    "icnss_register_event": (ICNSS, r"static int icnss_driver_event_register_driver"),
    "icnss_register_sets_ops": (ICNSS, r"penv->ops = data"),
    "icnss_register_requires_fw_ready": (ICNSS, r"if \(!test_bit\(ICNSS_FW_READY, &penv->state\)\)"),
    "icnss_register_probe_loop": (ICNSS, r"ret = penv->ops->probe\(&penv->pdev->dev\)"),
    "icnss_driver_probed_bit": (ICNSS, r"set_bit\(ICNSS_DRIVER_PROBED, &penv->state\)"),
    "icnss_fw_ready_event": (ICNSS, r"static int icnss_driver_event_fw_ready_ind"),
    "icnss_fw_ready_sets_bit": (ICNSS, r"set_bit\(ICNSS_FW_READY, &penv->state\)"),
    "icnss_fw_ready_log": (ICNSS, r"WLAN FW is ready"),
    "icnss_fw_ready_calls_probe": (ICNSS, r"icnss_call_driver_probe\(penv\)"),
    "wlfw_new_server": (ICNSS_QMI, r"static int wlfw_new_server"),
    "wlfw_new_server_posts_arrive": (ICNSS_QMI, r"ICNSS_DRIVER_EVENT_SERVER_ARRIVE"),
    "icnss_server_arrive": (ICNSS, r"static int icnss_driver_event_server_arrive"),
    "icnss_server_arrive_connects_qmi": (ICNSS, r"icnss_connect_to_fw_server\(penv, data\)"),
    "icnss_qmi_connected_log": (ICNSS_QMI, r"QMI Server Connected"),
}

FORBIDDEN_ACTIONS = (
    "device command",
    "custom kernel flash or boot image write",
    "partition write or reboot",
    "Wi-Fi HAL, wificond, supplicant, or hostapd start",
    "Wi-Fi scan/connect/link-up",
    "credential use",
    "DHCP, route change, or external ping",
    "boot_wlan or qcwlanstate write",
    "esoc0 open or subsystem state write",
    "bind/unbind, driver_override, or module load/unload",
)


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--v809-manifest", type=Path, default=DEFAULT_V809_MANIFEST)
    parser.add_argument("--v808-manifest", type=Path, default=DEFAULT_V808_MANIFEST)
    parser.add_argument("--v806-manifest", type=Path, default=DEFAULT_V806_MANIFEST)
    parser.add_argument("--v805-manifest", type=Path, default=DEFAULT_V805_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def safe_read(path: Path) -> tuple[str, dict[str, Any]]:
    resolved = resolve(path)
    info: dict[str, Any] = {"path": str(resolved), "exists": resolved.exists()}
    if not resolved.exists() or not resolved.is_file():
        return "", info
    data = resolved.read_bytes()[:READ_LIMIT_BYTES]
    info.update({
        "is_file": True,
        "size": resolved.stat().st_size,
        "bytes_read": len(data),
        "truncated": resolved.stat().st_size > len(data),
    })
    return data.decode("utf-8", errors="replace"), info


def load_json(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    if not text:
        return {"file": info, "data": {}}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": payload if isinstance(payload, dict) else {}}


def get_nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def line_of(text: str, pattern: str) -> int | None:
    regex = re.compile(pattern)
    for index, line in enumerate(text.splitlines(), start=1):
        if regex.search(line):
            return index
    return None


def contains(text: str, pattern: str) -> bool:
    return re.search(pattern, text, flags=re.MULTILINE | re.DOTALL) is not None


def load_sources(source_root: Path) -> dict[str, dict[str, Any]]:
    root = resolve(source_root)
    loaded: dict[str, dict[str, Any]] = {}
    for relative in sorted(set(path for path, _pattern in ANCHORS.values())):
        text, info = safe_read(root / relative)
        loaded[relative] = {"text": text, "file": info}
    return loaded


def analyze_source(args: argparse.Namespace) -> dict[str, Any]:
    sources = load_sources(args.source_root)
    anchors: dict[str, dict[str, Any]] = {}
    for name, (relative, pattern) in ANCHORS.items():
        text = str(sources.get(relative, {}).get("text") or "")
        anchors[name] = {
            "source": relative,
            "line": line_of(text, pattern),
            "pattern": pattern,
        }
    icnss = str(sources[ICNSS]["text"])
    register_is_async = contains(
        icnss,
        r"icnss_driver_event_post\(ICNSS_DRIVER_EVENT_REGISTER_DRIVER,\s*0,\s*ops\)",
    ) and contains(
        icnss,
        r"if \(!\(flags & ICNSS_EVENT_SYNC\)\)\s*goto out;",
    )
    register_defers_probe = contains(
        icnss,
        r"icnss_driver_event_register_driver.*?penv->ops = data.*?!test_bit\(ICNSS_FW_READY.*?goto out;.*?penv->ops->probe",
    )
    fw_ready_triggers_probe = contains(
        icnss,
        r"icnss_driver_event_fw_ready_ind.*?set_bit\(ICNSS_FW_READY.*?WLAN FW is ready.*?icnss_call_driver_probe\(penv\)",
    )
    wlfw_precedes_fw_ready = all(
        anchors[name]["line"]
        for name in (
            "wlfw_new_server_posts_arrive",
            "icnss_server_arrive_connects_qmi",
            "icnss_qmi_connected_log",
            "icnss_fw_ready_event",
        )
    )
    source = {
        "source_root": str(resolve(args.source_root)),
        "source_files": {relative: item["file"] for relative, item in sources.items()},
        "anchors": anchors,
        "derived": {
            "pld_snoc_register_path_present": all(
                anchors[name]["line"]
                for name in (
                    "hdd_register_calls_pld",
                    "pld_register_driver",
                    "pld_register_calls_snoc",
                    "pld_snoc_calls_icnss",
                    "icnss_register_posts_event",
                )
            ),
            "register_event_is_async": register_is_async,
            "register_event_defers_probe_until_fw_ready": register_defers_probe,
            "fw_ready_event_triggers_probe": fw_ready_triggers_probe,
            "wlfw_server_arrival_precedes_qmi_and_fw_ready": wlfw_precedes_fw_ready,
        },
    }
    return source


def summarize_manifest(label: str, path: Path) -> dict[str, Any]:
    entry = load_json(path)
    data = entry["data"]
    return {
        "label": label,
        "file": entry["file"],
        "decision": data.get("decision", ""),
        "pass": bool(data.get("pass")),
        "reason": data.get("reason", ""),
    }


def analyze_evidence(args: argparse.Namespace) -> dict[str, Any]:
    v809_entry = load_json(args.v809_manifest)
    v808_entry = load_json(args.v808_manifest)
    v806 = summarize_manifest("v806", args.v806_manifest)
    v805 = summarize_manifest("v805", args.v805_manifest)
    v809 = v809_entry["data"]
    v808 = v808_entry["data"]
    v808_counts = get_nested(v808, "live", "markers", "counts", default={})
    v808_counts = v808_counts if isinstance(v808_counts, dict) else {}
    return {
        "v809": {
            "file": v809_entry["file"],
            "decision": v809.get("decision", ""),
            "pass": bool(v809.get("pass")),
            "derived": get_nested(v809, "source", "derived", default={}),
        },
        "v808": {
            "file": v808_entry["file"],
            "decision": v808.get("decision", ""),
            "pass": bool(v808.get("pass")),
            "provider_first_context_executed": bool(v808.get("provider_first_context_executed")),
            "boot_wlan_write_executed": bool(v808.get("boot_wlan_write_executed")),
            "counts": {
                "wlan_loading": int_value(v808_counts.get("wlan_loading")),
                "qcwlanstate": int_value(v808_counts.get("qcwlanstate")),
                "wlan_driver_loaded": int_value(v808_counts.get("wlan_driver_loaded")),
                "icnss_qmi_connected": int_value(v808_counts.get("icnss_qmi_connected")),
                "fw_ready": int_value(v808_counts.get("fw_ready")),
                "wlfw": int_value(v808_counts.get("wlfw")),
                "bdf": int_value(v808_counts.get("bdf")),
                "wiphy": int_value(v808_counts.get("wiphy")),
                "wlan0": int_value(v808_counts.get("wlan0")),
                "service_notifier": int_value(v808_counts.get("service_notifier")),
                "qrtr_rx": int_value(v808_counts.get("qrtr_rx")),
                "qrtr_tx": int_value(v808_counts.get("qrtr_tx")),
            },
        },
        "v806": v806,
        "v805": v805,
    }


def build_checks(command: str, source: dict[str, Any], evidence: dict[str, Any]) -> list[dict[str, Any]]:
    if command == "plan":
        return [{
            "name": "plan-only",
            "status": "pass",
            "detail": "host-only register/probe source classifier; no device command or Wi-Fi action",
            "next_step": "run V810 host-only classifier",
        }]
    derived = source.get("derived") if isinstance(source.get("derived"), dict) else {}
    v808 = evidence["v808"]
    counts = v808.get("counts") if isinstance(v808.get("counts"), dict) else {}
    v809 = evidence["v809"]
    missing_probe_chain = not any(
        int_value(counts.get(name))
        for name in ("icnss_qmi_connected", "fw_ready", "wlfw", "bdf", "wiphy", "wlan0")
    )
    return [
        {
            "name": "v809-input-ready",
            "status": "pass"
            if v809.get("pass") and v809.get("decision") == "v809-modules-not-initialized-source-mapped"
            else "blocked",
            "detail": {"decision": v809.get("decision"), "pass": v809.get("pass")},
            "next_step": "complete V809 before V810",
        },
        {
            "name": "register-path-present",
            "status": "pass" if derived.get("pld_snoc_register_path_present") else "blocked",
            "detail": {"pld_snoc_register_path_present": derived.get("pld_snoc_register_path_present")},
            "next_step": "refresh OSRC source if PLD/SNOC/ICNSS register anchors are missing",
        },
        {
            "name": "register-defers-until-fw-ready",
            "status": "pass"
            if derived.get("register_event_is_async")
            and derived.get("register_event_defers_probe_until_fw_ready")
            and derived.get("fw_ready_event_triggers_probe")
            else "blocked",
            "detail": {
                "register_event_is_async": derived.get("register_event_is_async"),
                "register_event_defers_probe_until_fw_ready": derived.get("register_event_defers_probe_until_fw_ready"),
                "fw_ready_event_triggers_probe": derived.get("fw_ready_event_triggers_probe"),
            },
            "next_step": "do not treat qcwlanstate or register-driver as the next trigger if FW_READY gate is absent",
        },
        {
            "name": "wlfw-precedes-fw-ready",
            "status": "pass" if derived.get("wlfw_server_arrival_precedes_qmi_and_fw_ready") else "blocked",
            "detail": {"wlfw_server_arrival_precedes_qmi_and_fw_ready": derived.get("wlfw_server_arrival_precedes_qmi_and_fw_ready")},
            "next_step": "classify why WLFW service69 is absent before retrying HAL/connect",
        },
        {
            "name": "v808-matches-fw-ready-gate",
            "status": "pass"
            if v808.get("pass")
            and v808.get("decision") == "v808-overlap-service69-still-absent"
            and counts.get("wlan_loading")
            and counts.get("qcwlanstate")
            and missing_probe_chain
            else "blocked",
            "detail": {
                "decision": v808.get("decision"),
                "pass": v808.get("pass"),
                "counts": counts,
                "missing_probe_chain": missing_probe_chain,
            },
            "next_step": "if FW_READY/QMI/netdev appeared, route to post-FW_READY classifier",
        },
        {
            "name": "prior-wlfw-gate-consistent",
            "status": "pass"
            if evidence["v805"].get("pass")
            and evidence["v806"].get("pass")
            and "service69" in str(evidence["v806"].get("decision"))
            else "finding",
            "detail": {
                "v805": {"decision": evidence["v805"].get("decision"), "pass": evidence["v805"].get("pass")},
                "v806": {"decision": evidence["v806"].get("decision"), "pass": evidence["v806"].get("pass")},
            },
            "next_step": "treat V805/V806 as supporting evidence; V808/V809 remain primary",
        },
        {
            "name": "no-live-or-widening-action",
            "status": "pass",
            "detail": {
                "v810_device_commands_executed": False,
                "wifi_hal_start_executed": False,
                "scan_connect_executed": False,
                "external_ping_executed": False,
            },
            "next_step": "keep next gate below HAL/scan/connect until WLFW/FW_READY is proven",
        },
    ]


def decide(command: str, checks: list[dict[str, Any]]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return (
            "v810-register-probe-wlfw-fwready-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run V810 host-only classifier",
        )
    blocked = [check["name"] for check in checks if check["status"] == "blocked"]
    if blocked:
        return (
            "v810-register-probe-wlfw-fwready-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "clear source/evidence blocker before selecting another live gate",
        )
    return (
        "v810-register-probe-gated-by-missing-wlfw-fwready",
        True,
        "PLD/SNOC registration reaches ICNSS register as an async event, but ICNSS defers probe until FW_READY; V808 matches that gate because WLFW/service69, ICNSS-QMI, FW_READY, BDF, wiphy, and wlan0 are all absent",
        "V811 should classify the WLFW service69 publication preconditions, especially WLAN-PD/modem firmware serving and QRTR service availability, before another live trigger",
    )


def build_manifest(args: argparse.Namespace) -> dict[str, Any]:
    source = analyze_source(args)
    evidence = analyze_evidence(args)
    checks = build_checks(args.command, source, evidence)
    decision, pass_ok, reason, next_step = decide(args.command, checks)
    return {
        "generated_at": now_iso(),
        "command": args.command,
        "cycle": "v810",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "next_step": next_step,
        "host": collect_host_metadata(),
        "inputs": {
            "source_root": str(resolve(args.source_root)),
            "v809_manifest": str(resolve(args.v809_manifest)),
            "v808_manifest": str(resolve(args.v808_manifest)),
            "v806_manifest": str(resolve(args.v806_manifest)),
            "v805_manifest": str(resolve(args.v805_manifest)),
        },
        "source": source,
        "evidence": evidence,
        "checks": checks,
        "device_commands_executed": False,
        "device_mutations": False,
        "custom_kernel_flash_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "reboot_executed": False,
        "boot_wlan_write_executed": False,
        "qcwlanstate_write_executed": False,
        "esoc0_access_executed": False,
        "bind_unbind_executed": False,
        "module_load_unload_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "forbidden_actions": FORBIDDEN_ACTIONS,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    check_rows = [
        [check["name"], check["status"], json.dumps(check["detail"], sort_keys=True), check["next_step"]]
        for check in manifest["checks"]
    ]
    derived_rows = [[key, str(value)] for key, value in manifest["source"]["derived"].items()]
    anchor_rows = [
        [name, anchor["source"], str(anchor["line"]), anchor["pattern"]]
        for name, anchor in manifest["source"]["anchors"].items()
    ]
    signal_rows = [
        ["V809", json.dumps({"decision": manifest["evidence"]["v809"].get("decision"), "pass": manifest["evidence"]["v809"].get("pass")}, sort_keys=True)],
        ["V808 counts", json.dumps(manifest["evidence"]["v808"].get("counts", {}), sort_keys=True)],
        ["V805/V806", json.dumps({
            "v805": {"decision": manifest["evidence"]["v805"].get("decision"), "pass": manifest["evidence"]["v805"].get("pass")},
            "v806": {"decision": manifest["evidence"]["v806"].get("decision"), "pass": manifest["evidence"]["v806"].get("pass")},
        }, sort_keys=True)],
    ]
    return "\n".join([
        "# V810 Register/Probe WLFW/FW_READY Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- command: `{manifest['command']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        f"- device_commands_executed: `{manifest['device_commands_executed']}`",
        f"- custom_kernel_flash_executed: `{manifest['custom_kernel_flash_executed']}`",
        f"- wifi_hal_start_executed: `{manifest['wifi_hal_start_executed']}`",
        f"- scan_connect_executed: `{manifest['scan_connect_executed']}`",
        f"- external_ping_executed: `{manifest['external_ping_executed']}`",
        "",
        "## Checks",
        "",
        markdown_table(["check", "status", "detail", "next"], check_rows),
        "",
        "## Evidence Signals",
        "",
        markdown_table(["source", "signals"], signal_rows),
        "",
        "## Source Derived Facts",
        "",
        markdown_table(["fact", "value"], derived_rows),
        "",
        "## Source Anchors",
        "",
        markdown_table(["anchor", "source", "line", "pattern"], anchor_rows),
        "",
        "## Guardrails",
        "",
        "\n".join(f"- {item}" for item in manifest["forbidden_actions"]),
        "",
    ])


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"custom_kernel_flash_executed: {manifest['custom_kernel_flash_executed']}")
    print(f"wifi_hal_start_executed: {manifest['wifi_hal_start_executed']}")
    print(f"scan_connect_executed: {manifest['scan_connect_executed']}")
    print(f"credential_use_executed: {manifest['credential_use_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    print(f"evidence: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
