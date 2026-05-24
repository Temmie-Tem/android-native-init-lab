#!/usr/bin/env python3
"""V798 host-only PIL code and Android/native gap classifier.

V797 captured real msm_pil_event:pil_notif payloads.  This classifier maps the
observed code values back to the Samsung OSRC enum and reconciles that sequence
with the existing Android/native gap evidence.  It does not contact the device.
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


DEFAULT_OUT_DIR = Path("tmp/wifi/v798-pil-code-gap-classifier")
LATEST_POINTER = Path("tmp/wifi/latest-v798-pil-code-gap-classifier.txt")
DEFAULT_SOURCE_ROOT = Path("tmp/wifi/v766-icnss-qcacld-patch-apply-build/source")
DEFAULT_V797_MANIFEST = Path("tmp/wifi/v797-pil-trace-payload/manifest.json")
DEFAULT_V783_MANIFEST = Path("tmp/wifi/v783-android-native-pil-gap/manifest.json")
READ_LIMIT_BYTES = 8 * 1024 * 1024

SOURCE_FILES = {
    "subsystem_notif": Path("include/soc/qcom/subsystem_notif.h"),
    "trace_msm_pil_event": Path("include/trace/events/trace_msm_pil_event.h"),
    "subsystem_restart": Path("drivers/soc/qcom/subsystem_restart.c"),
    "sysmon_qmi": Path("drivers/soc/qcom/sysmon-qmi.c"),
    "service_notifier": Path("drivers/soc/qcom/service-notifier.c"),
    "icnss": Path("drivers/soc/qcom/icnss.c"),
    "memshare": Path("drivers/soc/qcom/memshare/msm_memshare.c"),
}


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
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--v797-manifest", type=Path, default=DEFAULT_V797_MANIFEST)
    parser.add_argument("--v783-manifest", type=Path, default=DEFAULT_V783_MANIFEST)
    parser.add_argument("command", choices=("plan", "run"), nargs="?", default="run")
    return parser.parse_args()


def resolve(path: Path) -> Path:
    return path if path.is_absolute() else repo_path(path)


def source_path(args: argparse.Namespace, key: str) -> Path:
    return resolve(args.source_root) / SOURCE_FILES[key]


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
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {"file": info, "data": {}, "error": str(exc)}
    return {"file": info, "data": data if isinstance(data, dict) else {}}


def get_nested(payload: dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def parse_enum_subsys_notif(text: str) -> dict[str, Any]:
    match = re.search(r"enum\s+subsys_notif_type\s*\{(?P<body>.*?)\};", text, re.S)
    if not match:
        return {"found": False, "values": {}, "ordered": []}
    value = 0
    values: dict[str, int] = {}
    ordered: list[dict[str, Any]] = []
    for raw in match.group("body").splitlines():
        item = raw.split("/*", 1)[0].split("//", 1)[0].strip().rstrip(",")
        if not item:
            continue
        if "=" in item:
            name, assigned = [part.strip() for part in item.split("=", 1)]
            try:
                value = int(assigned, 0)
            except ValueError:
                continue
        else:
            name = item.strip()
        if not re.fullmatch(r"[A-Z0-9_]+", name):
            continue
        values[name] = value
        ordered.append({"name": name, "value": value})
        value += 1
    return {"found": True, "values": values, "ordered": ordered}


def read_snippet(path: Path, start: int, end: int) -> str:
    text, _ = safe_read(path)
    lines = text.splitlines()
    selected = []
    for line_no in range(start, min(end, len(lines)) + 1):
        selected.append(f"{line_no:5d}: {lines[line_no - 1]}")
    return "\n".join(selected) + "\n"


def write_source_snippets(args: argparse.Namespace, store: EvidenceStore) -> dict[str, str]:
    snippets = {
        "subsystem_notif_enum": ("subsystem_notif", 22, 33),
        "trace_pil_notif_format": ("trace_msm_pil_event", 43, 66),
        "subsystem_restart_notif_emit": ("subsystem_restart", 676, 723),
        "subsystem_restart_start_order": ("subsystem_restart", 899, 935),
        "sysmon_qmi_notif_map": ("sysmon_qmi", 82, 88),
        "service_notifier_new_server": ("service_notifier", 327, 339),
        "icnss_service_notifier_registration": ("icnss", 1971, 2032),
        "memshare_modem_after_powerup": ("memshare", 541, 600),
    }
    out: dict[str, str] = {}
    for name, (source_key, start, end) in snippets.items():
        rel = f"source/{name}.txt"
        store.write_text(rel, read_snippet(source_path(args, source_key), start, end))
        out[name] = rel
    return out


def extract_fw_name(event: dict[str, Any]) -> str:
    fw = str(event.get("fw_name") or "")
    if fw:
        return fw
    line = str(event.get("line") or "")
    match = re.search(r"\bfw(?:_name)?[=:]\s*([^,\s]+)", line)
    return match.group(1).strip() if match else ""


def v797_events(v797: dict[str, Any], code_names: dict[int, str]) -> list[dict[str, Any]]:
    events = get_nested(v797, "live", "trace_payload", "events", default=[]) or []
    mapped: list[dict[str, Any]] = []
    for index, event in enumerate(events, start=1):
        code_text = str(event.get("code") or "")
        try:
            code = int(code_text, 0)
        except ValueError:
            code = None
        mapped.append({
            "index": index,
            "event_name": event.get("event_name") or "",
            "code": code,
            "code_name": code_names.get(code or -1, "UNKNOWN"),
            "fw_name": extract_fw_name(event),
            "line": event.get("line") or "",
        })
    return mapped


def pair_status(mapped: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, set[str]] = {}
    fw_names = sorted({event["fw_name"] for event in mapped if event.get("fw_name")})
    for event in mapped:
        grouped.setdefault(event["code_name"], set()).add(event["event_name"])
    expected = ("SUBSYS_BEFORE_POWERUP", "SUBSYS_AFTER_POWERUP", "SUBSYS_PROXY_VOTE", "SUBSYS_PROXY_UNVOTE")
    complete = {
        name: {"before_send_notif", "after_send_notif"}.issubset(grouped.get(name, set()))
        for name in expected
    }
    return {
        "fw_names": fw_names,
        "observed_code_names": [event["code_name"] for event in mapped],
        "unique_code_names": sorted({event["code_name"] for event in mapped}),
        "paired": complete,
        "modem_powerup_complete": complete["SUBSYS_BEFORE_POWERUP"] and complete["SUBSYS_AFTER_POWERUP"] and fw_names == ["modem"],
        "proxy_vote_cycle_seen": complete["SUBSYS_PROXY_VOTE"] and complete["SUBSYS_PROXY_UNVOTE"],
    }


def marker_count(markers: dict[str, Any], key: str) -> int:
    item = markers.get(key) if isinstance(markers, dict) else None
    if isinstance(item, dict):
        try:
            return int(item.get("count") or 0)
        except (TypeError, ValueError):
            return 0
    try:
        return int(item or 0)
    except (TypeError, ValueError):
        return 0


def extract_android_native_gap(v783: dict[str, Any], v797: dict[str, Any]) -> dict[str, Any]:
    analysis = v783.get("analysis") or {}
    android = analysis.get("android") or {}
    native = analysis.get("native") or {}
    comparison = analysis.get("comparison") or {}
    selected = android.get("selected_reference") or comparison.get("selected_reference")
    selected_ref = android.get("v649") if selected == "android-v649" else android.get("v519")
    if not selected_ref:
        selected_ref = android.get("v649") or android.get("v519") or {}
    android_markers = selected_ref.get("markers") or {}
    native_v782 = native.get("v782") or {}
    native_markers = native_v782.get("markers") or {}
    v797_markers = get_nested(v797, "live", "markers", "counts", default={}) or {}
    return {
        "selected_android_reference": selected,
        "android_mss_state": get_nested(android, "lower_state", "mss_state", default=""),
        "android_mdm3_state": get_nested(android, "lower_state", "mdm3_state", default=""),
        "native_v797_mss": [
            get_nested(v797, "live", "mss_before", default=""),
            get_nested(v797, "live", "mss_after_holder", default=""),
            get_nested(v797, "live", "mss_after_boot", default=""),
        ],
        "native_v797_mdm3": [
            get_nested(v797, "live", "mdm3_before", default=""),
            get_nested(v797, "live", "mdm3_after_holder", default=""),
            get_nested(v797, "live", "mdm3_after_boot", default=""),
        ],
        "android_service_notifier_74": marker_count(android_markers, "service_notifier_74"),
        "android_service_notifier_180": marker_count(android_markers, "service_notifier_180"),
        "android_wlan_pd": marker_count(android_markers, "wlan_pd_ind"),
        "android_icnss_qmi": marker_count(android_markers, "icnss_qmi"),
        "android_bdf_regdb": marker_count(android_markers, "bdf_regdb"),
        "android_wlan_fw_ready": marker_count(android_markers, "wlan_fw_ready"),
        "android_wlan0": marker_count(android_markers, "wlan0"),
        "native_v782_service_notifier_74": marker_count(native_markers, "service_notifier_74"),
        "native_v782_service_notifier_180": marker_count(native_markers, "service_notifier_180"),
        "native_v782_memshare_fail": marker_count(native_markers, "memshare_fail"),
        "native_v797_service_notifier": int(v797_markers.get("service_notifier") or 0),
        "native_v797_sysmon_qmi": int(v797_markers.get("sysmon_qmi") or 0),
        "native_v797_service69": int((get_nested(v797, "live", "qrtr_services_after_boot", default={}) or {}).get("69") or 0),
        "native_v797_wlan0": bool(get_nested(v797, "live", "wlan0_after", default=False)),
        "native_v797_wiphy": bool(get_nested(v797, "live", "wiphy_after", default=False)),
    }


def build_analysis(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    source_infos: dict[str, Any] = {}
    for key in SOURCE_FILES:
        _, info = safe_read(source_path(args, key))
        source_infos[key] = info
    v797 = load_json(args.v797_manifest)
    v783 = load_json(args.v783_manifest)
    enum_text, _ = safe_read(source_path(args, "subsystem_notif"))
    enum = parse_enum_subsys_notif(enum_text)
    code_names = {int(item["value"]): str(item["name"]) for item in enum.get("ordered", [])}
    mapped = v797_events(v797["data"], code_names)
    pairs = pair_status(mapped)
    gap = extract_android_native_gap(v783["data"], v797["data"])
    snippets = write_source_snippets(args, store)
    return {
        "source_files": source_infos,
        "snippets": snippets,
        "v797_file": v797["file"],
        "v783_file": v783["file"],
        "subsys_notif_enum": enum,
        "mapped_v797_events": mapped,
        "pair_status": pairs,
        "gap": gap,
        "derived": {
            "modem_pil_sequence_complete": pairs["modem_powerup_complete"] and pairs["proxy_vote_cycle_seen"],
            "service_notifier_gap_after_modem_powerup": (
                pairs["modem_powerup_complete"]
                and gap["native_v797_sysmon_qmi"] > 0
                and gap["native_v797_service_notifier"] == 0
                and gap["android_service_notifier_74"] > 0
                and gap["android_service_notifier_180"] > 0
            ),
            "mdm3_gap_remains": gap["android_mdm3_state"] == "ONLINE" and gap["native_v797_mdm3"][-1] != "ONLINE",
            "wl_fw_absent": gap["native_v797_service69"] == 0 and not gap["native_v797_wlan0"] and not gap["native_v797_wiphy"],
        },
    }


def build_checks(command: str, analysis: dict[str, Any]) -> list[Check]:
    if command == "plan":
        return [Check("plan-only", "pass", "info", "no device command executed", [], "run host-only classifier")]
    enum = analysis["subsys_notif_enum"]
    derived = analysis["derived"]
    gap = analysis["gap"]
    required_sources = [key for key, info in analysis["source_files"].items() if not info.get("exists")]
    return [
        Check("source-inputs", "pass" if not required_sources else "blocked", "blocker", ",".join(required_sources), list(analysis["snippets"].values()), "restore staged OSRC source files"),
        Check("enum-map", "pass" if enum.get("found") and {"SUBSYS_BEFORE_POWERUP", "SUBSYS_AFTER_POWERUP", "SUBSYS_PROXY_VOTE", "SUBSYS_PROXY_UNVOTE"}.issubset((enum.get("values") or {}).keys()) else "blocked", "blocker", json.dumps(enum.get("ordered", [])[:10]), [analysis["snippets"]["subsystem_notif_enum"]], "repair enum parser or source path"),
        Check("v797-sequence", "pass" if derived["modem_pil_sequence_complete"] else "blocked", "blocker", json.dumps(analysis["pair_status"], sort_keys=True), ["v797_file"], "do not classify gap until V797 has a complete modem powerup sequence"),
        Check("android-native-gap", "pass" if derived["service_notifier_gap_after_modem_powerup"] and derived["mdm3_gap_remains"] else "blocked", "blocker", json.dumps(gap, sort_keys=True), ["v783_file", "v797_file"], "refresh Android/native comparison if evidence is stale"),
        Check("wifi-still-gated", "pass" if derived["wl_fw_absent"] else "advanced", "info", json.dumps({"service69": gap["native_v797_service69"], "wlan0": gap["native_v797_wlan0"], "wiphy": gap["native_v797_wiphy"]}, sort_keys=True), ["v797_file"], "if advanced, stop before credentials and capture interface state"),
        Check("safety", "pass", "blocker", "host-only; no device command, flash, reboot, HAL, scan/connect, credential, DHCP, or external ping", [], "preserve V798 boundary"),
    ]


def decide(command: str, checks: list[Check], analysis: dict[str, Any]) -> tuple[str, bool, str, str]:
    if command == "plan":
        return "v798-pil-code-gap-classifier-plan-ready", True, "plan-only; no device command executed", "run host-only classifier"
    blocked = [check.name for check in checks if check.severity == "blocker" and check.status != "pass"]
    if blocked:
        return "v798-pil-code-gap-classifier-blocked", False, "blocked by " + ", ".join(blocked), "repair host inputs before continuing"
    if analysis["derived"]["service_notifier_gap_after_modem_powerup"]:
        return (
            "v798-modem-pil-complete-service-notifier-mdm3-gap-classified",
            True,
            "V797 proves modem PIL powerup/proxy notifications complete, but native still lacks service-notifier 74/180, mdm3 ONLINE, service69, wiphy, and wlan0 while Android has the service-notifier/WLAN-PD chain",
            "V799 should classify service-notifier registration/root-PD state around the lower window before another Wi-Fi trigger",
        )
    return "v798-pil-code-gap-classifier-inconclusive", False, "host evidence did not identify a single next gap", "refresh V797/V783 evidence"


def render_summary(manifest: dict[str, Any]) -> str:
    analysis = manifest["analysis"]
    gap = analysis["gap"]
    mapped_rows = [
        [event["index"], event["event_name"], event["code"], event["code_name"], event["fw_name"]]
        for event in analysis["mapped_v797_events"]
    ]
    enum_rows = [[item["value"], item["name"]] for item in analysis["subsys_notif_enum"].get("ordered", [])]
    if not gap:
        gap = {
            "android_mdm3_state": "",
            "native_v797_mdm3": [],
            "android_service_notifier_74": "",
            "android_service_notifier_180": "",
            "native_v797_service_notifier": "",
            "native_v797_sysmon_qmi": "",
            "native_v797_service69": "",
            "native_v797_wlan0": "",
            "native_v797_wiphy": "",
            "native_v782_memshare_fail": "",
        }
    native_v797_mdm3 = gap.get("native_v797_mdm3") or []
    return "\n".join([
        "# V798 PIL Code Gap Classifier",
        "",
        f"- generated: `{manifest['generated_at']}`",
        f"- decision: `{manifest['decision']}`",
        f"- pass: `{manifest['pass']}`",
        f"- reason: {manifest['reason']}",
        f"- next_step: {manifest['next_step']}",
        "",
        "## Subsystem Notification Enum",
        "",
        markdown_table(["code", "name"], enum_rows),
        "",
        "## V797 Mapped Sequence",
        "",
        markdown_table(["index", "event", "code", "enum", "fw"], mapped_rows),
        "",
        "## Android/Native Gap",
        "",
        markdown_table(["signal", "value"], [
            ["Android mdm3", gap["android_mdm3_state"]],
            ["Native V797 mdm3", " -> ".join(native_v797_mdm3)],
            ["Android service-notifier 74/180", f"{gap['android_service_notifier_74']} / {gap['android_service_notifier_180']}"],
            ["Native V797 service-notifier", gap["native_v797_service_notifier"]],
            ["Native V797 sysmon_qmi", gap["native_v797_sysmon_qmi"]],
            ["Native V797 service69/wlan0/wiphy", f"{gap['native_v797_service69']} / {gap['native_v797_wlan0']} / {gap['native_v797_wiphy']}"],
            ["Native V782 memshare_fail", gap["native_v782_memshare_fail"]],
        ]),
        "",
        "## Checks",
        "",
        markdown_table(["name", "status", "severity", "detail", "next"], [[check["name"], check["status"], check["severity"], check["detail"], check["next_step"]] for check in manifest["checks"]]),
        "",
        "## Safety",
        "",
        "- Host-only classifier. No device command executed.",
        "- No service-manager, Wi-Fi HAL, scan/connect, credentials, DHCP/routes, external ping, raw `esoc0`, boot image write, partition write, reboot, or custom kernel flash.",
    ])


def build_manifest(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    if args.command == "plan":
        analysis: dict[str, Any] = {
            "source_files": {},
            "snippets": {},
            "subsys_notif_enum": {"ordered": []},
            "mapped_v797_events": [],
            "pair_status": {},
            "gap": {},
            "derived": {},
        }
    else:
        analysis = build_analysis(args, store)
    checks = build_checks(args.command, analysis)
    decision, passed, reason, next_step = decide(args.command, checks, analysis)
    manifest = {
        "cycle": "v798",
        "generated_at": now_iso(),
        "command": args.command,
        "decision": decision,
        "pass": passed,
        "reason": reason,
        "next_step": next_step,
        "analysis": analysis,
        "checks": [asdict(check) for check in checks],
        "device_commands_executed": False,
        "service_manager_start_executed": False,
        "wifi_hal_start_executed": False,
        "scan_connect_executed": False,
        "credential_use_executed": False,
        "dhcp_route_executed": False,
        "external_ping_executed": False,
        "reboot_executed": False,
        "boot_image_write_executed": False,
        "partition_write_executed": False,
        "custom_kernel_flash_executed": False,
        "host": collect_host_metadata(),
    }
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    return manifest


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    store.mkdir("source")
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
