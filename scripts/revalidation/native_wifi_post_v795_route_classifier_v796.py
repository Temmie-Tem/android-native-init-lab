#!/usr/bin/env python3
"""V796 host-only post-V795 route classifier.

V795 showed that the firmware-backed subsys_modem holder brings mss ONLINE and
QRTR RX, but mdm3/esoc0 and WLFW publication do not advance.  This classifier
reconciles V795 with the current CNSS, BPF, memshare, and mdm_helper evidence to
select the next smallest gate toward native Wi-Fi readiness.  It does not
contact the device.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from a90_kernel_tools import collect_host_metadata, markdown_table, repo_path
from a90harness.evidence import EvidenceStore, write_private_text


DEFAULT_OUT_DIR = Path("tmp/wifi/v796-post-v795-route-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v796-post-v795-route-classifier.txt")
DEFAULT_V795_MANIFEST = Path("tmp/wifi/v795-lower-window-mdm3-esoc-observer/manifest.json")
DEFAULT_V792_MANIFEST = Path("tmp/wifi/v792-known-asoc-warning-cnss-wlfw/manifest.json")
DEFAULT_V782_MANIFEST = Path("tmp/wifi/v782-bpf-counter-boot-wlan/manifest.json")
DEFAULT_V785_MANIFEST = Path("tmp/wifi/v785-android-native-memshare-delta/manifest.json")
DEFAULT_V764_MANIFEST = Path("tmp/wifi/v764-mdm-helper-service180-retry/manifest.json")
DEFAULT_V768_MANIFEST = Path("tmp/wifi/v768-mdm3-esoc-gap-classifier/manifest.json")
DEFAULT_V777_REPORT = Path("docs/reports/NATIVE_INIT_V777_TRACEPOINT_FORMAT_CLASSIFIER_2026-05-25.md")
DEFAULT_V781_REPORT = Path("docs/reports/NATIVE_INIT_V781_BPF_IDLE_ATTACH_2026-05-25.md")
READ_LIMIT_BYTES = 8 * 1024 * 1024


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    severity: str
    detail: str
    evidence: list[str]
    next_step: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v795-manifest", type=Path, default=DEFAULT_V795_MANIFEST)
    parser.add_argument("--v792-manifest", type=Path, default=DEFAULT_V792_MANIFEST)
    parser.add_argument("--v782-manifest", type=Path, default=DEFAULT_V782_MANIFEST)
    parser.add_argument("--v785-manifest", type=Path, default=DEFAULT_V785_MANIFEST)
    parser.add_argument("--v764-manifest", type=Path, default=DEFAULT_V764_MANIFEST)
    parser.add_argument("--v768-manifest", type=Path, default=DEFAULT_V768_MANIFEST)
    parser.add_argument("--v777-report", type=Path, default=DEFAULT_V777_REPORT)
    parser.add_argument("--v781-report", type=Path, default=DEFAULT_V781_REPORT)
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
        return {"path": info["path"], "exists": False}
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"path": info["path"], "exists": True, "invalid": str(exc)}
    if not isinstance(payload, dict):
        return {"path": info["path"], "exists": True, "invalid": "json-root-not-object"}
    payload.setdefault("path", info["path"])
    payload.setdefault("exists", True)
    return payload


def read_report(path: Path) -> dict[str, Any]:
    text, info = safe_read(path)
    return {
        "file": info,
        "text": text,
        "has_pil_fields": all(token in text for token in ("event_name", "code", "fw_name")),
        "bpf_idle_attach_pass": "v781-bpf-idle-attach-detach-pass" in text and "attach-detach-pass" in text,
    }


def get_nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def marker_counts(payload: dict[str, Any]) -> dict[str, int]:
    markers = payload.get("markers") if isinstance(payload, dict) else {}
    if isinstance(markers, dict) and isinstance(markers.get("counts"), dict):
        markers = markers["counts"]
    if not isinstance(markers, dict):
        return {}
    return {str(key): int_value(value) for key, value in markers.items()}


def extract_facts(inputs: dict[str, Any]) -> dict[str, Any]:
    v795_live = inputs["v795"].get("live") or {}
    v792_live = get_nested(inputs["v792"], "lower_readback", "live", default={}) or {}
    v782_live = inputs["v782"].get("live") or {}
    v785_analysis = inputs["v785"].get("analysis") or {}
    v764 = inputs["v764"]
    v768_analysis = inputs["v768"].get("analysis") or {}
    v795_markers = marker_counts(v795_live)
    v792_markers = marker_counts(v792_live)
    v782_markers = marker_counts(v782_live)
    v795_services = v795_live.get("qrtr_services_after_holder") or {}
    v792_services = v792_live.get("qrtr_services_after_companion") or {}
    v782_services = v782_live.get("qrtr_services_after_boot") or {}
    return {
        "v795": {
            "decision": inputs["v795"].get("decision"),
            "pass": inputs["v795"].get("pass"),
            "holder_opened": bool(v795_live.get("holder_opened")),
            "mss_after_holder": v795_live.get("mss_after_holder"),
            "mdm3_after_holder": v795_live.get("mdm3_after_holder"),
            "esoc0_state": get_nested(v795_live, "surface", "esoc0_subsys_state", default=""),
            "qrtr_rx": bool((v795_live.get("qrtr_rx_wait") or {}).get("seen")),
            "service69": int_value(v795_services.get("69")),
            "service74": int_value(v795_services.get("74")),
            "service180": int_value(v795_services.get("180")),
            "wlfw": int_value(v795_markers.get("wlfw")),
            "bdf": int_value(v795_markers.get("bdf")),
            "wlan0": bool(get_nested(v795_live, "surface", "wlan0_visible", default=False)),
        },
        "v792": {
            "decision": inputs["v792"].get("decision"),
            "pass": inputs["v792"].get("pass"),
            "order": get_nested(v792_live, "helper", "order", default=""),
            "cnss_diag": bool(get_nested(v792_live, "helper", "cnss_diag", default=0)),
            "cnss_daemon": bool(get_nested(v792_live, "helper", "cnss_daemon", default=0)),
            "service_manager": bool(get_nested(v792_live, "helper", "service_manager", default=0)),
            "wifi_hal": bool(get_nested(v792_live, "helper", "wifi_hal", default=0)),
            "service_notifier": int_value(v792_markers.get("service_notifier")),
            "sysmon_qmi": int_value(v792_markers.get("sysmon_qmi")),
            "mss_final": (v792_live.get("mss") or [""])[-1],
            "mdm3_final": (v792_live.get("mdm3") or [""])[-1],
            "service69": int_value(v792_services.get("69")),
            "service74": int_value(v792_services.get("74")),
            "service180": int_value(v792_services.get("180")),
            "wlfw": int_value(v792_markers.get("wlfw")),
            "bdf": int_value(v792_markers.get("bdf")),
            "wlan0": int_value(v792_markers.get("wlan0")),
        },
        "v782": {
            "decision": inputs["v782"].get("decision"),
            "pass": inputs["v782"].get("pass"),
            "bpf_event_count": int_value(v782_live.get("bpf_event_count")),
            "bpf_result": get_nested(v782_live, "bpf_counter_result", "result", default=""),
            "boot_wlan_write_executed": bool(v782_live.get("boot_wlan_write_executed")),
            "mss_after_boot": v782_live.get("mss_after_boot"),
            "mdm3_after_boot": v782_live.get("mdm3_after_boot"),
            "service69": int_value(v782_services.get("69")),
            "service74": int_value(v782_services.get("74")),
            "service180": int_value(v782_services.get("180")),
            "qcwlanstate_after": bool(v782_live.get("qcwlanstate_after")),
            "wiphy_after": bool(v782_live.get("wiphy_after")),
            "wlan0_after": bool(v782_live.get("wlan0_after")),
            "wlfw": int_value(v782_markers.get("wlfw")),
            "bdf": int_value(v782_markers.get("bdf")),
        },
        "v785": {
            "decision": inputs["v785"].get("decision"),
            "pass": inputs["v785"].get("pass"),
            "comparison": v785_analysis.get("comparison") or {},
        },
        "v764": {
            "decision": v764.get("decision"),
            "pass": v764.get("pass"),
            "mdm_helper_start_executed": bool(v764.get("mdm_helper_start_executed")),
            "esoc0_open_executed": bool(v764.get("esoc0_open_executed")),
            "wifi_hal_start_executed": bool(v764.get("wifi_hal_start_executed")),
            "external_ping_executed": bool(v764.get("external_ping_executed")),
        },
        "v768": {
            "decision": inputs["v768"].get("decision"),
            "pass": inputs["v768"].get("pass"),
            "derived": v768_analysis.get("derived") or {},
        },
    }


def build_checks(args: argparse.Namespace,
                 inputs: dict[str, Any],
                 facts: dict[str, Any],
                 reports: dict[str, Any]) -> list[Check]:
    input_paths = [
        args.v795_manifest,
        args.v792_manifest,
        args.v782_manifest,
        args.v785_manifest,
        args.v764_manifest,
        args.v768_manifest,
    ]
    checks: list[Check] = []
    checks.append(Check(
        "inputs-present",
        "pass" if all(inputs[name].get("exists") and not inputs[name].get("invalid") for name in inputs) else "blocked",
        "blocker",
        ", ".join(f"{name}={inputs[name].get('decision')} pass={inputs[name].get('pass')}" for name in inputs),
        [str(resolve(path)) for path in input_paths],
        "restore required manifests before routing V796",
    ))
    checks.append(Check(
        "current-v795-blocker",
        "pass" if facts["v795"]["pass"] and facts["v795"]["holder_opened"] and facts["v795"]["mss_after_holder"] == "ONLINE" and facts["v795"]["mdm3_after_holder"] == "OFFLINING" and facts["v795"]["service69"] == 0 and not facts["v795"]["wlan0"] else "blocked",
        "blocker",
        json.dumps(facts["v795"], sort_keys=True),
        [str(resolve(args.v795_manifest))],
        "rerun V795 if lower-window holder result is stale or ambiguous",
    ))
    checks.append(Check(
        "cnss-continuation-still-absent",
        "pass" if facts["v792"]["pass"] and facts["v792"]["service_notifier"] >= 2 and facts["v792"]["sysmon_qmi"] >= 1 and facts["v792"]["service69"] == 0 and facts["v792"]["wlfw"] == 0 and facts["v792"]["wlan0"] == 0 else "blocked",
        "blocker",
        json.dumps(facts["v792"], sort_keys=True),
        [str(resolve(args.v792_manifest))],
        "recapture CNSS readback only if service-notifier/WLFW evidence is ambiguous",
    ))
    checks.append(Check(
        "pil-observer-counted-no-payload",
        "pass" if facts["v782"]["pass"] and facts["v782"]["bpf_event_count"] > 0 and facts["v782"]["service69"] == 0 and not facts["v782"]["wlan0_after"] else "blocked",
        "blocker",
        json.dumps(facts["v782"], sort_keys=True),
        [str(resolve(args.v782_manifest))],
        "capture PIL event names/codes before another trigger retry",
    ))
    checks.append(Check(
        "demoted-branches",
        "pass" if facts["v764"]["mdm_helper_start_executed"] and not facts["v764"]["esoc0_open_executed"] and facts["v785"]["decision"] == "v785-memshare-common-nonfatal-sibling-sysmon-gap" and facts["v768"]["decision"] == "v768-mdm3-esoc-gap-rerouted-to-instrumentation-packaging" else "blocked",
        "blocker",
        f"v764={facts['v764']} v785={facts['v785']['decision']} v768={facts['v768']['decision']}",
        [str(resolve(args.v764_manifest)), str(resolve(args.v785_manifest)), str(resolve(args.v768_manifest))],
        "do not repeat mdm_helper, memshare-only, or raw esoc branches without new evidence",
    ))
    checks.append(Check(
        "payload-capture-feasible",
        "pass" if reports["v777"].get("has_pil_fields") and reports["v781"].get("bpf_idle_attach_pass") else "blocked",
        "blocker",
        f"pil_fields={reports['v777'].get('has_pil_fields')} bpf_idle_attach={reports['v781'].get('bpf_idle_attach_pass')}",
        [str(resolve(args.v777_report)), str(resolve(args.v781_report))],
        "verify tracepoint fields and attach feasibility before a payload gate",
    ))
    checks.append(Check(
        "v796-host-only",
        "pass",
        "blocker",
        "no device command, mount, trace control write, daemon start, Wi-Fi action, reboot, flash, or partition write",
        [],
        "keep route classifier host-only",
    ))
    return checks


def decide(args: argparse.Namespace, checks: list[Check], facts: dict[str, Any]) -> tuple[str, bool, str, str]:
    if args.command == "plan":
        return (
            "v796-post-v795-route-classifier-plan-ready",
            True,
            "plan-only; no device command executed",
            "run host-only V796 route classifier",
        )
    blocked = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blocked:
        return (
            "v796-post-v795-route-classifier-blocked",
            False,
            "blocked by " + ", ".join(blocked),
            "repair input evidence before selecting next live gate",
        )
    return (
        "v796-pil-notif-payload-capture-selected",
        True,
        "mss/QRTR/PIL movement is proven but mdm3/service69/WLFW remain absent; counted PIL events need event_name/code/fw_name payload before another trigger retry",
        "plan V797 bounded tracefs/BPF PIL payload capture around the already-tested lower-window transition; still no HAL, scan/connect, DHCP, external ping, custom kernel, or raw esoc0",
    )


def render_summary(manifest: dict[str, Any]) -> str:
    facts = manifest["facts"]
    rows = [
        ["V795 holder-only", facts["v795"]["mss_after_holder"], facts["v795"]["mdm3_after_holder"], facts["v795"]["service69"], facts["v795"]["wlfw"], facts["v795"]["wlan0"], "holder proves mss/QRTR but not mdm3"],
        ["V792 CNSS readback", facts["v792"]["mss_final"], facts["v792"]["mdm3_final"], facts["v792"]["service69"], facts["v792"]["wlfw"], facts["v792"]["wlan0"], "service 180/74 and CNSS still no WLFW"],
        ["V782 BPF boot_wlan", facts["v782"]["mss_after_boot"], facts["v782"]["mdm3_after_boot"], facts["v782"]["service69"], facts["v782"]["wlfw"], facts["v782"]["wlan0_after"], f"PIL count={facts['v782']['bpf_event_count']} but no payload"],
    ]
    return "\n".join([
        "# V796 Post-V795 Route Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Evidence Matrix",
        "",
        markdown_table(["source", "mss", "mdm3", "service69", "WLFW", "wlan0", "interpretation"], rows),
        "",
        "## Demoted Branches",
        "",
        markdown_table(["branch", "classification"], [
            ["mdm_helper", f"started={facts['v764']['mdm_helper_start_executed']} no raw esoc0={not facts['v764']['esoc0_open_executed']}"],
            ["memshare/CMA", facts["v785"]["decision"]],
            ["custom-kernel/esoc retry", facts["v768"]["decision"]],
        ]),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[check["name"], check["status"], check["severity"], check["detail"], check["next_step"]] for check in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- V796 is host-only.",
        "- No device command, reboot, mount, daemon start, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, boot image write, partition write, custom kernel flash, or raw esoc0 access.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    inputs = {
        "v795": load_json(args.v795_manifest),
        "v792": load_json(args.v792_manifest),
        "v782": load_json(args.v782_manifest),
        "v785": load_json(args.v785_manifest),
        "v764": load_json(args.v764_manifest),
        "v768": load_json(args.v768_manifest),
    }
    reports = {
        "v777": read_report(args.v777_report),
        "v781": read_report(args.v781_report),
    }
    facts = extract_facts(inputs)
    checks = build_checks(args, inputs, facts, reports)
    decision, passed, reason, next_step = decide(args, checks, facts)
    manifest = {
        "cycle": "v796",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "inputs": {name: {"path": payload.get("path"), "exists": payload.get("exists"), "decision": payload.get("decision"), "pass": payload.get("pass")} for name, payload in inputs.items()},
        "report_inputs": {name: {"path": payload.get("file", {}).get("path"), "exists": payload.get("file", {}).get("exists")} for name, payload in reports.items()},
        "facts": facts,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "device_mutations": False,
        "trace_control_write_executed": False,
        "daemon_start_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "boot_wlan_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "esoc0_access_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = build_manifest(args, store)
    write_private_text(repo_path(LATEST_POINTER), str(store.run_dir.relative_to(repo_path("."))) + "\n")
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"next: {manifest['next_step']}")
    print(f"evidence: {store.run_dir}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"external_ping_executed: {manifest['external_ping_executed']}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
