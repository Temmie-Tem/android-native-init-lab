#!/usr/bin/env python3
"""V426 host-only mapper for Android Wi-Fi service surface and native gaps.

The mapper consumes V425/V423 evidence captured from a boot-complete Android
handoff.  It does not execute ADB, mutate the device, start daemons, or perform
Wi-Fi bring-up.  Its job is to turn the captured text into a small decision
packet that separates Android baseline surface from the native private-runtime
gap seen in V422/V407.
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
from a90harness.evidence import EvidenceStore
from wifi_android_hwservice_inventory_v423 import TARGETED_WAIT_TARGETS


DEFAULT_OUT_DIR = Path("tmp/wifi/v426-service-surface-mapper")
DEFAULT_V425_PATTERN = "v425-settled-handoff-live-*"
WIFI_RE = re.compile(r"wifi|wlan|wificond|supplicant|hostapd|cnss|IWifi|ISehWifi", re.IGNORECASE)
SERVICE_LINE_RE = re.compile(r"^\s*(?P<index>\d+)\s+(?P<name>[A-Za-z0-9_.-]+):\s+\[(?P<iface>[^\]]*)\]")
PROP_RE = re.compile(r"^(?P<key>[A-Za-z0-9_.-]+)=(?P<value>.*)$")
PROCESS_NAME_RE = re.compile(r"\s(?P<name>[A-Za-z0-9_.@/-]*(?:wifi|wlan|wificond|supplicant|hostapd|cnss)[A-Za-z0-9_.@/-]*)$", re.IGNORECASE)


@dataclass
class SurfaceItem:
    name: str
    present: bool
    source: str
    detail: str


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--v425-manifest", type=Path, default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("plan")
    subparsers.add_parser("run")
    return parser.parse_args()


def latest_manifest(pattern: str) -> Path | None:
    candidates = sorted(repo_path("tmp/wifi").glob(pattern), key=lambda path: path.stat().st_mtime)
    for candidate in reversed(candidates):
        manifest = candidate / "manifest.json"
        if manifest.exists():
            return manifest
    return None


def load_json(path: Path) -> dict[str, Any]:
    resolved = repo_path(path)
    if not resolved.exists():
        return {"present": False, "path": str(resolved)}
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(resolved)
    return payload


def choose_v425_manifest(args: argparse.Namespace) -> Path | None:
    if args.v425_manifest:
        return repo_path(args.v425_manifest)
    return latest_manifest(DEFAULT_V425_PATTERN)


def evidence_dir_from_v425(v425_manifest: Path) -> Path:
    return v425_manifest.parent / "v423-android-hwservice-bootcomplete-run"


def read_command(evidence_dir: Path, name: str) -> str:
    path = evidence_dir / "commands" / f"{name}.txt"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def read_v423_manifest(evidence_dir: Path) -> dict[str, Any]:
    path = evidence_dir / "manifest.json"
    if not path.exists():
        return {"present": False, "path": str(path)}
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["present"] = True
    payload["path"] = str(path)
    return payload


def parse_props(text: str) -> dict[str, str]:
    props: dict[str, str] = {}
    for line in text.splitlines():
        match = PROP_RE.match(line.strip())
        if match:
            props[match.group("key")] = match.group("value")
    return props


def matching_lines(text: str, limit: int = 200) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$") or line.startswith("rc="):
            continue
        if not WIFI_RE.search(line):
            continue
        if line in seen:
            continue
        seen.add(line)
        lines.append(line)
        if len(lines) >= limit:
            break
    return lines


def parse_service_list(text: str) -> list[dict[str, str]]:
    services: list[dict[str, str]] = []
    for line in text.splitlines():
        match = SERVICE_LINE_RE.match(line)
        if match and WIFI_RE.search(match.group("name") + " " + match.group("iface")):
            services.append(match.groupdict())
    return services


def parse_processes(text: str) -> list[dict[str, str]]:
    processes: list[dict[str, str]] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("$") or line.startswith("rc="):
            continue
        if not WIFI_RE.search(line):
            continue
        name_match = PROCESS_NAME_RE.search(line)
        name = name_match.group("name") if name_match else line.split()[-1]
        if name in seen:
            continue
        seen.add(name)
        columns = line.split()
        context = columns[0] if columns else ""
        user = columns[1] if len(columns) > 1 else ""
        processes.append({"name": name, "context": context, "user": user, "line": line.strip()})
    return processes


def parse_lshal(text: str) -> dict[str, Any]:
    lines = matching_lines(text)
    fqinstances: list[str] = []
    warnings: list[str] = []
    for line in lines:
        if line.startswith("Warning:"):
            warnings.append(line)
        for token in line.split():
            if "::" in token and "/" in token and WIFI_RE.search(token):
                fqinstances.append(token.strip('"'))
    unique_fqinstances = sorted(dict.fromkeys(fqinstances))
    matched_targets = [target for target in TARGETED_WAIT_TARGETS if target in text]
    return {
        "lines": lines,
        "warnings": warnings,
        "fqinstances": unique_fqinstances,
        "matched_targets": matched_targets,
    }


def surface_items(props: dict[str, str],
                  services: list[dict[str, str]],
                  dumpsys_lines: list[str],
                  processes: list[dict[str, str]],
                  lshal: dict[str, Any],
                  vintf_lines: list[str]) -> list[SurfaceItem]:
    service_names = {service["name"] for service in services}
    process_names = {process["name"] for process in processes}
    fqinstances = set(lshal["fqinstances"])
    items = [
        SurfaceItem("boot-complete", props.get("sys.boot_completed") == "1", "getprop", f"sys.boot_completed={props.get('sys.boot_completed', '')}"),
        SurfaceItem("framework-wifi-service", "wifi" in service_names, "service list", "wifi binder service"),
        SurfaceItem("framework-wifiscanner-service", "wifiscanner" in service_names, "service list", "wifiscanner binder service"),
        SurfaceItem("samsung-sem-wifi-service", "sem_wifi" in service_names, "service list", "Samsung sem_wifi binder service"),
        SurfaceItem("hwservicemanager-running", props.get("init.svc.hwservicemanager") == "running", "getprop", f"init.svc.hwservicemanager={props.get('init.svc.hwservicemanager', '')}"),
        SurfaceItem("vendor-wifi-hal-ext-running", props.get("init.svc.vendor.wifi_hal_ext") == "running", "getprop", f"init.svc.vendor.wifi_hal_ext={props.get('init.svc.vendor.wifi_hal_ext', '')}"),
        SurfaceItem("wificond-running", props.get("init.svc.wificond") == "running" or "wificond" in process_names, "getprop/ps", "wificond process/service"),
        SurfaceItem("wpa-supplicant-process", "wpa_supplicant" in process_names, "ps", "Android boot-complete baseline includes supplicant process"),
        SurfaceItem("android-wifi-hal-process", "android.hardware.wifi@1.0-service" in process_names, "ps", "AOSP Wi-Fi HAL process"),
        SurfaceItem("samsung-wifi-hal-process", "vendor.samsung.hardware.wifi@2.0-service" in process_names, "ps", "Samsung Wi-Fi HAL process"),
        SurfaceItem("target-seh-wifi-fqinstances", set(TARGETED_WAIT_TARGETS).issubset(set(lshal["matched_targets"])), "lshal", ", ".join(lshal["matched_targets"])),
        SurfaceItem("supplicant-fqinstances-declared", any("supplicant" in item.lower() for item in fqinstances), "lshal", "supplicant HIDL fqinstances in lshal surface"),
        SurfaceItem("vintf-wifi-declarations", bool(vintf_lines), "VINTF grep", f"{len(vintf_lines)} Wi-Fi-looking declaration lines"),
        SurfaceItem("dumpsys-wifi-services", bool(dumpsys_lines), "dumpsys -l", f"{len(dumpsys_lines)} Wi-Fi-looking service names"),
    ]
    return items


def classify_gap(v425: dict[str, Any], v423: dict[str, Any], items: list[SurfaceItem]) -> tuple[str, bool, str, list[str]]:
    comparison = v425.get("context", {}).get("comparison", {})
    v422 = comparison.get("v422", {})
    v407 = comparison.get("v407", {})
    missing_required = [item.name for item in items if item.name in {
        "boot-complete",
        "framework-wifi-service",
        "hwservicemanager-running",
        "vendor-wifi-hal-ext-running",
        "target-seh-wifi-fqinstances",
    } and not item.present]
    if missing_required:
        return "v426-android-surface-incomplete", False, "missing required Android boot-complete surface: " + ", ".join(missing_required), missing_required
    if v423.get("decision") == "v423-android-hwservice-targets-present" and v422.get("micro_query_result") == "service-query-timeout":
        gaps = [
            "native private runtime lacks boot-complete Android framework binder surface",
            "native private runtime does not carry Android supplicant/framework Wi-Fi state",
            "native V407 proves HAL process lifetime, but V422 cannot observe the Samsung ISehWifi fqinstances",
        ]
        return "v426-native-registration-surface-gap", True, "Android boot-complete surface is present; native targeted query still times out", gaps
    if v407.get("helper_result") != "start-only-pass":
        return "v426-native-hal-lifecycle-gap", True, "Android surface is present, but native HAL lifecycle is not yet clean", ["native HAL start-only lifecycle"]
    return "v426-gap-unclassified", True, "surface parsed, but gap classification needs manual review", []


def run_plan(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v425_path = choose_v425_manifest(args)
    return {
        "generated_at": now_iso(),
        "command": "plan",
        "decision": "v426-service-surface-mapper-plan-ready",
        "pass": True,
        "reason": "host-only mapper plan generated; no device command is executed",
        "host": collect_host_metadata(),
        "inputs": {
            "v425_manifest": str(v425_path) if v425_path else "",
            "v425_present": bool(v425_path and v425_path.exists()),
        },
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def run_mapper(args: argparse.Namespace, store: EvidenceStore) -> dict[str, Any]:
    v425_path = choose_v425_manifest(args)
    if v425_path is None or not v425_path.exists():
        return {
            "generated_at": now_iso(),
            "command": "run",
            "decision": "v426-missing-v425-evidence",
            "pass": False,
            "reason": "no V425 live manifest found",
            "host": collect_host_metadata(),
            "device_commands_executed": False,
            "device_mutations": False,
            "wifi_bringup_executed": False,
        }
    v425 = load_json(v425_path)
    evidence_dir = evidence_dir_from_v425(v425_path)
    v423 = read_v423_manifest(evidence_dir)
    props = parse_props(read_command(evidence_dir, "identity-props"))
    service_text = read_command(evidence_dir, "service-list-wifi")
    dumpsys_text = read_command(evidence_dir, "dumpsys-service-names-wifi")
    process_text = read_command(evidence_dir, "service-processes")
    lshal_text = read_command(evidence_dir, "lshal-binderized-neat") + "\n" + read_command(evidence_dir, "lshal-wifi-filter")
    vintf_text = read_command(evidence_dir, "vintf-wifi-hal")
    netdev_text = read_command(evidence_dir, "netdev-rfkill-readonly")

    services = parse_service_list(service_text)
    dumpsys_lines = matching_lines(dumpsys_text)
    processes = parse_processes(process_text)
    lshal = parse_lshal(lshal_text)
    vintf_lines = matching_lines(vintf_text)
    netdev_lines = matching_lines(netdev_text)
    items = surface_items(props, services, dumpsys_lines, processes, lshal, vintf_lines)
    decision, pass_ok, reason, native_gaps = classify_gap(v425, v423, items)

    parsed = {
        "props": props,
        "services": services,
        "dumpsys_lines": dumpsys_lines,
        "processes": processes,
        "lshal": lshal,
        "vintf_lines": vintf_lines,
        "netdev_lines": netdev_lines,
        "surface_items": [asdict(item) for item in items],
        "native_gaps": native_gaps,
    }
    store.write_json("parsed-surface.json", parsed)
    return {
        "generated_at": now_iso(),
        "command": "run",
        "decision": decision,
        "pass": pass_ok,
        "reason": reason,
        "host": collect_host_metadata(),
        "inputs": {
            "v425_manifest": str(v425_path),
            "v425_decision": v425.get("decision"),
            "v425_pass": v425.get("pass"),
            "v423_manifest": str(evidence_dir / "manifest.json"),
            "v423_decision": v423.get("decision"),
            "v423_pass": v423.get("pass"),
        },
        "comparison": (v425.get("context") or {}).get("comparison", {}),
        "parsed": parsed,
        "device_commands_executed": False,
        "device_mutations": False,
        "wifi_bringup_executed": False,
    }


def render_summary(manifest: dict[str, Any]) -> str:
    items = manifest.get("parsed", {}).get("surface_items", [])
    item_rows = [[item["name"], "present" if item["present"] else "missing", item["source"], item["detail"]] for item in items]
    process_rows = [
        [process["name"], process.get("user", ""), process.get("context", "")]
        for process in manifest.get("parsed", {}).get("processes", [])
    ]
    service_rows = [
        [service["name"], service["iface"]]
        for service in manifest.get("parsed", {}).get("services", [])
    ]
    gap_rows = [[gap] for gap in manifest.get("parsed", {}).get("native_gaps", [])]
    target_rows = [
        [target, "present" if target in set(manifest.get("parsed", {}).get("lshal", {}).get("matched_targets", [])) else "missing"]
        for target in TARGETED_WAIT_TARGETS
    ]
    return "\n".join(
        [
            "# V426 Wi-Fi Service Surface Mapper",
            "",
            f"- generated: `{manifest['generated_at']}`",
            f"- command: `{manifest['command']}`",
            f"- decision: `{manifest['decision']}`",
            f"- pass: `{manifest['pass']}`",
            f"- reason: {manifest['reason']}",
            f"- device_commands_executed: `{manifest['device_commands_executed']}`",
            f"- device_mutations: `{manifest['device_mutations']}`",
            f"- wifi_bringup_executed: `{manifest['wifi_bringup_executed']}`",
            "",
            "## Target Match",
            "",
            markdown_table(["target", "state"], target_rows if target_rows else [["-", "-"]]),
            "",
            "## Surface Items",
            "",
            markdown_table(["item", "state", "source", "detail"], item_rows if item_rows else [["-", "-", "-", "-"]]),
            "",
            "## Android Processes",
            "",
            markdown_table(["process", "user", "context"], process_rows if process_rows else [["-", "-", "-"]]),
            "",
            "## Framework Services",
            "",
            markdown_table(["service", "interface"], service_rows if service_rows else [["-", "-"]]),
            "",
            "## Native Gaps",
            "",
            markdown_table(["gap"], gap_rows if gap_rows else [["-"]]),
            "",
        ]
    )


def main() -> int:
    args = parse_args()
    store = EvidenceStore(repo_path(args.out_dir))
    manifest = run_plan(args, store) if args.command == "plan" else run_mapper(args, store)
    store.write_json("manifest.json", manifest)
    store.write_text("summary.md", render_summary(manifest))
    print(f"decision: {manifest['decision']}")
    print(f"pass: {manifest['pass']}")
    print(f"reason: {manifest['reason']}")
    print(f"device_commands_executed: {manifest['device_commands_executed']}")
    print(f"device_mutations: {manifest['device_mutations']}")
    print(f"wifi_bringup_executed: {manifest['wifi_bringup_executed']}")
    print(f"out_dir: {store.run_dir}")
    return 0 if manifest["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
